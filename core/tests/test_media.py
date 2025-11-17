import shutil
import pytest
from django.conf import settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import Tweet, TweetImage


# =============== AUTOFIX: MEDIA ROOT TEMPORAL PARA TODOS LOS TESTS ===============
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


# =============================== HELPERS =========================================
def make_small_png_bytes():
    """
    Crea un PNG muy pequeño válido en memoria (1x1).
    """
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDATx\xdacd\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8f\xb1"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def make_big_jpg_bytes(size_mb=6):
    """
    Genera bytes 'grandes' para disparar el validador de tamaño (>5MB).
    No validamos contenido JPEG real; solo el tamaño del archivo.
    """
    return b"0" * (size_mb * 1024 * 1024)


# =============================== FIXTURES ========================================
@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="kevin12", password="segura1234")


@pytest.fixture
def auth_client(client, user):
    assert client.login(username="kevin12", password="segura1234")
    return client


# =============================== TESTS ===========================================

# 1) Subida múltiple exitosa mediante formset (3 imágenes)
@pytest.mark.django_db
def test_upload_multiple_images_via_formset(auth_client):
    url = reverse("timeline")

    # Management form del formset (prefijo por defecto: 'form')
    data = {
        "content": "Good games",
        "form-TOTAL_FORMS": "4",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "4",

        # Archivos + coordenadas de cropping mínimas para validar el formset
        "form-0-image": SimpleUploadedFile("a.png", make_small_png_bytes(), content_type="image/png"),
        "form-0-cropping": "0,0,1,1",

        "form-1-image": SimpleUploadedFile("b.png", make_small_png_bytes(), content_type="image/png"),
        "form-1-cropping": "0,0,1,1",

        "form-2-image": SimpleUploadedFile("c.png", make_small_png_bytes(), content_type="image/png"),
        "form-2-cropping": "0,0,1,1",
        # form-3-image/cropping vacíos a propósito
    }

    resp = auth_client.post(url, data=data, follow=True)
    assert resp.status_code == 200

    tw = Tweet.objects.latest("id")
    assert tw.content == "Good games"
    assert TweetImage.objects.filter(tweet=tw).count() == 3


# 2) Rechaza extensión inválida
@pytest.mark.django_db
def test_reject_invalid_extension(auth_client):
    url = reverse("timeline")

    data = {
        "content": "archivo invalido",
        "form-TOTAL_FORMS": "4",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "4",

        # extensión no permitida
        "form-0-image": SimpleUploadedFile("mal.txt", b"noesimagen", content_type="text/plain"),
        "form-0-cropping": "0,0,1,1",
    }

    resp = auth_client.post(url, data=data)
    # Debe renderizar con errores (sin redirigir)
    assert resp.status_code == 200
    assert Tweet.objects.count() == 0
    assert TweetImage.objects.count() == 0


# 3) Rechaza tamaño > 5 MB
@pytest.mark.django_db
def test_reject_oversize_image(auth_client):
    url = reverse("timeline")

    data = {
        "content": "muy grande",
        "form-TOTAL_FORMS": "4",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "4",

        "form-0-image": SimpleUploadedFile("grande.jpg", make_big_jpg_bytes(6), content_type="image/jpeg"),
        "form-0-cropping": "0,0,1,1",
    }

    resp = auth_client.post(url, data=data)
    assert resp.status_code == 200
    assert Tweet.objects.count() == 0
    assert TweetImage.objects.count() == 0


# 4) Borrado en cascada: eliminar Tweet elimina sus imágenes
@pytest.mark.django_db
def test_delete_tweet_cascades_images(auth_client, user):
    tw = Tweet.objects.create(user=user, content="con imagenes")
    for name in ("1.png", "2.png"):
        TweetImage.objects.create(
            tweet=tw,
            image=SimpleUploadedFile(name, make_small_png_bytes(), content_type="image/png")
        )
    assert TweetImage.objects.filter(tweet=tw).count() == 2

    tw_id = tw.id  # Guarda el id antes de borrar
    tw.delete()

    assert Tweet.objects.filter(id=tw_id).count() == 0
    assert TweetImage.objects.filter(tweet_id=tw_id).count() == 0


