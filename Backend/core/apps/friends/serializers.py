from rest_framework import serializers
from .models import Friendship

class FriendshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friendship
        fields = ['from_user', 'to_user', 'status']

class FriendshipListSerializer(serializers.ModelSerializer):
    from_user = serializers.StringRelatedField()  
    to_user = serializers.StringRelatedField()

    class Meta:
        model = Friendship
        fields = ['from_user', 'to_user', 'status']
