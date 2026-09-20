from django.contrib.auth import get_user_model

User = get_user_model()

class EmailAuthBackend:
    """
    Custom authentication backend.
    Allows users to log in using their email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 'username' here refers to whatever the user typed into the login field
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

# Django's authentication system stores the user's primary key in the session after login,
#  regardless of which authentication backend authenticated them.If we have custom authentication
# we will use email = username and find users by email else it will use username= username hence pk=user_id