"""Non-recursive Jellyfin browsing that mirrors the server's own structure.

Home Assistant's built-in Jellyfin media source browses with
``Recursive=true`` queries and drops any playable item whose file path has
no guessable mime type. Both hurt fidelity:

- recursive ``IncludeItemTypes=Series`` queries can surface series that the
  Jellyfin UI does NOT show inside that library (merged/misplaced items
  become phantom folders full of unrelated seasons),
- the mime filter silently hides whole seasons of episodes.

This module browses through the SAME api client the Jellyfin integration
already authenticated, but strictly parent -> direct children (exactly what
the Jellyfin web UI requests), with server-side sorting and no mime
filtering. Results are shaped like ``media_source/browse_media`` responses
and keep ``media-source://jellyfin/<id>`` content ids, so playback still
resolves through the standard Home Assistant pipeline.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

JELLYFIN_DOMAIN = "jellyfin"
URI_PREFIX = "media-source://jellyfin"
MAX_IMAGE_WIDTH = 500
CHILD_LIMIT = 5000

# Jellyfin item Type -> (media_class, can_play, can_expand)
ITEM_CLASS: dict[str, tuple[str, bool, bool]] = {
    "CollectionFolder": ("directory", False, True),
    "UserView": ("directory", False, True),
    "Folder": ("directory", False, True),
    "BoxSet": ("directory", False, True),
    "PhotoAlbum": ("directory", False, True),
    "Series": ("tv_show", False, True),
    "Season": ("season", False, True),
    "Episode": ("episode", True, False),
    "Movie": ("movie", True, False),
    "Video": ("video", True, False),
    "MusicVideo": ("video", True, False),
    "Trailer": ("video", True, False),
    "MusicArtist": ("artist", False, True),
    "MusicAlbum": ("album", False, True),
    "Audio": ("track", True, False),
    "Playlist": ("playlist", False, True),
}

# Library collection types that make no sense in a media browser.
DENY_COLLECTION_TYPES = {"books", "livetv", "folders"}


def _get_api(hass: HomeAssistant) -> Any:
    """Return the jellyfin api of the loaded Jellyfin config entry."""
    entries = hass.config_entries.async_loaded_entries(JELLYFIN_DOMAIN)
    if not entries:
        raise ValueError("Jellyfin integration not loaded")
    return entries[0].runtime_data.api_client.jellyfin


def _item_id(media_content_id: str) -> Optional[str]:
    """media-source://jellyfin[/<id>] -> <id> or None for the root."""
    if media_content_id in ("", URI_PREFIX):
        return None
    if media_content_id.startswith(f"{URI_PREFIX}/"):
        item_id = media_content_id[len(URI_PREFIX) + 1 :]
        return item_id or None
    # Raw Jellyfin id (tolerated so callers can pass either form).
    if "://" not in media_content_id:
        return media_content_id
    raise ValueError(f"Not a Jellyfin media id: {media_content_id}")


def _thumbnail(api: Any, item: dict[str, Any]) -> Optional[str]:
    """Primary artwork URL; episodes fall back to their series poster."""
    if "Primary" in (item.get("ImageTags") or {}):
        return str(api.artwork(item["Id"], "Primary", MAX_IMAGE_WIDTH))
    if item.get("SeriesPrimaryImageTag") and item.get("SeriesId"):
        return str(api.artwork(item["SeriesId"], "Primary", MAX_IMAGE_WIDTH))
    return None


def _content_type(item: dict[str, Any]) -> str:
    media_type = item.get("MediaType")
    if media_type == "Audio":
        return "audio"
    if media_type == "Video":
        return "video"
    return ""


def _to_entry(api: Any, item: dict[str, Any]) -> dict[str, Any]:
    """One Jellyfin item -> one media_source-shaped browse child."""
    media_class, can_play, can_expand = ITEM_CLASS.get(
        item.get("Type", ""), ("directory", False, True)
    )
    title = item.get("Name") or ""
    # "S01E05 - Title" style labels keep episode lists readable without the
    # surrounding season context the Jellyfin UI provides.
    if item.get("Type") == "Episode" and item.get("IndexNumber") is not None:
        season_no = item.get("ParentIndexNumber")
        prefix = (
            f"S{season_no:02d}E{item['IndexNumber']:02d}"
            if isinstance(season_no, int)
            else f"E{item['IndexNumber']:02d}"
        )
        title = f"{prefix} · {title}" if title else prefix
    return {
        "title": title,
        "media_content_id": f"{URI_PREFIX}/{item['Id']}",
        "media_content_type": _content_type(item),
        "media_class": media_class,
        "can_play": can_play,
        "can_expand": can_expand,
        "thumbnail": _thumbnail(api, item),
        "children_media_class": None,
    }


def _children_params(item: dict[str, Any]) -> dict[str, Any]:
    """Direct-children query for a parent item, Jellyfin-UI style sorting."""
    item_type = item.get("Type")
    parent_id = item["Id"]
    if item_type == "MusicAlbum":
        return {
            "ParentId": parent_id,
            "SortBy": "ParentIndexNumber,IndexNumber,SortName",
            "SortOrder": "Ascending",
        }
    if item_type == "MusicArtist":
        # Artists are logical items: their albums are linked, not nested.
        return {
            "ArtistIds": parent_id,
            "Recursive": "true",
            "IncludeItemTypes": "MusicAlbum",
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    if item_type == "CollectionFolder" and item.get("CollectionType") == "music":
        # Match the Jellyfin UI's default Albums view for music libraries;
        # plain folder walking would show raw directory names instead.
        return {
            "ParentId": parent_id,
            "Recursive": "true",
            "IncludeItemTypes": "MusicAlbum",
            "SortBy": "AlbumArtist,SortName",
            "SortOrder": "Ascending",
        }
    # Libraries, folders, boxsets: EXACTLY the direct children, folders
    # first, like the Jellyfin UI. Never recursive: recursion is what
    # manufactured phantom series in libraries they do not belong to.
    return {"ParentId": parent_id, "SortBy": "IsFolder,SortName", "SortOrder": "Ascending"}


def _dominant_class(children: list[dict[str, Any]]) -> Optional[str]:
    counts: dict[str, int] = {}
    for child in children:
        counts[child["media_class"]] = counts.get(child["media_class"], 0) + 1
    return max(counts, key=counts.get) if counts else None


def _browse_root(api: Any) -> dict[str, Any]:
    """The user's libraries, every browsable collection type included."""
    response = api.get_media_folders()
    children = [
        _to_entry(api, library)
        for library in response.get("Items", [])
        if (library.get("CollectionType") or "") not in DENY_COLLECTION_TYPES
    ]
    return {
        "title": "Jellyfin",
        "media_content_id": URI_PREFIX,
        "media_content_type": "",
        "media_class": "directory",
        "can_play": False,
        "can_expand": True,
        "thumbnail": None,
        "children_media_class": _dominant_class(children),
        "children": children,
    }


def browse(hass_ref: HomeAssistant, media_content_id: str) -> dict[str, Any]:
    """Blocking browse (executor): parent item + its direct children."""
    api = _get_api(hass_ref)
    item_id = _item_id(media_content_id)
    if item_id is None:
        return _browse_root(api)

    item = api.get_item(item_id)
    if not item or "Id" not in item:
        raise ValueError(f"Unknown Jellyfin item {item_id}")

    item_type = item.get("Type")
    if item_type == "Series":
        # The Jellyfin UI's own series page: /Shows/{id}/Seasons follows the
        # logical SeriesId links (virtual seasons included) instead of the
        # physical folder ancestry, which stays correct even when the
        # server's ancestry data is damaged (10.11 upgrade corruption).
        response = api.shows(f"/{item_id}/Seasons", {"UserId": "{UserId}"})
    elif item_type == "Season" and item.get("SeriesId"):
        # Same logic for episodes: /Shows/{series}/Episodes?SeasonId=...
        # is what the Jellyfin UI lists, already in playback order.
        response = api.shows(
            f"/{item['SeriesId']}/Episodes",
            {"SeasonId": item_id, "UserId": "{UserId}"},
        )
    elif item_type == "Playlist":
        # Playlist order is user-defined: ParentId queries would re-sort it.
        response = api.get_playlist_items(item_id, limit=CHILD_LIMIT)
    else:
        params = _children_params(item)
        params["Limit"] = CHILD_LIMIT
        response = api.user_items("", params)

    children = [_to_entry(api, child) for child in response.get("Items", [])]
    entry = _to_entry(api, item)
    entry["children_media_class"] = _dominant_class(children)
    entry["children"] = children
    return entry
