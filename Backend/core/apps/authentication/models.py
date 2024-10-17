from django.db import models
from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.tokens import RefreshToken


class Player(AbstractUser):
    username = models.CharField(max_length=20, unique=True, blank=False, null=False)
    email = models.CharField(max_length=50, unique=True, blank=False, null=False)
    display_name = models.CharField(max_length=30, unique=True, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='default_avatar.png')
    # wins = models.IntegerField(default=0)
    # losses = models.IntegerField(default=0)
    # friends = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='friend_set')

    def __str__(self):
        return self.username
    
    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return{
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }

# new: for friend user    
# class Friendship(models.Model):
#     user = models.ForeignKey(Player, related_name='friends', on_delete=models.CASCADE)
#     friend = models.ForeignKey(Player, related_name='friend_of', on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)

# # new: for match history
# class Match(models.Model):
#     user = models.ForeignKey(Player, related_name='matches', on_delete=models.CASCADE)
#     opponent = models.ForeignKey(Player, related_name='opponents', on_delete=models.CASCADE)
#     result = models.CharField(max_length=10)  # 'win' or 'loss'
#     date = models.DateTimeField(auto_now_add=True)


# class UserProfile(models.Model):
#     user = models.OneToOneField(Player, on_delete=models.CASCADE)
#     display_name = models.CharField(max_length=50, unique=True)
#     avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png')
#     wins = models.IntegerField(default=0)
#     losses = models.IntegerField(default=0)

# class Friend(models.Model):
#     user = models.ForeignKey(Player, related_name='friendships', on_delete=models.CASCADE)
#     friend = models.ForeignKey(Player, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)


# class Match(models.Model):
#     player1 = models.ForeignKey(Player, related_name='matches_as_player1', on_delete=models.CASCADE)
#     player2 = models.ForeignKey(Player, related_name='matches_as_player2', on_delete=models.CASCADE)
#     winner = models.ForeignKey(Player, related_name='matches_won', on_delete=models.CASCADE)
#     played_at = models.DateTimeField(auto_now_add=True)
# or:
# class Match(models.Model):
#     player1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='player1')
#     player2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='player2')
#     date = models.DateTimeField(auto_now_add=True)
#     result = models.CharField(max_length=20)  # Example: "Player1 won"

#     def __str__(self):
#         return f"Match {self.player1} vs {self.player2} on {self.date}"

# comment