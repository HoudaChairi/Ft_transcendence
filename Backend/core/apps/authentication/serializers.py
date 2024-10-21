from rest_framework import serializers
from .models import Player
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

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirmPassword = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Player
        fields = ['email', 'username', 'password', 'confirmPassword']

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
        )
        return user
    
# new Login serializer:
class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=255, min_length=3)
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    tokens = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_tokens(self, user):
        # Now `user` is the Player instance
        return {
            'refresh': user.tokens()['refresh'],
            'access': user.tokens()['access'],
        }

    def get_avatar(self, user):
        # Call the method to get the avatar URL
        return user.get_avatar_url()

    class Meta:
        model = Player
        fields = ['username', 'password', 'tokens', 'avatar']

    def validate(self, attrs):
        username = attrs.get('username', '')
        password = attrs.get('password', '')
        user = auth.authenticate(username=username, password=password)

        if not user:
            raise AuthenticationFailed('Invalid credentials, try again')
        if not user.is_active:
            raise AuthenticationFailed('Account disabled, contact admin')
        
        # Return the user instance instead of a dictionary
        return user  # Return the Player instance directly

        
# new Logout serializer:
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
            
# --------------------------------------------------------------------------------------


class UpdateInfosSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Player
        fields = ['username', 'email', 'first_name', 'last_name', 'old_password', 'new_password']
        extra_kwargs = {
            'new_password': {'write_only': True},
        }

    # Validate username
    def validate_username(self, value):
        if Player.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    # Validate email
    def validate_email(self, value):
        if Player.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Email is already taken.")
        return value

    # Validate first name
    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("First name cannot be empty.")
        return value

    # Validate last name
    def validate_last_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Last name cannot be empty.")
        return value

    def save(self, **kwargs):
        # Handle password change
        old_password = self.validated_data.get('old_password', None)
        new_password = self.validated_data.get('new_password', None)

        # Check if the old password is provided and validate it
        if old_password and not authenticate(username=self.instance.username, password=old_password):
            raise serializers.ValidationError("Old password is incorrect.")

        # If a new password is provided, hash it before saving
        if new_password:
            self.instance.password = make_password(new_password)

        # Save the instance with other fields
        return super().save(**kwargs)

class DisplayNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['display_name']
    
    def validate_display_name(self, value):
        if Player.objects.filter(display_name=value).exists():
            raise serializers.ValidationError("This display name is already taken.")
        return value


class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['avatar']

    def validate_avatar(self, value):
        # Check file type
        if not value.name.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            raise serializers.ValidationError("File type is not supported. Please upload an image.")
        
        # Check file size (e.g., limit to 5 MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size should be less than 5 MB.")
        
        return value



# class FriendSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Player
#         fields = ['username', 'display_name', 'online_status']