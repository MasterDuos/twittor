import os
import shutil
import pytest
from django.conf import settings

@pytest.fixture(autouse=True)
def _temp_media(tmp_path):
    """
    Redirige MEDIA_ROOT a un directorio temporal para no ensuciar /media real.
    Se aplica automáticamente a todos los tests.
    """
    original_media = settings.MEDIA_ROOT
    tmp_media = tmp_path / "media"
    tmp_media.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = str(tmp_media)
    yield
    settings.MEDIA_ROOT = original_media
    shutil.rmtree(tmp_media, ignore_errors=True)
