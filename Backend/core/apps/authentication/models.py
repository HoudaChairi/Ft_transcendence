from django.db import models
from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.tokens import RefreshToken
import pyotp


class Player(AbstractUser):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]   
    remote = models.BooleanField(default=False)
    username = models.CharField(max_length=20, unique=True, blank=False, null=False)
    email = models.EmailField(max_length=50, unique=True, blank=False, null=False)
    first_name = models.CharField(max_length=30, blank=True, null=True) 
    last_name = models.CharField(max_length=30, blank=True, null=True) 
    tournament_username = models.CharField(max_length=20, unique=True, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', default='textures/svg/ProfilePic.svg')
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    t_games = models.IntegerField(default=0)
    t_points = models.IntegerField(default=0)
    goals_f = models.IntegerField(default=0)
    goals_a = models.IntegerField(default=0)
    
    #2FA Fields
    is_2fa_enabled = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=32, blank=True, null=True)
    
    def verify_otp(self, otp):
        totp = pyotp.TOTP(self.otp_secret)
        return totp.verify(otp)
    
    def generate_otp_secret(self):
        self.otp_secret = pyotp.random_base32()
        self.save()

    def get_avatar_url(self):
        if 'textures/svg/' in self.avatar.name or self.avatar.name.startswith('http'):
            return f'{self.avatar}'
        return f'/media/{self.avatar}'

    def __str__(self):
        return self.username
    
    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }


class Match(models.Model):
    player1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_player1')
    player2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_player2')
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, related_name='matches_won', null=True, blank=True)
    loser = models.ForeignKey(Player, on_delete=models.SET_NULL, related_name='matches_loss', null=True, blank=True)
    date_played = models.DateTimeField(auto_now_add=True)
    score_player1 = models.IntegerField()
    score_player2 = models.IntegerField()

    def __str__(self):
        return f"Match: {self.player1} vs {self.player2} on {self.date_played}"