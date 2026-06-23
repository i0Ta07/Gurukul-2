from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
import uuid,os
from PIL import Image

from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models

# AbstractUser's default manager expects a username. If you remove it, Django's createsuperuser can behave unexpectedly.
# Create a custom manager

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)



# AbstractUser already contains first_name, last_name, is_staff etc. In AbstractUser only username and password are mandotory
# So we have to override the fields we want necessary
class User(AbstractUser):
    username = None
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
        return f"profile_photos/{instance.id}/{uuid.uuid4()}{extension.lower()}"

    profile_photo = models.ImageField(
        # If the image is None show the default from static
        # Make sure using validators that image extension are png, use validators for book, notes uploads
        upload_to=user_directory_path,
        blank=True
    )
    bio = models.CharField(max_length=100, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_type})"
    
    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_obj = User.objects.get(pk=self.pk)
                # If a new file is being uploaded, delete the old file
                if old_obj.profile_photo and self.profile_photo != old_obj.profile_photo:
                    old_obj.profile_photo.delete(save=False)
            except User.DoesNotExist:
                pass
                
        super().save(*args, **kwargs)

        if self.profile_photo:
            img = Image.open(self.profile_photo.path)

            if img.height > 100 or img.width > 100:
                img.thumbnail((100, 100))
                img.save(self.profile_photo.path)


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