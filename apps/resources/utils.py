from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat

def render_message_from_modal_to_page(request):
    """From a modal if you want to render the message in the main page."""
    response = render(request,"partials/messages.html")
    response["HX-Retarget"] = "#page-container" 
    response["HX-Reswap"] = "beforeend"
    return response

def clean_file_size(file,max_size:int):
    """max_size in megabytes"""
    max_size = max_size * 1024 * 1024 
    if file.size > max_size:
        raise ValidationError(
            f"File too large. Size must be under {filesizeformat(max_size)}."
            f"Current size is {filesizeformat(file.size)}."
        )
