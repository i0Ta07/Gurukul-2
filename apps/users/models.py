from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
import uuid,os

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

    # If your Friend model already ensures both-way friendship on ACCEPTED — you're good. 
    # means Bob-> alice means bob is a freind of alice and alice is a friend of bob
    # solution: When query use Friendship.objects.filter(Q(from_user=user) | Q(to_user=user),status=Friendship.Status.ACCEPTED,)
    friends = models.ManyToManyField('self', through='Friendship')

    def user_directory_path(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"profile_photos/{uuid.uuid4()}.{extension.lower()}"

    profile_photo = models.ImageField(
        # If the image is None show the default from static
        # Make sure using validators that image extension are png, use validators for book, notes uploads
        upload_to=user_directory_path,
        blank=True
    )
    bio = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_type})"

class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = 'P',_('Pending')
        ACCEPTED = 'A',_('Accepted')
        # If rejected we delete the relationship object if rejected

    from_user = models.ForeignKey(User, related_name='sent_requests', related_query_name='sent_request',on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests',related_query_name='received_request', on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=Status, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
        
    class Meta:
        ordering = ['-created_at']
        # In views.py check both ['from_user', 'to_user'],['to_user','from_user] exists if yes then auto-accept, if already exists
        # In views check if the user is not sending a freind request to himself.
        # implement the "send friend request" with transaction.atomic()
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                name='unique_friend_req'
            ),
            models.CheckConstraint(
                condition=~models.Q(from_user=models.F("to_user")),
                name="prevent_self_req",
            )
        ]

    # full_clean() calls clean() and full_clean() is called only when input come from model.form or forms.form or Django Admin
    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.get_status_display()})"

