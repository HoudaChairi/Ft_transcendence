from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from social_django.utils import social_auth
from core.apps.authentication import Player
from rest_framework_simplejwt.tokens import RefreshToken

class GoogleOAuth2CallbackView(APIView):

    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({'error': 'No code provided'}, status=status.HTTP_400_BAD_REQUEST)

        backend = social_auth.get_backend('google-oauth2')
        if backend is None:
            return Response({'error': 'Google OAuth2 backend not found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            user = backend.do_auth(code)
            if user is None:
                return Response({'error': 'Google login failed'}, status=status.HTTP_400_BAD_REQUEST)

            player, created = Player.objects.get_or_create(
                email=user.email,
                defaults={
                    'username': user.email.split('@')[0], 
                    'display_name': user.name,              
                    'is_google_user': True                
                }
            )


            if not created:
                player.is_google_user = True
                player.save()


            refresh = RefreshToken.for_user(player)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'username': player.username,
                    'email': player.email,
                    'display_name': player.display_name,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
