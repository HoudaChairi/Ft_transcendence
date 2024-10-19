from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import login
from django.urls import reverse
from requests_oauthlib import OAuth2Session
from core.apps.authentication.models import Player
import requests
from django.contrib.auth import login as django_login
from django.contrib.auth import get_user_model
from rest_framework import status


from django.contrib.auth.backends import ModelBackend 

# Configuration for Google OAuth
GOOGLE_CLIENT_ID = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
GOOGLE_CLIENT_SECRET = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI  # Callback URL

# OAuth Scopes for Google
GOOGLE_OAUTH_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

class GoogleLoginAPIView(APIView):
    """
    Initiates Google OAuth login by redirecting to Google's OAuth server.
    """
    def get(self, request):
        # Create an OAuth2 session
        google = OAuth2Session(GOOGLE_CLIENT_ID, scope=GOOGLE_OAUTH_SCOPE, redirect_uri=GOOGLE_REDIRECT_URI)

        # Get the Google authorization URL
        authorization_url, state = google.authorization_url(
            'https://accounts.google.com/o/oauth2/auth',
            access_type="offline", prompt="select_account"
        )

        # Redirect to the Google authorization URL
        return redirect(authorization_url)

class GoogleLoginCallbackAPIView(APIView):
    def get(self, request):
        google = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI)
        authorization_response = request.build_absolute_uri()

        try:
            token = google.fetch_token(
                'https://oauth2.googleapis.com/token',
                authorization_response=authorization_response,
                client_secret=GOOGLE_CLIENT_SECRET
            )
        except Exception as e:
            print(f"Error fetching token: {e}")
            return Response({"error": str(e)}, status=400)

        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            params={'alt': 'json', 'access_token': token['access_token']}
        )

        user_info = userinfo_response.json()
        email = user_info.get('email')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')
        username = email.split('@')[0]

        user, created = Player.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        django_login(request, user)

        tokens = user.tokens()

        # Redirect to frontend with tokens as query parameters
        frontend_url = f'https://{request.get_host()}/?access={tokens["access"]}&refresh={tokens["refresh"]}'
        return redirect(frontend_url)