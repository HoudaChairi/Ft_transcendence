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
    
    def get_tokens(self, obj):
        user = Player.objects.get(username=obj['username'])
        return {
            'username': obj['username'],
            'refresh': user.tokens()['refresh'],
            'access': user.tokens()['access'],
        }
        
    class Meta:
        model = Player
        fields = ['username','password','tokens']
    
    def validate(self, attrs):
        username = attrs.get('username','')
        password = attrs.get('password','')
        user = auth.authenticate(username=username,password=password)
        if not user:
            raise AuthenticationFailed('Invalid credentials, try again')
        if not user.is_active:
            raise AuthenticationFailed('Account disabled, contact admin')
        return {
            'username': user.username,
            'tokens': user.tokens,
        }
        
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
    class Meta:
        model = Player
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True},  # We don't want to return the password in the response
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
        if not value:
            raise serializers.ValidationError("First name cannot be empty.")
        return value

    # Validate last name
    def validate_last_name(self, value):
        if not value:
            raise serializers.ValidationError("Last name cannot be empty.")
        return value

    # Override the save method to handle password hashing
    def save(self, **kwargs):
        password = self.validated_data.get('password', None)
        if password:
            # Hash the password before saving
            self.instance.password = make_password(password)
        
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
        # You can add validation for the uploaded file if needed (e.g., file size, type)
        return value



# class FriendSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Player
#         fields = ['username', 'display_name', 'online_status']