   
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Player, Match
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView
from django.db.models import Q
import pyotp
import qrcode
from io import BytesIO
import base64

# ------------------------------------- Register/Login/Logout ------------------------------------- #
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
                'avatar': user.get_avatar_url(),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            
            # Check if user has 2FA enabled
            if user.is_2fa_enabled:
                return Response({'message': '2FA required', 'otp_required': True, 'username': user.username}, status=status.HTTP_200_OK)
            
            # Generate tokens if 2FA is not required
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
    
# ------------------------------------- Infos UPDATE ------------------------------------- #
class UpdateInfosView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        serializer = UpdateInfosSerializer(user, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully.',
                'user': serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdatePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user 
        data = request.data

        serializer = UpdatePasswordSerializer(data=data, context={'user': user})

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password updated successfully.'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# class UpdateDisplayNameView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         user = request.user
#         serializer = DisplayNameSerializer(user, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "Display name updated successfully"}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ------------------------------------- Avatar UPDATE ------------------------------------- #
class UpdateAvatarView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = AvatarSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "avatar": user.get_avatar_url()
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ------------------------------------- Match HISTORY ------------------------------------- #
class MatchCreateView(APIView):
    def post(self, request, *args, **kwargs):
        player1_username = request.data.get('player1')
        player2_username = request.data.get('player2')
        score_player1 = request.data.get('score_player1')
        score_player2 = request.data.get('score_player2')
        winner_username = request.data.get('winner')
        loser_username = request.data.get('loser')

        try:
            player1 = Player.objects.get(username=player1_username)
            player2 = Player.objects.get(username=player2_username)

            # Determine the winner and loser based on the provided usernames
            winner = player1 if winner_username == player1_username else player2
            loser = player1 if loser_username == player1_username else player2
            
        except Player.DoesNotExist:
            return Response({"error": "One or more players not found."}, status=status.HTTP_404_NOT_FOUND)

        winner.wins += 1
        loser.losses += 1
        winner.t_points += 3
        loser.t_points -= 1
        
        player1.t_games += 1
        player1.goals_f += int(score_player1)
        player1.goals_a += int(score_player2)
        
        player2.t_games += 1
        player2.goals_f += int(score_player2)
        player2.goals_a += int(score_player1)
        
        player1.save()
        player2.save()

        match_data = {
            'player1': player1.id,
            'player2': player2.id,
            'score_player1': score_player1,
            'score_player2': score_player2,
            'loser': loser.id,
            'winner': winner.id
        }
        
        serializer = MatchSerializer(data=match_data)
        if serializer.is_valid():
            match = serializer.save()
            return Response(MatchSerializer(match).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#  ------------------------------------- 2FA AUTHENTICATION ------------------------------------- #

# View for Enabling 2FA
class Enable2FA(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = request.user
        player.generate_otp_secret()

        # Generate the OTP URI
        totp = pyotp.TOTP(player.otp_secret)
        otp_uri = totp.provisioning_uri(name=player.email, issuer_name='Ft_transcendence')

        # Generate QR code
        img = qrcode.make(otp_uri)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return Response({'qr_code': f'data:image/png;base64,{img_str}'}, status=status.HTTP_200_OK)

# View for Verifying OTP
class Verify2FA(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        otp = request.data.get('otp')
        player = request.user

        totp = pyotp.TOTP(player.otp_secret)
        if totp.verify(otp):
            player.is_2fa_enabled = True
            player.save()
            return Response({'message': '2FA enabled successfully!'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP! Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

#  ------------------------------------- List and Infos User ------------------------------------- #

class UserList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            users = Player.objects.only('username', 'avatar', 'first_name', 'last_name')
            
            users_list = [
                {
                    'username': user.username,
                    'avatar': user.get_avatar_url(),
                    'first': user.first_name if user.first_name else user.username,
                    'last': user.last_name if user.last_name else '',
                }
                for user in users
            ]
            
            return Response({'users': users_list})
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserInfos(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            # Fetch the user by username
            user = Player.objects.get(username=username)

            # Retrieve all matches where the user is either player1 or player2
            matches = Match.objects.filter(Q(player1=user) | Q(player2=user)).select_related('player1', 'player2', 'winner', 'loser').order_by('id')

            # Format the matches data
            matches_data = [{
                'player1': match.player1.username,
                'player2': match.player2.username,
                'winner': match.winner.username if match.winner else None,
                'loser': match.loser.username if match.loser else None,
                'score_player1': match.score_player1,
                'score_player2': match.score_player2,
                'player1_avatar': match.player1.get_avatar_url(),
                'player2_avatar': match.player2.get_avatar_url()
            } for match in matches]

            # Return the user data along with their matches
            return Response({
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'avatar': user.get_avatar_url(),
                'tournament_username': user.tournament_username,
                'gender': user.gender,
                'wins': user.wins,
                'losses': user.losses,
                't_games': user.t_games,
                't_points': user.t_points,
                'goals_f': user.goals_f,
                'goals_a': user.goals_a,
                'matches': matches_data  # Adding matches data to the response
            }, status=status.HTTP_200_OK)

        except Player.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------------------------- Tokens verification ------------------------------------- #

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
            avatar = user.get_avatar_url()
            response.data['username'] = username
            response.data['avatar'] = avatar
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
            avatar = user.get_avatar_url()
            response.data['username'] = username
            response.data['avatar'] = avatar
        except Exception as e:
            return Response({'error': 'Invalid refresh token or user not found'}, status=status.HTTP_400_BAD_REQUEST)

        return response