from social_core.pipeline.partial import partial
from .models import User
from django.shortcuts import render

@partial
def get_user_type(strategy, backend, details, user=None, **kwargs):
    """
    Custom pipeline to ask the user_type, before creating a new user. 
    """
    # If existing user -> continue with the pipeline
    if user:
        return

    # If user submitted the form?
    user_type = strategy.request_data().get("user_type")
    if user_type:
        # Details save the email,first_name, last_name etc. Therefore we have to return the user_type to details 
        # the create_user method in custom UserManager will create the user object using this details.
        details['user_type'] = user_type
        return {'details': details}
    
    context = {
        'backend':backend.name,
        "user_type_choices": User.UserType.choices,
    }
    
    # Pause pipeline and render the form
    return render(strategy.request,"users/register/select_user_type.html",context,)