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


GOOGLE_CLIENT_ID = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
GOOGLE_CLIENT_SECRET = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI

GOOGLE_OAUTH_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

class GoogleView(APIView):
    def get(self, request):
        google = OAuth2Session(GOOGLE_CLIENT_ID, scope=GOOGLE_OAUTH_SCOPE, redirect_uri=GOOGLE_REDIRECT_URI)

        authorization_url, state = google.authorization_url(
            'https://accounts.google.com/o/oauth2/auth',
            access_type="offline", prompt="select_account"
        )

        return redirect(authorization_url)

class GoogleCallbackView(APIView):
    def get(self, request):
        error = request.GET.get('error')
        if error:
            if error == 'access_denied':
                frontend_url = f'https://{request.get_host()}/login?error=access_denied'
                return redirect(frontend_url)
            else:
                frontend_url = f'https://{request.get_host()}/login?error={error}'
                return redirect(frontend_url)

        google = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI)
        authorization_response = request.build_absolute_uri()

        try:
            token = google.fetch_token(
                'https://oauth2.googleapis.com/token',
                authorization_response=authorization_response,
                client_secret=GOOGLE_CLIENT_SECRET
            )
        except Exception as e:
            frontend_url = f'https://{request.get_host()}/login?error=token_fetch_failed'
            return redirect(frontend_url)

        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            params={'alt': 'json', 'access_token': token['access_token']}
        )

        user_info = userinfo_response.json()
        email = user_info.get('email')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')
        username = email.split('@')[0]
        profile_pic_url = user_info.get('picture')

        user, created = Player.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        user.remote = True
        user.tournament_username = user.username
        if created or not user.avatar:
            user.avatar = profile_pic_url
            user.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        django_login(request, user)

        tokens = user.tokens()

        frontend_url = f'https://{request.get_host()}/login?access={tokens["access"]}&refresh={tokens["refresh"]}'
        return redirect(frontend_url)

# 42
FT_CLIENT_ID = settings.SOCIAL_AUTH_42_KEY
FT_CLIENT_SECRET = settings.SOCIAL_AUTH_42_SECRET  
FT_REDIRECT_URI = settings.SOCIAL_AUTH_42_REDIRECT_URI

class FtView(APIView):
    def get(self, request):
        ft_oauth = OAuth2Session(FT_CLIENT_ID, redirect_uri=FT_REDIRECT_URI)
        authorization_url, state = ft_oauth.authorization_url(
            'https://api.intra.42.fr/oauth/authorize'
        )
        return redirect(authorization_url)

class FtCallbackView(APIView):
    def get(self, request):
        ft_oauth = OAuth2Session(FT_CLIENT_ID, redirect_uri=FT_REDIRECT_URI)
        authorization_response = request.build_absolute_uri()

        try:
            token = ft_oauth.fetch_token(
                'https://api.intra.42.fr/oauth/token',
                authorization_response=authorization_response,
                client_secret=FT_CLIENT_SECRET
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        userinfo_response = requests.get(
            'https://api.intra.42.fr/v2/me',
            headers={'Authorization': f'Bearer {token["access_token"]}'}
        )

        user_info = userinfo_response.json()
        email = user_info.get('email')
        first_name = user_info.get('first_name')
        last_name = user_info.get('last_name')
        username = user_info.get('login')
        avatar_url = user_info.get('image', {}).get('link')

        user, created = Player.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        user.remote = True
        user.tournament_username = user.username
        if created:
            user.avatar = avatar_url
        user.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        django_login(request, user)

        tokens = user.tokens()

        frontend_url = f'https://{request.get_host()}/login?access={tokens["access"]}&refresh={tokens["refresh"]}'
        return redirect(frontend_url)