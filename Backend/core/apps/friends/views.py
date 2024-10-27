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

    def get(self, request):
        try:
            pending_friendships = Friendship.objects.filter(
                to_user=request.user,
                status='pending'
            )

            blocked_friendships = Friendship.objects.filter(
                from_user=request.user,
                status='blocked'
            )

            accepted_friendships = Friendship.objects.filter(
                Q(from_user=request.user) | Q(to_user=request.user),
                status='accepted'
            )

            def get_user_data(friendship):
                friend = friendship.to_user if friendship.from_user == request.user else friendship.from_user
                return {
                    'username': friend.username,
                    'avatar': friend.get_avatar_url(),
                    'first': friend.first_name if friend.first_name else friend.username,
                    'last': friend.last_name if friend.last_name else '',
                }

            pending_data = [get_user_data(friendship) for friendship in pending_friendships]
            blocked_data = [get_user_data(friendship) for friendship in blocked_friendships]
            accepted_data = [get_user_data(friendship) for friendship in accepted_friendships]

            return Response({
                "pending": pending_data,
                "blocked": blocked_data,
                "accepted": accepted_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                elif friendship.status == 'none':
                    friendship.status = 'pending'
                    friendship.save()
                    return Response(FriendshipSerializer(friendship).data, status=status.HTTP_201_CREATED)
            else:
                friendship = Friendship.objects.create(
                    from_user=request.user,
                    to_user=target_user,
                    status='pending'
                )
                return Response(FriendshipSerializer(friendship).data, status=status.HTTP_201_CREATED)

        elif action == 'remove':
            if friendship and friendship.status == 'accepted':
                friendship.status = 'none'
                friendship.save()
                return Response({"message": "Friendship removed"}, status=status.HTTP_200_OK)
            return Response({"error": "No active friendship to remove"}, status=status.HTTP_400_BAD_REQUEST)


        elif action == 'block':
            if friendship:
                if friendship.status == 'blocked' and friendship.from_user == request.user:
                    return Response({"error": "User already blocked"}, status=status.HTTP_400_BAD_REQUEST)
                elif friendship.from_user == request.user:
                    friendship.status = 'blocked'
                    friendship.save()
                    return Response({"message": "User blocked"}, status=status.HTTP_200_OK)
                elif friendship.to_user == request.user and friendship.status == 'blocked':
                    return Response({"error": "Cannot block a user that has already blocked you"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    friendship.from_user = request.user
                    friendship.to_user = target_user
                    friendship.status = 'blocked'
                    friendship.save()
                    return Response({"message": "User blocked"}, status=status.HTTP_200_OK)
            else:
                friendship = Friendship.objects.create(
                    from_user=request.user,
                    to_user=target_user,
                    status='blocked'
                )
                return Response({"message": "User blocked"}, status=status.HTTP_200_OK)


        elif action == 'unblock':
            if friendship and friendship.status == 'blocked' and friendship.from_user == request.user:
                friendship.status = 'none'
                friendship.save()
                return Response({"message": "User unblocked"}, status=status.HTTP_200_OK)
            return Response({"error": "User is not blocked by you"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
