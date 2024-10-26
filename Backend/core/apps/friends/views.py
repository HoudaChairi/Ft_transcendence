# friends/views.py

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from core.apps.authentication.models import Player  # Importing Player directly
from .models import Friendship
from .serializers import FriendshipSerializer

class ManageFriendshipView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action, username, *args, **kwargs):
        target_user = get_object_or_404(Player, username=username)  # Using Player model

        # Check if a friendship already exists or create a new one
        friendship, created = Friendship.objects.get_or_create(
            from_user=request.user,
            to_user=target_user
        )

        if action == 'add':
            # Handle friend request (send friend request if it doesn't exist)
            if friendship.status == 'none' or created:
                friendship.status = 'pending'
                friendship.save()
                return Response(FriendshipSerializer(friendship).data, status=status.HTTP_201_CREATED)
            elif friendship.status == 'pending':
                return Response({"error": "Friend request already sent"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "Action not allowed"}, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'remove':
            # Remove a friend (revert to "none" status)
            if friendship.status in ['accepted', 'pending', 'blocked']:
                friendship.status = 'none'
                friendship.save()
                return Response({"message": "Friendship removed"}, status=status.HTTP_200_OK)
            return Response({"error": "No active friendship to remove"}, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'block':
            # Block a user
            if friendship.status != 'blocked':
                friendship.status = 'blocked'
                friendship.save()
                return Response({"message": "User blocked"}, status=status.HTTP_200_OK)
            return Response({"error": "User already blocked"}, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'unblock':
            # Unblock a user (set status back to "none")
            if friendship.status == 'blocked':
                friendship.status = 'none'
                friendship.save()
                return Response({"message": "User unblocked"}, status=status.HTTP_200_OK)
            return Response({"error": "User is not blocked"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
