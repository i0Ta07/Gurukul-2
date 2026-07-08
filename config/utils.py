from django.shortcuts import redirect
from django.contrib import messages
from typing import Literal
from django.http import HttpResponseRedirect

def create_message_and_redirect(request, message: str, url: str, code: Literal['info', 'success', 'error', 'warning'] = 'error')-> HttpResponseRedirect | None:
    """Create the message and redirects to the given URL."""
    # Dynamically get the correct messages function based on the 'code' string
    message_func = getattr(messages, code) # works as message.code
    message_func(request, message)
    return redirect(url)