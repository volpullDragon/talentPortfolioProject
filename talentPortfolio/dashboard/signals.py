"""Signal handlers for dashboard media file lifecycle."""

from pathlib import Path

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Files, Picture, Video


def _safe_delete_file(field_file) -> None:
    """Delete file from storage if present, ignoring missing files."""
    if not field_file:
        return
    storage = field_file.storage
    name = field_file.name
    if name and storage.exists(name):
        storage.delete(name)


def _cleanup_empty_parent_dirs(field_file) -> None:
    """Remove empty user media subdirectories after file deletion."""
    if not field_file:
        return

    file_path = Path(field_file.path)
    user_dir = file_path.parent
    media_type_dir = user_dir.parent

    if user_dir.exists() and user_dir.is_dir():
        try:
            user_dir.rmdir()
        except OSError:
            pass

    # Try to remove the media type directory only if it became empty.
    if media_type_dir.exists() and media_type_dir.is_dir():
        try:
            media_type_dir.rmdir()
        except OSError:
            pass


@receiver(post_delete, sender=Picture)
def delete_picture_file_on_row_delete(sender, instance, **kwargs):
    field_file = instance.image
    _safe_delete_file(field_file)
    _cleanup_empty_parent_dirs(field_file)


@receiver(post_delete, sender=Video)
def delete_video_file_on_row_delete(sender, instance, **kwargs):
    field_file = instance.video
    _safe_delete_file(field_file)
    _cleanup_empty_parent_dirs(field_file)


@receiver(post_delete, sender=Files)
def delete_document_file_on_row_delete(sender, instance, **kwargs):
    field_file = instance.file
    _safe_delete_file(field_file)
    _cleanup_empty_parent_dirs(field_file)


@receiver(pre_save, sender=Picture)
def delete_old_picture_on_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Picture.objects.get(pk=instance.pk)
    except Picture.DoesNotExist:
        return
    if old.image and old.image != instance.image:
        _safe_delete_file(old.image)


@receiver(pre_save, sender=Video)
def delete_old_video_on_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Video.objects.get(pk=instance.pk)
    except Video.DoesNotExist:
        return
    if old.video and old.video != instance.video:
        _safe_delete_file(old.video)


@receiver(pre_save, sender=Files)
def delete_old_document_on_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Files.objects.get(pk=instance.pk)
    except Files.DoesNotExist:
        return
    if old.file and old.file != instance.file:
        _safe_delete_file(old.file)
