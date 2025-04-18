import os
import json
import datetime
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from django.shortcuts import render
from .models import Message
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

# -------------------------------
# Import Required LangChain & Related Packages
# -------------------------------
from langchain.document_loaders import CSVLoader as LC_CSVLoader
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()

# Global variable to hold the RAG chain
rag_chain = None


def get_chat_history_from_db(user_id):
    """
    Retrieve chat history for the given user_id from the database.
    Expected to return a list of dictionaries with keys: "role" and "content".
    For example:
        [{"role": "human", "content": "Hello!"}, {"role": "ai", "content": "Hi there!"}]
    """

    # Query the database for all messages from this user, ordered by timestamp
    messages = Message.objects.filter(user_id=user_id).order_by("timestamp")

    # Convert the Message objects to the expected format
    chat_history = []
    for message in messages:
        role = "human" if message.is_from_user else "ai"
        # print(message.text)
        chat_history.append({"role": role, "content": message.text})

    return chat_history


def update_chat_history_in_db(user_id, new_messages):
    """
    Update the conversation history in the database by appending new messages.
    new_messages: List of dicts, e.g.,
        [{"role": "human", "content": "User query"}, {"role": "ai", "content": "AI answer"}]
    """

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)

        # Create new Message objects for each message in new_messages
        for message in new_messages:
            role = message.get("role", "").lower()
            content = message.get("content", "")

            # Only process valid messages
            if role in ["human", "ai"] and content:
                Message.objects.create(
                    user=user, text=content, is_from_user=(role == "human")
                )
    except User.DoesNotExist:
        # Handle case where user doesn't exist
        # You might want to log this error or handle it differently
        pass


# -------------------------------
# Chatbot Initialization Function with VectorStore Caching
# -------------------------------
def init_chatbot():
    global rag_chain
    # 1 - Initialize Embedding Model
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )

    # 2 - Attempt to load the cached vectorstore
    cache_dir = "chat/faiss_cache"  # Local cache directory for the vector store
    vectorstore = None
    if os.path.exists(cache_dir):
        try:
            vectorstore = FAISS.load_local(
                folder_path=cache_dir,
                embeddings=embeddings,
                allow_dangerous_deserialization=True,  # Necessary for pickle loading
            )
            print("[INFO] Loaded cached vectorstore from:", cache_dir)
        except Exception as e:
            print("[ERROR] Failed to load cached vectorstore:", e)

    # 3 - If vectorstore is not loaded, build it from CSV files and cache it
    if not vectorstore:
        csv_directory = r"chat\csv_files"  # Directory containing the CSV files
        csv_files = [
            os.path.join(csv_directory, file)
            for file in os.listdir(csv_directory)
            if file.endswith(".csv")
        ]
        all_data = []
        for file_path in csv_files:
            try:
                loader = LC_CSVLoader(file_path=file_path, encoding="utf-8")
                data = loader.load()
                all_data.extend(data)
                print(f"[INFO] Loaded {len(data)} documents from {file_path}")
            except UnicodeDecodeError:
                print(
                    f"[ERROR] Could not read {file_path} with 'utf-8'. Trying 'utf-8-sig'..."
                )
                try:
                    loader = LC_CSVLoader(file_path=file_path, encoding="utf-8-sig")
                    data = loader.load()
                    all_data.extend(data)
                    print(
                        f"[INFO] Loaded {len(data)} documents from {file_path} using 'utf-8-sig'"
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to load {file_path}: {e}")
        print(
            f"[INFO] Successfully loaded {len(all_data)} documents from {len(csv_files)} CSV files."
        )
        vectorstore = FAISS.from_documents(all_data, embeddings)
        vectorstore.save_local(cache_dir)
        print("[INFO] Saved new vectorstore cache to:", cache_dir)

    # 4 - Initialize the LLM Model (OpenAI)
    api_key = os.getenv("OPENAI_API_KEY")
    llm_model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, streaming=True)

    # 5 - Define the Custom System Prompt
    system_prompt = """
        You are an AI-powered Smart Tourism Assistant for Saudi Arabia, designed to provide detailed, accurate, and engaging responses to users' questions about tourism in the Kingdom.
        Your role is to act as a knowledgeable, friendly, and culturally aware guide.
        The Context: {context}
    
        Your response must be:
        - Don't mention context or provided information. Answer as AI-powered Smart Tourism Assistant.
        - Use fact-based answers from the knowledge base.
        - Maintain an engaging, friendly tone.
        - Be mindful of Saudi Arabia’s traditions and laws.
        - Provide concise and informative responses.
        - Support multilingual responses if requested (Arabic/English).
    
        Handling Irrelevant Questions:
        If a question is unrelated to Saudi Arabian tourism, kindly inform the user of your specialization.
    """

    # 6 - Create the QA Prompt Template
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),  # chat history inserted dynamically
            ("human", "{input}"),
        ]
    )

    # 7 - Create the Prompt Template for Reformulating the User Question
    contextualize_q_system_prompt = """
        Given a chat history and the latest user question, reformulate the question so it is understandable without prior chat history.
        If no changes are needed, return the question as is.
    """
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    # 8 - Create a History-Aware Retriever
    retriever = vectorstore.as_retriever()
    history_aware_retriever = create_history_aware_retriever(
        llm_model, retriever, contextualize_q_prompt
    )

    # 9 - Build the Chain for Answering Questions with Context
    question_answer_chain = create_stuff_documents_chain(llm_model, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    print("[INFO] Chatbot initialization completed.")


# Initialize the chatbot (and vectorstore caching) when this module is loaded.
init_chatbot()


@csrf_exempt
def chat(request):
    user_id = request.user.pk

    if request.method == "GET":
        # Handle two cases: initial page load and streaming request
        if "input" in request.GET:
            # Streaming request via EventSource
            try:
                return handle_streaming_request(request, user_id)
            except Ratelimited:

                def error_generator():
                    yield f"data: {json.dumps({'error': 'Rate limit exceeded. Please try again later.'})}\n\n"


                return StreamingHttpResponse(
                    error_generator(),
                    content_type="text/event-stream",
                    status=200,
                )

        # Regular page load with history
        history_data = get_chat_history_from_db(user_id)

        return render(
            request,
            "chat/index.html",
            {"chat_history": history_data, "session_id": request.session.session_key},
        )

    return JsonResponse({"error": "Method not allowed"}, status=405)


@ratelimit(key="user_or_ip", rate="30/m")
def handle_streaming_request(request, user_id):
    # Validate required parameters
    user_input = request.GET.get("input", "")
    session_id = request.GET.get("session_id", "")

    if not user_input or not session_id:
        return JsonResponse({"error": "Missing parameters"}, status=400)

    # Verify session (important for security)
    if not request.session.session_key == session_id:
        return JsonResponse({"error": "Invalid session"}, status=403)

    # Retrieve chat history
    history_data = get_chat_history_from_db(user_id)
    chat_history = [
        (
            HumanMessage(content=msg["content"])
            if msg["role"] == "human"
            else AIMessage(content=msg["content"])
        )
        for msg in history_data
    ]

    def event_stream():
        full_answer = []
        try:
            for chunk in rag_chain.stream(
                {"input": user_input, "chat_history": chat_history}
            ):
                # for chunk in [
                # {"answer": "hello "},
                # {"answer": "i am an ai "},
                # {"answer": "how can i help you?\n\n"},
                # {
                # "answer": "Sure! Here are ten fantastic places to visit in Saudi Arabia:\n\n\n\n1. **Al-Ula**: Famous for its stunning rock formations and archaeological sites, including the UNESCO World Heritage site of Madain Saleh.\n\n\n\n2. **Mecca (Makkah)**: The holiest city in Islam, home to the Kaaba and Masjid al-Haram, where millions of Muslims come for pilgrimage (Hajj).\n\n\n\n3. **Medina (Madinah)**: The second holiest city in Islam, known for the Prophet’s Mosque, which houses the tomb of Prophet Muhammad.\n\n\n\n4. **Riyadh**: The capital city features modern attractions like Kingdom Centre Tower, the National Museum, and historical sites like Al Masmak Fortress.\n\n\n\n5. **Jeddah**: A coastal city known for its beautiful Corniche, the historic Al-Balad district, and the stunning Floating Mosque.\n\n\n\n6. **The Empty Quarter (Rub' al Khali)**: The world's largest sand desert, perfect for dune bashing, stargazing, and exploring its vast beauty.\n\n\n\n7. **Farasan Islands**: A stunning group of islands off the coast of Jazan, ideal for snorkeling, diving, birdwatching, and relaxing on beautiful beaches.\n\n\n\n8. **Al-Ahsa Oasis**: A UNESCO World Heritage site known for its lush palm groves, historical sites, and beautiful landscapes.\n\n\n\n9. **At-Turaif District**: Located in Riyadh, this UNESCO World Heritage site features traditional Najdi architecture and reflects the historical significance of the region.\n\n\n\n10. **The Edge of the World (Jebel Fihrayn)**: A breathtaking viewpoint offering stunning vistas of the desert and cliffs, perfect for adventure seekers.\n\n\n\nEach of these places showcases the rich history, culture, and natural beauty of Saudi Arabia. Enjoy your travels!"
                # },
                # ]:
                # print(chunk)
                if "answer" in chunk:
                    token = chunk["answer"]
                    full_answer.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # Save to database after successful completion
            update_chat_history_in_db(
                user_id,
                [
                    {"role": "human", "content": user_input},
                    {"role": "ai", "content": "".join(full_answer)},
                ],
            )
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Close any resources if needed
            pass

    return StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@require_POST
@csrf_protect
def chat_clear(request):
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")

        # Clear chat history for the given session_id
        user_id = request.user.pk
        Message.objects.filter(user_id=user_id).delete()

        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
