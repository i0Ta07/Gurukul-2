import magic
from django.core.exceptions import ValidationError
from typing import List

# Create a factory function that returns the actual validator, then call the factory function 
# that will return the callable i.e. the validator.
def validate_file_mimetype(allowed_mime_types: List[str]):
    def validator(upload):
        file_sample = upload.read(2048)
        upload.seek(0)         
        mime_type = magic.from_buffer(file_sample, mime=True)      
        
        if mime_type not in allowed_mime_types:
            raise ValidationError(
                f"Unsupported file type: {mime_type}. Allowed: {', '.join(allowed_mime_types)}"
            )
            
    return validator # Return the validator an actaul callable that can be used by django.