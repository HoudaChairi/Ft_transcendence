from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Friendship
from core.apps.authentication.models import Player 
from .serializers import FriendshipListSerializer  
from django.db.models import Q  


class FriendshipView(APIView):
    permission_classes = [IsAuthenticated]

    def get_friendship_lists(self, user):

        friends = Friendship.objects.filter(
            Q(from_user=user, status='accepted') | 
            Q(to_user=user, status='accepted')
        )
        pending = Friendship.objects.filter(to_user=user, status='pending')
        blocked = Friendship.objects.filter(
            Q(from_user=user, status='blocked') | 
            Q(to_user=user, status='blocked')
        )

        return {
            "friends": FriendshipListSerializer(friends, many=True).data,
            "pending": FriendshipListSerializer(pending, many=True).data,
            "blocked": FriendshipListSerializer(blocked, many=True).data,
        }

    def post(self, request):

        to_username = request.data.get('to_username')
        from_user = request.user
        
        try:
            to_user = Player.objects.get(username=to_username)

            friendship, created = Friendship.objects.get_or_create(
                from_user=from_user, 
                to_user=to_user, 
                defaults={'status': 'pending'}
            )

            if not created:
                if friendship.status == 'pending':
                    return Response({"message": "Friendship request already sent", "lists": self.get_friendship_lists(from_user)}, status=status.HTTP_400_BAD_REQUEST)
                elif friendship.status == 'accepted':
                    return Response({"message": "You are already friends", "lists": self.get_friendship_lists(from_user)}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "message": "Friendship request sent",
                "lists": self.get_friendship_lists(from_user)
            }, status=status.HTTP_201_CREATED)

        except Player.DoesNotExist:
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, username):
        action = request.data.get('action')  
        from_user = request.user 
        to_user = get_object_or_404(Player, username=username)

        try:
            friendship = Friendship.objects.get(
                Q(from_user=from_user, to_user=to_user) |
                Q(from_user=to_user, to_user=from_user)
            )
        except Friendship.DoesNotExist:
            if action == 'block':
                friendship = Friendship.objects.create(from_user=from_user, to_user=to_user, status='blocked')
                return Response({
                    "message": f"{to_user.username} has been blocked",
                    "lists": self.get_friendship_lists(from_user)
                }, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Friendship request not found"}, status=status.HTTP_404_NOT_FOUND)

        if action == 'block':
            friendship.status = 'blocked'
            friendship.save()
            return Response({
                "message": f"{to_user.username} has been blocked",
                "lists": self.get_friendship_lists(from_user)
            }, status=status.HTTP_200_OK)

        elif action == 'unblock':
            if friendship.status == 'blocked':
                friendship.delete()
                return Response({
                    "message": f"{to_user.username} has been unblocked, no friendship exists anymore",
                    "lists": self.get_friendship_lists(from_user)
                }, status=status.HTTP_200_OK)
            else:
                return Response({"message": "This user is not blocked"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)


    def delete(self, request, username):
        from_user = request.user
        to_user = get_object_or_404(Player, username=username)

        try:
            friendship = Friendship.objects.get(
                Q(from_user=from_user, to_user=to_user) | 
                Q(from_user=to_user, to_user=from_user)
            )
            friendship.delete()

            return Response({
                "message": "Friendship removed",
                "lists": self.get_friendship_lists(from_user)
            }, status=status.HTTP_200_OK)

        except Friendship.DoesNotExist:
            return Response({"message": "Friendship not found"}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request):
        return Response(self.get_friendship_lists(request.user), status=status.HTTP_200_OK)
