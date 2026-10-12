
import secrets,asyncio
from typing import List, Literal
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.template.loader import render_to_string
from channels.layers import get_channel_layer
# Base 64 encoding 
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.db.models import Count
from apps.users.models import Notification
from django.core.cache import cache

def get_register_token_key(token):
    return f'register:token:{token}'

def get_hex_token(length:int = 32):
    "Generates a 32 hexa-decimal token"
    return secrets.token_hex(length)

def encode_user_id(user_id: int) -> str:
    """Converts an integer user_id to a URL-safe base64 string."""
    return urlsafe_base64_encode(force_bytes(user_id))

def decode_user_id(encoded_id: str) -> int:
    """Decodes a URL-safe base64 string back to an integer user_id."""
    return int(force_str(urlsafe_base64_decode(encoded_id)))

# Use the old email as salt
def _get_signer(salt):
    """
    Same as django, we will use a changing field to invalidate the link after one use, such as email. 
    When changing email we will use the old email as salt.
    """
    return TimestampSigner(salt=salt)

def sign_str(unsigned:str,salt:str):
    signer = _get_signer(salt=salt)
    value = signer.sign(unsigned)
    return value

def unsign_str(signed:str,salt:str,max_age= 300):
    signer = _get_signer(salt=salt)
    try:
        value = signer.unsign(signed,max_age=max_age)
    except (SignatureExpired, BadSignature):
        return False
    return value

def get_changeEmail_key(user_id):
    return f'change_email:user:{user_id}'

def get_user_online_key(user_id):
    return f"users:online:{user_id}"

def get_notification_count_key(user_id):
    return f"users:{user_id}:notification-count"

async def create_notifications(users_id,body:str,url_path:str):
    """Create Notification objects."""
    notifications = [Notification(user_id=id, body=body,url_path = url_path) for id in users_id]
    await Notification.objects.abulk_create(notifications)
    
# have to implement batching if users_id is larger
async def send_notifications(users_id:List,body:str,url_path:str,code:Literal["info","error","success","warning"] = "info"):
    """Sends the notification to user's notification channel layer."""
    sends = []
    notification = render_to_string(template_name = "users/partials/notifications.html#notification",context={'notification':{'body':body,'code':code,'url_path':url_path}})
    channel_layer = get_channel_layer()

    for id in users_id:
        sends.append(
            channel_layer.group_send(
                f"user_notifications_{id}",
                {
                    "type":"sse",
                    "event_name": "notification-messages",
                    "html": notification.replace('\n','')
                }
            )
        )
    await asyncio.gather(*sends)

async def update_notification_icon(users_id:List):
    """Sends the updated count icon over the user's channel layer and update cache value too."""
    channel_layer = get_channel_layer()
    sends = []
    counts = Notification.objects.filter(
        user_id__in = users_id
    ).values("user_id").annotate(count = Count("id"))

    async for obj in counts: # create async for because of lazy evaluation of acount(); for is synchronous natively
        notification_icon = render_to_string(template_name="users/partials/notification_icon.html",context={"notification_count":obj['count']})
        sends.append(
            channel_layer.group_send(
                f"user_notifications_{obj['user_id']}",
                {
                    "type":"sse",
                    "event_name": "notification-count",
                    "html": notification_icon.replace('\n','')
                }
            )
        )
        key = get_notification_count_key(obj['user_id'])
        cur_count = await cache.aget(key,None)
        if cur_count is not None and cur_count != obj["count"]:
            await cache.aset(key,obj['count'])
    await asyncio.gather(*sends)

