"""Music Assistant play-queue access.

The ``music_assistant.get_queue`` service only returns the queue's
properties (current/next item, item COUNT): the full item list never
crosses the Home Assistant service layer. This module reaches the
Music Assistant client the integration already connected and exposes:

- the full queue item list (``player_queues/items``), serialized to the
  slim shape the Bubble Dashboard queue view needs (title, artists,
  duration, artwork through the MA image proxy),
- the queue commands the view acts with (play a given index, remove an
  item, move one next, clear).

Callers obtain the ``queue_id`` from ``music_assistant.get_queue`` first;
nothing here guesses entity -> queue mappings.
"""
from __future__ import annotations

from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .ma_client import get_mass as _get_mass


def _serialize_item(mass: Any, item: Any) -> dict[str, Any]:
    """One QueueItem -> the slim dict the queue view renders."""
    media_item = getattr(item, "media_item", None)
    artists = ""
    album = ""
    uri = None
    if media_item is not None:
        artists = ", ".join(
            artist.name
            for artist in getattr(media_item, "artists", None) or []
            if getattr(artist, "name", None)
        )
        album = getattr(getattr(media_item, "album", None), "name", "") or ""
        uri = getattr(media_item, "uri", None)
    try:
        image = mass.get_media_item_image_url(item)
    except Exception:  # never fail a whole queue for one artwork
        image = None
    return {
        "queue_item_id": item.queue_item_id,
        "name": item.name,
        "duration": item.duration,
        "artists": artists,
        "album": album,
        "uri": uri,
        "image": image,
    }


async def get_items(
    hass: HomeAssistant,
    queue_id: str,
    limit: int = 500,
    offset: int = 0,
    config_entry_id: Optional[str] = None,
) -> dict[str, Any]:
    """The queue's items, slim-serialized, in queue order."""
    mass = _get_mass(hass, config_entry_id)
    items = await mass.player_queues.get_queue_items(
        queue_id, limit=limit, offset=offset
    )
    return {"items": [_serialize_item(mass, item) for item in items]}


async def command(
    hass: HomeAssistant,
    queue_id: str,
    action: str,
    index: Optional[int] = None,
    item_id: Optional[str] = None,
    config_entry_id: Optional[str] = None,
) -> dict[str, Any]:
    """One queue mutation. ``index`` addresses play_index, ``item_id`` the rest."""
    mass = _get_mass(hass, config_entry_id)
    queues = mass.player_queues
    if action == "play_index":
        if index is None:
            raise ValueError("play_index requires an index")
        await queues.play_index(queue_id, index)
    elif action == "delete_item":
        target = item_id if item_id is not None else index
        if target is None:
            raise ValueError("delete_item requires an item_id or index")
        await queues.delete_item(queue_id, target)
    elif action == "move_next":
        if not item_id:
            raise ValueError("move_next requires an item_id")
        await queues.move_item(queue_id, item_id, 0)
    elif action == "clear":
        await queues.clear(queue_id)
    else:
        raise ValueError(f"Unknown queue action {action}")
    return {"ok": True}
