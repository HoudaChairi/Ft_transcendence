from rest_framework import serializers
from .models import Player
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.hashers import check_password


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
    )
    confirmPassword = serializers.CharField(
        write_only=True,
        required=True,
    )

    class Meta:
        model = Player
        fields = ['email', 'username', 'password', 'confirmPassword']
        extra_kwargs = {
            'username': {'required': True},
        }

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as exc:
            raise serializers.ValidationError(str(exc))
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirmPassword']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    def create(self, validated_data):
        # Remove confirmPassword from validated_data before creating user
        validated_data.pop('confirmPassword', None)
        user = Player.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
        )
        # Additional user setup can be done here
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
# class LogoutSerializer(serializers.Serializer):
#     refresh = serializers.CharField()
#     def validate(self, attrs):
#         self.token = attrs['refresh']
#         return attrs
#     def save(self, **kwargs):
#         try:
#             RefreshToken(self.token).blacklist()
#         except TokenError:
#             self.fail('bad_token')
    
# --------------------------------------------------------------------------------------


class DisplayNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['display_name']
    
    def validate_display_name(self, value):
        if Player.objects.filter(display_name=value).exists():
            raise serializers.ValidationError("This display name is already taken.")
        return value


#  after:  for display name, avatar,
# class UpdateProfileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Player
#         fields = ['email', 'username', 'display_name', 'avatar']
    
#     def validate_username(self, value):
#         if not value.isalnum():
#             raise serializers.ValidationError("Username must be alphanumeric.")
#         return value
    
#     def validate_display_name(self, value):
#         if Player.objects.filter(display_name=value).exists():
#             raise serializers.ValidationError("Display name is already taken.")
#         return value

# class FriendSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Player
#         fields = ['username', 'display_name', 'online_status']