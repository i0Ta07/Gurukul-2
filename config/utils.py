from django.shortcuts import redirect
from django.contrib import messages
from typing import Literal
from django.http import HttpResponse
from django.urls import reverse
from django.template.loader import render_to_string
from config.tasks import send_email_task

# Session
from apps.users.models import CustomSession
from django.contrib.auth import logout

def create_message_and_redirect(request, message: str, url: str, code: Literal['info', 'success', 'error', 'warning'] = 'error'):
    """Create the message and redirects to the given URL."""
    getattr(messages, code)(request, message)
    target = reverse(url)

    if request.htmx:
        response = HttpResponse(status=200)
        response["HX-Redirect"] = target
        return response

    return redirect(target)


def send_email(email_template_name:str,subject:str, receiver:list[str], context:dict,html_email_template_name:str = None):
    """
    Adds the send_email task to redis task queue for async compatibility. Celery worker takes the async task from the 
    message broker queue i.e. Redis and finishes them. Function is used to send reset or register emails asynchronously.
    """
    text_content = render_to_string(
        email_template_name,
        context=context,
    )

    html_content = None

    if html_email_template_name:
        html_content = render_to_string(
            html_email_template_name,
            context=context,
        )

    send_email_task.delay(subject, text_content, receiver, html_content,)

def logout_user_from_all_devices(request, user):
    """
    Instantly deletes all active sessions for the user at the database level.
    """
    # Flush all sessions stored in database for the current user
    CustomSession.objects.filter(user_id=user.id).delete()
    
    # Clear the cookie/session for the current request context
    logout(request)

