from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

@shared_task()
def send_email_task(subject,text_content,receiver,html_content):
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=(receiver,),
    )
    msg.attach_alternative( html_content,"text/html")
    msg.send()
