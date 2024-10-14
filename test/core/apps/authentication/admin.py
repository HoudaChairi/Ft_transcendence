from django.contrib import admin
from .models import Player
from django.contrib.auth.admin import UserAdmin

admin.site.register(Player, UserAdmin)
