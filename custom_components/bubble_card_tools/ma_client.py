"""Shared access to the connected Music Assistant client.

Every Music Assistant feature of this integration (queue, favorites) needs
the same thing: the ``mass`` client object the Music Assistant integration
already connected for a loaded config entry. It lives on the entry's
``runtime_data``; nothing here opens its own connection.

Callers pass the config entry id of the player they act on (the Bubble
Dashboard reads it from the device registry, which non-admin sessions can
see). Without one the first loaded entry wins — correct for the single
server setup, and the only guess this module ever makes.
"""
from __future__ import annotations

from typing import Any, Optional

from homeassistant.core import HomeAssistant

MASS_DOMAIN = "music_assistant"


def get_mass(hass: HomeAssistant, config_entry_id: Optional[str] = None) -> Any:
    """The connected Music Assistant client of a loaded config entry."""
    entries = hass.config_entries.async_loaded_entries(MASS_DOMAIN)
    if not entries:
        raise ValueError("Music Assistant integration not loaded")
    if config_entry_id:
        for entry in entries:
            if entry.entry_id == config_entry_id:
                return entry.runtime_data.mass
    return entries[0].runtime_data.mass
