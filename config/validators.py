from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
import magic
from typing import List

# implement __call__ and __init__ for every validator
@deconstructible # important for serialization of args
class ValidateFileMimeType:
    def __init__(self, allowed_mime_types: List[str]):
        self.allowed_mime_types = allowed_mime_types

    def __call__(self, upload):
        file_sample = upload.read(2048)
        upload.seek(0)

        mime_type = magic.from_buffer(file_sample, mime=True)

        if mime_type not in self.allowed_mime_types:
            raise ValidationError(
                f"Unsupported file type: {mime_type}. "
                f"Allowed: {', '.join(self.allowed_mime_types)}"
            )

pdf_validator = ValidateFileMimeType(allowed_mime_types=['application/pdf'])
excel_validator = ValidateFileMimeType(allowed_mime_types=['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'])
image_validator = ValidateFileMimeType(allowed_mime_types=['image/png', 'image/jpeg'])