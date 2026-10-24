import os
from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def get_protected_storage_root():
    """
    Returns the absolute directory path where protected store digital assets are stored.
    In development/testing: <BASE_DIR>/protected_storage
    In production: PROTECTED_STORAGE_ROOT environment variable or /home3/nptorcom/protected_storage
    Crucially: This path is OUTSIDE the public web root (/public_html/media/).
    """
    env_root = os.environ.get("PROTECTED_STORAGE_ROOT")
    if env_root:
        return Path(env_root)
    if settings.DEBUG:
        return settings.BASE_DIR / "protected_storage"
    return Path("/home3/nptorcom/protected_storage")


class ProtectedFileSystemStorage(FileSystemStorage):
    """
    Protected filesystem storage backend.
    Disallows generating public URLs by raising ValueError on url().
    Ensures files can only be accessed through server-side authenticated streaming views.
    """
    def __init__(self, **kwargs):
        kwargs.setdefault("location", str(get_protected_storage_root()))
        super().__init__(**kwargs)

    def url(self, name):
        raise ValueError("Protected storage assets do not have a public URL.")


protected_storage = ProtectedFileSystemStorage()
