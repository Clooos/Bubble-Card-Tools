"""Music Assistant favorites ("like") access.

Home Assistant's Music Assistant integration exposes no favorite service:
liking an item is a Music Assistant SERVER command
(``music/favorites/add_item`` / ``music/favorites/remove_item``). This
module reaches the client the integration already connected and exposes the
two calls the Bubble Dashboard heart button needs:

- ``get_state``: is the item behind a uri a favorite right now, and under
  which LIBRARY item id (the only id ``remove_item`` accepts),
- ``set_state``: like / unlike it.

Music Assistant does the provider work itself: adding a favorite pulls the
item into the MA library and forwards the flag to every provider mapping
whose provider supports favorites edit — a Deezer track liked here comes
back liked in Deezer.

``music/item_by_uri`` always prefers the LIBRARY row when the item is in
the library, so a provider-flavoured answer (``provider != "library"``) is
the honest "not in the library, therefore not a favorite" signal.
"""
from __future__ import annotations

from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .ma_client import get_mass

# Live provider content: no stable library identity, the server rejects
# them as favorites. Reported as unsupported so the button just hides.
UNFAVORITABLE = {"audio_source", "sound_effect", "unknown", ""}


def _media_type(item: Any) -> str:
    """The item's media type as a plain string ('track', 'album'…)."""
    media_type = getattr(item, "media_type", None)
    return str(getattr(media_type, "value", media_type) or "")


async def get_state(
    hass: HomeAssistant,
    uri: str,
    config_entry_id: Optional[str] = None,
) -> dict[str, Any]:
    """Favorite status of one media item uri."""
    mass = get_mass(hass, config_entry_id)
    item = await mass.music.get_item_by_uri(uri)
    in_library = getattr(item, "provider", None) == "library"
    media_type = _media_type(item)
    return {
        "uri": uri,
        "media_type": media_type,
        "supported": media_type not in UNFAVORITABLE,
        "favorite": in_library and bool(getattr(item, "favorite", False)),
        # Only library items have one; None simply means "nothing to remove".
        "library_item_id": str(item.item_id) if in_library else None,
    }


async def set_state(
    hass: HomeAssistant,
    uri: str,
    favorite: bool,
    media_type: Optional[str] = None,
    library_item_id: Optional[str] = None,
    config_entry_id: Optional[str] = None,
) -> dict[str, Any]:
    """Like (``favorite=True``) or unlike one media item uri."""
    mass = get_mass(hass, config_entry_id)
    if favorite:
        # The uri is enough: the server resolves it, adds it to the library
        # and forwards the flag to the providers that support it.
        await mass.music.add_item_to_favorites(uri)
        return {"favorite": True}
    # Removal is addressed by library id. The caller normally passes back
    # what get_state reported; re-resolve when it did not (stale cache).
    if not library_item_id or not media_type:
        state = await get_state(hass, uri, config_entry_id)
        media_type = state["media_type"]
        library_item_id = state["library_item_id"]
    if not library_item_id:
        # Not in the library at all: already "not a favorite".
        return {"favorite": False}
    # The command is sent RAW instead of through
    # ``mass.music.remove_item_from_favorites`` because the two sides drifted
    # apart: the client Home Assistant 2026.6.1 pins (music-assistant-client
    # 1.3.5) still names the argument ``item_id``, while the server (2.9.9)
    # renamed it ``library_item_id`` — the helper's payload therefore arrives
    # with the parameter MISSING and the server rejects it with
    # "Value None ... is invalid for library_item_id".
    # Both names are sent: the server's parse_arguments is non-strict, so
    # whichever one it does not know is simply ignored, and this keeps
    # working across the skew in either direction.
    # media_type stays a plain string: the server coerces api command
    # arguments to their annotated types, so importing the MA models here
    # would buy nothing but an extra hard dependency.
    await mass.send_command(
        "music/favorites/remove_item",
        media_type=media_type,
        library_item_id=library_item_id,
        item_id=library_item_id,
    )
    return {"favorite": False}
