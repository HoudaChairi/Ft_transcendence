from rest_framework import serializers
from .models import Player, Match
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.hashers import check_password
from django.contrib.auth import authenticate
import re

# -------------------------------------------------------------------------------------- #
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirmPassword = serializers.CharField(write_only=True, required=True)
    gender = serializers.ChoiceField(choices=Player.GENDER_CHOICES, required=False)

    class Meta:
        model = Player
        fields = ['email', 'username', 'password', 'confirmPassword', 'gender']

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as exc:
            raise serializers.ValidationError(str(exc))
        return value
    
    def validate_username(self, value):
        if ' ' in value:
            raise serializers.ValidationError("Username should not contain spaces.")    
        if not re.match("^[a-zA-Z0-9_-]+$", value):
            raise serializers.ValidationError(
                "Username should only contain letters, numbers, dashes, or underscores.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirmPassword']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirmPassword', None)
        user = Player.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            gender=validated_data.get('gender', None),
            tournament_username = validated_data['username'],
            avatar='textures/svg/M.svg' if validated_data.get('gender', None) == 'M' else 'textures/svg/ProfilePic.svg'
        )
        return user
    
# Login serializer:
class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=255, min_length=3)
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    tokens = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = ['username', 'password', 'tokens', 'avatar']

    def get_tokens(self, user):
        return {
            'refresh': user.tokens()['refresh'],
            'access': user.tokens()['access'],
        }

    def get_avatar(self, user):
        return user.get_avatar_url()

    def validate(self, attrs):
        username = attrs.get('username', '')
        password = attrs.get('password', '')
        
        user = authenticate(username=username, password=password)

        if not user:
            raise AuthenticationFailed('Invalid credentials, try again.')
        
        if not user.is_active:
            raise AuthenticationFailed('Account disabled, contact admin.')

        if user.is_2fa_enabled:
            return {
                'username': user.username,
                'otp_required': True,
                'message': '2FA required'
            }

        return {
            'user': user,
            'tokens': self.get_tokens(user),
            'avatar': self.get_avatar(user)
        }

        
# Logout serializer:
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_messages = {
        'bad_token': 'Token is invalid or expired',
        'blacklisted_token': 'Token is already blacklisted'
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.check_blacklist()
        except TokenError as e:
            if str(e) == "Token is blacklisted":
                self.fail('blacklisted_token')
            else:
                self.fail('bad_token')
        else:
            token.blacklist() 
            
# -------------------------------------------------------------------------------------- #

class UpdateInfosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['tournament_username', 'email', 'first_name', 'last_name']

    def validate_tournament_username(self, value):
        if Player.objects.filter(tournament_username=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Tournament username is already taken.")
        return value

    def validate_email(self, value):
        if self.instance.remote:
            raise serializers.ValidationError("Remote Login can't change email.")
        if Player.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Email is already taken.")
        return value

    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("First name cannot be empty.")
        return value

    def validate_last_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Last name cannot be empty.")
        return value


class UpdatePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        user = self.context['user']
        
        if user.remote:
            raise serializers.ValidationError("Remote Login can't change password.")

        if data.get('old_password') and not data.get('new_password'):
            raise serializers.ValidationError("New password is required when old password is provided.")
        return data

    def save(self, **kwargs):
        user = self.context['user']
        
        old_password = self.validated_data.get('old_password')
        new_password = self.validated_data.get('new_password')

        if old_password:
            if not authenticate(username=user.username, password=old_password):
                raise serializers.ValidationError("Old password is incorrect.")
            if new_password:
                user.password = make_password(new_password)
                
        elif new_password:
            user.password = make_password(new_password)

        user.save()
        return user
    
class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['avatar']

    def validate_avatar(self, value):
        if not value.name.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            raise serializers.ValidationError("File type is not supported. Please upload an image.")
        
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size should be less than 5 MB.")
        
        return value


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ['player1', 'player2', 'score_player1', 'score_player2', 'winner', 'loser']

    def validate(self, attrs):
        if attrs['player1'] == attrs['player2']:
            raise serializers.ValidationError("Players cannot be the same.")
        return attrs