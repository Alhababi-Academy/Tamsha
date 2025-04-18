from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class Message(models.Model):
    """
    Represents a single message in the chatbot conversation.
    Each message is associated with a user and indicates whether it was sent by the user or the bot.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="The user associated with this message.",
    )
    text = models.TextField(help_text="The content of the message.")
    timestamp = models.DateTimeField(
        auto_now_add=True, help_text="The time the message was created."
    )
    is_from_user = models.BooleanField(
        help_text="True if the message is from the user, False if from the bot."
    )

    def __str__(self):
        """String representation of the message for admin interface or debugging."""
        sender = "User" if self.is_from_user else "Bot"
        return f"{sender}: {self.text[:50]}..."

    @property
    def sender(self):
        """Returns the sender of the message as a string for easy display."""
        return "User" if self.is_from_user else "Bot"

    class Meta:
        """Metadata for the Message model."""

        ordering = ["timestamp"]  # Orders messages chronologically by timestamp
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            # Optimizes queries filtering by user and ordering by timestamp
        ]


# from django.contrib.auth.models import AbstractUser
# class User(AbstractUser):
#     """
#     Custom User model extending Django's AbstractUser.
#     You can add additional fields here if needed (e.g., profile picture, bio, etc.).
#     """
#     # Add any additional fields you want for the user
#     # Example:
#     # profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

#     def __str__(self):
#         return self.username
