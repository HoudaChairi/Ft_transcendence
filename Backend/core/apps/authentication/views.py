   
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import RegisterSerializer,LoginSerializer, LogoutSerializer, DisplayNameSerializer
    #UpdateProfileSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Player
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # Create the user
            tokens = user.tokens()    # Get the tokens for the newly created user
            
            return Response({
                'email': user.email,
                'username': user.username,
                'access': tokens['access'],
                'refresh': tokens['refresh'],
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# ---------------------------------------------------------------------------------
# 
class UpdateDisplayNameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = DisplayNameSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Display name updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# 
# 
# after : to handle user updates.
# class UpdateProfileView(APIView):
#     # permission_classes = [permissions.IsAuthenticated]

#     def put(self, request):
#         user = request.user
#         serializer = UpdateProfileSerializer(user, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# friend list
# class FriendListView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         friends = user.friends.all()
#         serializer = FriendSerializer(friends, many=True)
#         return Response(serializer.data)

# new: views to add and remove friends.
# class AddFriendAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, friend_id):
#         friend = get_object_or_404(Player, id=friend_id)
#         Friendship.objects.get_or_create(user=request.user, friend=friend)
#         return Response({"message": "Friend added!"}, status=status.HTTP_201_CREATED)

# class RemoveFriendAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, friend_id):
#         friendship = get_object_or_404(Friendship, user=request.user, friend_id=friend_id)
#         friendship.delete()
#         return Response({"message": "Friend removed!"}, status=status.HTTP_204_NO_CONTENT)

# # new: Create an endpoint to retrieve match history.
# class MatchHistoryAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         matches = Match.objects.filter(user=request.user).values('opponent__username', 'result', 'date')
#         return Response(matches, status=status.HTTP_200_OK)

# or : 
# class MatchHistoryView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         match_history = user.match_set.all()  # Assuming you have a Match model
#         return Response(match_history)


class UserList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = Player.objects.all()

        users_list = [
            {
                'username': user.username,
            }
            for user in users
        ]

        return Response({'users': users_list})


#------------------------------------------------
# Custom TokenVerifyView to return username
class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        try:
            token = request.data.get('token')
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = Player.objects.get(id=user_id)
            username = user.username
            response.data['username'] = username
        except Exception as e:
            return Response({'error': 'Invalid token or user not found'}, status=status.HTTP_400_BAD_REQUEST)

        return response


# Custom TokenRefreshView to return username
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        try:
            refresh_token = request.data.get('refresh')
            access_token = AccessToken(response.data['access'])
            user_id = access_token['user_id']
            user = Player.objects.get(id=user_id)
            username = user.username
            response.data['username'] = username
        except Exception as e:
            return Response({'error': 'Invalid refresh token or user not found'}, status=status.HTTP_400_BAD_REQUEST)

        return response