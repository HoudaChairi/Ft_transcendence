from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from core.apps.authentication.models import Player
from .models import Friendship
from .serializers import FriendshipSerializer

class ManageFriendshipView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action, username, *args, **kwargs):
        target_user = get_object_or_404(Player, username=username)
    
        friendship = Friendship.objects.filter(
            (Q(from_user=request.user) & Q(to_user=target_user)) |
            (Q(from_user=target_user) & Q(to_user=request.user))
        ).first()

        if action == 'add':
            if friendship:
                if friendship.status == 'pending':
                    return Response({"error": "Friend request already sent"}, status=status.HTTP_400_BAD_REQUEST)
                elif friendship.status == 'accepted':
                    return Response({"error": "You are already friends"}, status=status.HTTP_400_BAD_REQUEST)
                elif friendship.status == 'blocked':
                    return Response({"error": "You cannot send a friend request to a blocked user"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                friendship = Friendship.objects.create(
                    from_user=request.user,
                    to_user=target_user,
                    status='pending'
                )
                return Response(FriendshipSerializer(friendship).data, status=status.HTTP_201_CREATED)

        elif action == 'remove':
            if friendship and friendship.status in ['accepted', 'pending', 'blocked']:
                friendship.status = 'none'
                friendship.save()
                return Response({"message": "Friendship removed"}, status=status.HTTP_200_OK)
            return Response({"error": "No active friendship to remove"}, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'block':
            if friendship:
                if friendship.status != 'blocked':
                    friendship.status = 'blocked'
                    friendship.save()
                    return Response({"message": "User blocked"}, status=status.HTTP_200_OK)
                return Response({"error": "User already blocked"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # If no friendship exists, you may handle it accordingly
                return Response({"error": "No friendship to block"}, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'unblock':
            if friendship and friendship.status == 'blocked':
                friendship.status = 'none'
                friendship.save()
                return Response({"message": "User unblocked"}, status=status.HTTP_200_OK)
            return Response({"error": "User is not blocked"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
