   
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
from core.apps.friends.models import Friendship

# ------------------------------------- Register/Login/Logout ------------------------------------- #

class RegisterAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = user.tokens()
            
            return Response({
                'email': user.email,
                'username': user.username,
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'avatar': user.get_avatar_url(),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        otp = request.data.get('otp')

        if not otp:
            serializer = LoginSerializer(data={'username': username, 'password': password})
            
            if serializer.is_valid():
                validated_data = serializer.validated_data
                
                if validated_data.get('otp_required'):
                    return Response({
                        'message': validated_data['message'],
                        'otp_required': validated_data['otp_required'],
                        'username': validated_data['username']
                    }, status=status.HTTP_200_OK)
                
                return Response({
                    'username': validated_data['user'].username,
                    'tokens': validated_data['tokens'],
                    'avatar': validated_data['avatar']
                }, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            user = authenticate(username=username, password=password)
            if not user or not user.verify_otp(otp):
                return Response({
                    'message': 'Invalid OTP, please try again.'
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = LoginSerializer(user)
            return Response({
                'username': user.username,
                'tokens': serializer.get_tokens(user),
                'avatar': serializer.get_avatar(user)
            }, status=status.HTTP_200_OK)
    
    
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

#  ------------------------------------- 2FA AUTHENTICATION ------------------------------------- #

class Enable2FA(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = request.user
        
        if player.remote:
            return Response({'error': "Remote login cannot enable 2FA."}, status=status.HTTP_403_FORBIDDEN)

        player.generate_otp_secret()
        
        totp = pyotp.TOTP(player.otp_secret)
        otp_uri = totp.provisioning_uri(name=player.email, issuer_name='Ft_transcendence')

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=0
        )
        qr.add_data(otp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return Response({'qr_code': f'data:image/png;base64,{img_str}'}, status=status.HTTP_200_OK)

class Confirm2FA(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = request.user
        otp = request.data.get('otp')

        if not player.otp_secret:
            return Response({'error': '2FA has not been initialized yet.'}, status=status.HTTP_400_BAD_REQUEST)

        if not otp:
            return Response({'error': 'OTP is required to confirm 2FA.'}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(player.otp_secret)
        if totp.verify(otp):
            player.is_2fa_enabled = True
            player.save()
            return Response({'message': '2FA enabled successfully!'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

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
        
class Disable2FA(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player = request.user
        otp = request.data.get('otp')
        print(otp)

        if not player.is_2fa_enabled:
            return Response({'error': '2FA is not enabled!'}, status=status.HTTP_400_BAD_REQUEST)

        if not otp:
            return Response({'error': 'OTP is required to disable 2FA.'}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(player.otp_secret)
        if not totp.verify(otp):
            return Response({'error': 'Invalid OTP. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

        player.is_2fa_enabled = False
        player.otp_secret = None
        player.save()
        
        return Response({'message': '2FA disabled successfully!'}, status=status.HTTP_200_OK)

#  ------------------------------------- List and Infos User ------------------------------------- #

class UserList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            blocked_users = Friendship.objects.filter(
                from_user=request.user,
                status='blocked'
            ).values_list('to_user', flat=True)

            users_blocked_by_others = Friendship.objects.filter(
                to_user=request.user,
                status='blocked'
            ).values_list('from_user', flat=True)

            excluded_user_ids = list(blocked_users) + list(users_blocked_by_others)
            users = Player.objects.exclude(id__in=excluded_user_ids).only('username', 'avatar', 'first_name', 'last_name')

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


class LeaderBoard(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            users = Player.objects.order_by('-t_points')

            users_list = [
                {
                    'username': user.username,
                    'avatar': user.get_avatar_url(),
                    't_points': user.t_points,
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
            user = Player.objects.get(username=username)
            
            matches = Match.objects.filter(Q(player1=user) | Q(player2=user)).select_related('player1', 'player2', 'winner', 'loser').order_by('id')

            matches_data = [{
                'player1': match.player1.username,
                'player2': match.player2.username,
                'winner': match.winner.username if match.winner else None,
                'loser': match.loser.username if match.loser else None,
                'score_player1': match.score_player1,
                'score_player2': match.score_player2,
                'player1_avatar': match.player1.get_avatar_url(),
                'player2_avatar': match.player2.get_avatar_url(),
                'date_played': match.date_played
            } for match in matches]

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
            otp = user.is_2fa_enabled
            remote = user.remote
            response.data['otp_required'] = otp
            response.data['username'] = username
            response.data['avatar'] = avatar
            response.data['remote'] = remote
        except Exception as e:
            return Response({'error': 'Invalid token or user not found'}, status=status.HTTP_400_BAD_REQUEST)

        return response


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
            otp = user.is_2fa_enabled
            remote = user.remote
            response.data['otp_required'] = otp
            response.data['username'] = username
            response.data['avatar'] = avatar
            response.data['remote'] = remote
        except Exception as e:
            return Response({'error': 'Invalid refresh token or user not found'}, status=status.HTTP_400_BAD_REQUEST)

        return response
