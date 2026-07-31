
import secrets
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.contrib.sites.shortcuts import get_current_site

# Base 64 encoding 
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

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

def get_website_context(request,token:str):
    return  {
        'domain':get_current_site(request).domain,
        'token':token,
        'protocol':'https' if request.is_secure() else 'http'
    }



