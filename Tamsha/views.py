from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.models import SelectedActivity  # Import the model to save selections


@login_required
def explore(request):
    # Define the list of available activities
    activities = [
        {"name": "Desert", "image": "Tamsha/desert.png"},
        {"name": "Mountain", "image": "Tamsha/mountain.png"},
        {"name": "Dining", "image": "Tamsha/dining.png"},
        {"name": "Sports", "image": "Tamsha/sports.png"},
        {"name": "Music", "image": "Tamsha/music.png"},
        {"name": "Historical Places", "image": "Tamsha/historical.png"},
    ]

    # Define the list of cities
    cities = [
        {
            "name": "Riyadh",
            "image": "Tamsha/riyadh.png",
            "description": "A Vibrant Capital Where Heritage Meets Modernity, Showcasing Iconic Landmarks, Rich Culture, And Rapid Innovation."
        },
        {
            "name": "Jeddah",
            "image": "Tamsha/jeddah.png",
            "description": "A Lively Coastal City With Rich History, Diverse Culture, And Beautiful Beaches."
        },
        {
            "name": "AlUla",
            "image": "Tamsha/alula.png",
            "description": "A Historic City With Ancient Monuments And Stunning Natural Landscapes."
        },
        {
            "name": "Red Sea",
            "image": "Tamsha/Red_Sea.png",
            "description": "A Natural Wonder Offering A Journey Into The Kingdom's Depths, With Stunning Coral Reefs And Unique Marine Life."
        },
        {
            "name": "Makkah",
            "image": "Tamsha/makkah.png",
            "description": "The Holiest City In Islam And A Destination For Millions Of Visitors From All Over The World."
        },
        {
            "name": "Madinah",
            "image": "Tamsha/madinah.png",
            "description": "A Spiritual Haven Of History And Beauty, Adorned With Islamic Landmarks And Welcoming Visitors Worldwide."
        },
    ]

    if request.method == 'POST':
        # Get the list of selected activities from the form
        selected = request.POST.getlist('activities')

        # Delete existing selections for this user to avoid duplicates
        SelectedActivity.objects.filter(user=request.user).delete()

        # Save new selections to the database
        for activity in selected:
            SelectedActivity.objects.create(user=request.user, activity=activity)

        # Add a success message
        messages.success(request, "Your selections have been saved successfully!")

        # Redirect to the index page
        return redirect('index')
    else:
        # For GET requests, retrieve the user's saved selections
        selected_activities = list(
            SelectedActivity.objects.filter(user=request.user).values_list('activity', flat=True)
        )

        # Add 'selected' key to each activity based on database records
        for activity in activities:
            activity['selected'] = activity['name'].lower() in selected_activities

        # Render the explore page with the activities and cities list
        return render(request, "accounts/explore.html", {
            "activities": activities,
            "cities": cities
        })


def index(request):
    return render(request, "Tamsha/index.html")
def explore_view(request):
    return render(request, 'accounts/cities.html', {})