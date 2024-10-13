from django.http import JsonResponse
from .models import Message
from authentication.models import Player


def room(request, user1, user2):
    room_name = '_'.join(sorted([user1, user2]))

    try:
        user1_obj = Player.objects.get(username=user1)
        user2_obj = Player.objects.get(username=user2)
    except Player.DoesNotExist:
        return JsonResponse({'error': 'Player not found.'}, status=404)

    messages = Message.objects.filter(
        sender__in=[user1_obj, user2_obj],
        receiver__in=[user1_obj, user2_obj]
    ).order_by('timestamp')

    messages_list = [
        {
            'sender': message.sender.username,
            'receiver': message.receiver.username,
            'content': message.content,
            # 'timestamp': message.timestamp.isoformat()
        }
        for message in messages
    ]

    return JsonResponse({
        # 'user1': user1,
        # 'user2': user2,
        # 'room_name': room_name,
        'messages': messages_list,
    })
