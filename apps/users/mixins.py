
from django.shortcuts import redirect

class AnonymousRequiredMixin:

    """Mixin that requires the user to anonymous to access a page."""
    # Dispatch is traffic controller. Request goes to dispatch check if post -> call post; if get-> call get;
    # earliest convenient hook in a Class based view
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users-dashboard")

        # else process dispatch as it otherwise normally would
        return super().dispatch(request, *args, **kwargs)    