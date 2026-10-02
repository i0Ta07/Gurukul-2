from django.db import models
from django.contrib.auth.models import AbstractUser,UserManager
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
import uuid,os
from PIL import Image
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models
from io import BytesIO
from django.core.files.base import ContentFile

class User(AbstractUser):
    email = models.EmailField(_('Email Address'),unique=True, blank=False)
    class UserType(models.TextChoices):
        TEACHER = 'T',_('Teacher')
        STUDENT = 'S',_('Student')

    # Use splitPhoneNumberFeild in form
    phone_number = PhoneNumberField(blank=True,unique=True,null=True)

    # Give friends notifications for birthdays
    date_of_birth = models.DateField(null=True,blank=True)
    user_type = models.CharField(
        max_length=1,
        choices=UserType,
        default=UserType.STUDENT,
    )

    def user_directory_path(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"users/profile_photos/{instance.id}/{uuid.uuid4()}{extension.lower()}"

    profile_photo = models.ImageField(
        # If the image is None show the default from static
        # Make sure using validators that image extension are png, use validators for book, notes uploads
        upload_to=user_directory_path,
        blank=True
    )
    bio = models.CharField(max_length=100, blank=True)
    last_seen = models.DateTimeField()

    REQUIRED_FIELDS = ['email']
    
    objects = UserManager()

    def __str__(self):
        return f"{self.get_full_name()} ({self.user_type})"

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        photo_being_updated = (
            update_fields is None or "profile_photo" in update_fields
        )

        old_photo = None

        if self.pk and photo_being_updated:
            old_photo = User.objects.get(pk=self.pk).profile_photo

        if self.profile_photo and photo_being_updated: # Here self refers to the new object in memory
            image = Image.open(self.profile_photo)
            image.thumbnail((100, 100))

            buffer = BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)

            self.profile_photo = ContentFile(
                buffer.getvalue(),
                name="profile_photo.png",
            )

        super().save(*args, **kwargs)

        if (
            photo_being_updated
            and old_photo
            and old_photo.name != self.profile_photo.name # If no updated_fields are provided, this prevents from deleting the old image.
        ):
            old_photo.delete(save=False)


class CustomSession(AbstractBaseSession):
    # Add a dedicated, indexed column for the user ID
    user_id = models.IntegerField(null=True, db_index=True)

    @classmethod
    def get_session_store_class(cls):
        return SessionStore


class SessionStore(DBStore):
    @classmethod
    def get_model_class(cls):
        return CustomSession

    def create_model_instance(self, data):
        """
        Extract the user ID from the session data dictionary 
        and save it to our custom database column.
        """
        obj = super().create_model_instance(data)
        try:
            user_id = int(data.get("_auth_user_id"))
        except (ValueError, TypeError):
            user_id = None
        obj.user_id = user_id
        return obj