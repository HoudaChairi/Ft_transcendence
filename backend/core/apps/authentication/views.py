   
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import RegisterSerializer,LoginSerializer,LogoutSerializer
    #UpdateProfileSerializer

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LogoutAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# ---------------------------------------------------------------------------------
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
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, friend_id):
#         friend = get_object_or_404(CustomUser, id=friend_id)
#         Friendship.objects.get_or_create(user=request.user, friend=friend)
#         return Response({"message": "Friend added!"}, status=status.HTTP_201_CREATED)

# class RemoveFriendAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, friend_id):
#         friendship = get_object_or_404(Friendship, user=request.user, friend_id=friend_id)
#         friendship.delete()
#         return Response({"message": "Friend removed!"}, status=status.HTTP_204_NO_CONTENT)

# # new: Create an endpoint to retrieve match history.
# class MatchHistoryAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

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
