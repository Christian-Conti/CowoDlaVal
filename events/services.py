from django.db import transaction

from .models import EventImage


@transaction.atomic
def save_uploaded_images(event, uploaded_files):
    start_position = event.images.count()

    for offset, uploaded_file in enumerate(uploaded_files):
        EventImage.objects.create(
            event=event,
            original_name=uploaded_file.name[:255],
            content_type=uploaded_file.content_type or "application/octet-stream",
            data=uploaded_file.read(),
            position=start_position + offset,
        )
