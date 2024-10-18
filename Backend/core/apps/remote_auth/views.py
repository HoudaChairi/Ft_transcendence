from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Player

class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)

            # Check if the user already exists
            user, created = Player.objects.get_or_create(
                email=idinfo['email'],
                defaults={
                    'username': idinfo['email'],  # or any unique username you want
                    'display_name': idinfo.get('name', ''),
                }
            )

            # Generate tokens
            tokens = user.tokens()

            return Response({
                'email': user.email,
                'username': user.username,
                'access': tokens['access'],
                'refresh': tokens['refresh'],
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
