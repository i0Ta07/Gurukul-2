from django.shortcuts import render

def render_message_from_modal_to_page(request):
    """From a modal if you want to render the message in the main page."""
    response = render(request,"partials/messages.html")
    response["HX-Retarget"] = "#page-container" 
    response["HX-Reswap"] = "beforeend"
    return response