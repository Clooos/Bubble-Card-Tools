"""Music Assistant home recommendations (the "Discover" rows).

The Music Assistant server builds its whole Home screen from ONE api
command (``music/recommendations``): a list of RecommendationFolder
objects, one per row (Recently played, provider "made for you" playlists,
Deezer mood flows...). The Home Assistant integration exposes none of it,
so this module reaches the client the integration already connected,
exactly like the queue and favorites helpers.

Provider coverage is the server's job: every music provider contributes
its own rows and the server appends its library-derived defaults — the
result is provider-agnostic by construction.

Serialization is slim (the dashboard renders rows of tiles): folder name
plus translation_key (the frontend localizes the builtin keys it knows),
and per item uri/name/artists/media_type/image. Artwork goes through
``get_media_item_image_url`` — the same remote-safe imageproxy path as
the queue view.
"""
from __future__ import annotations

from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .ma_client import get_mass

MAX_ITEMS_PER_FOLDER = 25

# Only item types the dashboard can browse/play through the player route
# (media_player/browse_media + play_media). Nested BrowseFolder items
# (some providers ship folder rows) have no such route and are skipped.
SUPPORTED_ITEM_TYPES = {
    "track", "album", "artist", "playlist", "radio", "podcast", "audiobook",
}


def _plain(value: Any) -> str:
    """Enum-or-string -> plain string ('track', 'album'...)."""
    return str(getattr(value, "value", value) or "")


def _serialize_item(mass: Any, item: Any) -> Optional[dict[str, Any]]:
    """One recommendation item -> the slim dict a row tile renders."""
    uri = getattr(item, "uri", None)
    media_type = _plain(getattr(item, "media_type", ""))
    if not uri or media_type not in SUPPORTED_ITEM_TYPES:
        return None
    artists = ", ".join(
        artist.name
        for artist in getattr(item, "artists", None) or []
        if getattr(artist, "name", None)
    )
    try:
        image = mass.get_media_item_image_url(item)
    except Exception:  # never drop a whole row for one artwork
        image = None
    return {
        "uri": uri,
        "name": getattr(item, "name", "") or "",
        "artists": artists,
        "media_type": media_type,
        "is_playable": bool(getattr(item, "is_playable", True)),
        "image": image,
    }


async def get(
    hass: HomeAssistant,
    config_entry_id: Optional[str] = None,
) -> dict[str, Any]:
    """Every recommendation row of the server, slim-serialized."""
    mass = get_mass(hass, config_entry_id)
    folders = await mass.music.recommendations()
    out: list[dict[str, Any]] = []
    for folder in folders:
        items = []
        for item in (getattr(folder, "items", None) or [])[:MAX_ITEMS_PER_FOLDER]:
            serialized = _serialize_item(mass, item)
            if serialized:
                items.append(serialized)
        if not items:
            continue  # an empty row renders as nothing anyway
        translation_key = getattr(folder, "translation_key", None)
        out.append({
            "folder_id": str(getattr(folder, "item_id", "")),
            "provider": str(getattr(folder, "provider", "")),
            "name": getattr(folder, "name", "") or "",
            "translation_key": translation_key if isinstance(translation_key, str) else None,
            "items": items,
        })
    return {"folders": out}
