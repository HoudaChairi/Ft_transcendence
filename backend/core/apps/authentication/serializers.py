from rest_framework import serializers
from .models import CustomUser
# new
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

# new Register serializer:
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'display_name', 'email']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            display_name=validated_data['display_name']
        )
        return user
    
# new Login serializer:
class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=255, min_length=3) # email or username
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    tokens = serializers.SerializerMethodField()
    def get_tokens(self, obj):
        user = CustomUser.objects.get(username=obj['username'])
        return {
            'refresh': user.tokens()['refresh'],
            'access': user.tokens()['access'],
        }
    class Meta:
        model = CustomUser
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
            'email': user.email,
            'username': user.username,
            'tokens': user.tokens,
        }
        
# new Logout serializer:
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs
    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('bad_token')
    
# --------------------------------------------------------------------------------------
#  after:  for display name, avatar,
class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'display_name', 'avatar']
    
    def validate_username(self, value):
        if not value.isalnum():
            raise serializers.ValidationError("Username must be alphanumeric.")
        return value
    
    def validate_display_name(self, value):
        if CustomUser.objects.filter(display_name=value).exists():
            raise serializers.ValidationError("Display name is already taken.")
        return value


# class FriendSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ['username', 'display_name', 'online_status']