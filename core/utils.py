import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from .models import LinkPreview

DEFAULT_TIMEOUT = 3  # segundos, timeout seguro


def get_or_create_link_preview(url: str) -> LinkPreview:
    """
    Obtiene o crea una vista previa de enlace (OpenGraph).
    Cachea los resultados por 24h, con timeout seguro.
    """
    try:
        preview = LinkPreview.objects.get(url=url)
        if not preview.is_expired():
            return preview
    except LinkPreview.DoesNotExist:
        preview = None

    try:
        resp = requests.get(
            url,
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": "TwittorBot/1.0 (+educational)"}
        )
        resp.raise_for_status()
    except Exception:
        if preview:
            return preview
        return LinkPreview.objects.create(
            url=url,
            title="(Enlace no disponible)",
            description="No se pudo obtener vista previa.",
            image="",
            fetched_at=timezone.now()
        )

    soup = BeautifulSoup(resp.text, "html.parser")

    def og(prop, fallback=""):
        tag = soup.find("meta", property=f"og:{prop}")
        if tag and tag.get("content"):
            return tag["content"].strip()
        return fallback

    title = og("title")
    desc = og("description")
    img = og("image")

    # Si no hay título OG, usar el <title> normal
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Actualizar o crear
    if preview:
        preview.title = title
        preview.description = desc
        preview.image = img
        preview.fetched_at = timezone.now()
        preview.save()
        return preview

    return LinkPreview.objects.create(
        url=url,
        title=title,
        description=desc,
        image=img,
        fetched_at=timezone.now()
    )
