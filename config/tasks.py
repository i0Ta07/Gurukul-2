from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

# bind= True give access to self (the task type instance), to call self.retry()
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},) # if any exception occurs -> retry
def send_email_task(self, subject:str, text_content:str, receiver:list[str], html_content:str=None,):
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email= settings.EMAIL_HOST_USER,
        to=receiver,
    )

    if html_content:
        msg.attach_alternative(html_content, "text/html")

    msg.send()