
"""WebSocket API for Bubble Card Tools."""
from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry

from . import list_modules, read_module, read_all_modules, write_module, delete_module

_LOGGER = logging.getLogger(__name__)

SCHEMA_LIST = {vol.Required("type"): "bubble_card_tools/list_modules"}
SCHEMA_READ = {vol.Required("type"): "bubble_card_tools/read_module", vol.Required("name"): str}
SCHEMA_READ_ALL = {vol.Required("type"): "bubble_card_tools/read_all_modules", vol.Optional("names"): [str]}
SCHEMA_WRITE = {vol.Required("type"): "bubble_card_tools/write_module", vol.Required("name"): str, vol.Required("content"): str}
SCHEMA_DELETE = {vol.Required("type"): "bubble_card_tools/delete_module", vol.Required("name"): str}
SCHEMA_MEDIA_BROWSE = {vol.Required("type"): "bubble_card_tools/media_browse", vol.Optional("media_content_id", default=""): str}
SCHEMA_MA_QUEUE_ITEMS = {
    vol.Required("type"): "bubble_card_tools/ma_queue_items",
    vol.Required("queue_id"): str,
    vol.Optional("limit", default=500): vol.Coerce(int),
    vol.Optional("offset", default=0): vol.Coerce(int),
    vol.Optional("config_entry_id"): str,
}
SCHEMA_MA_QUEUE_COMMAND = {
    vol.Required("type"): "bubble_card_tools/ma_queue_command",
    vol.Required("queue_id"): str,
    vol.Required("command"): str,
    vol.Optional("index"): vol.Coerce(int),
    vol.Optional("item_id"): str,
    vol.Optional("config_entry_id"): str,
}
SCHEMA_MA_RECOMMENDATIONS = {
    vol.Required("type"): "bubble_card_tools/ma_recommendations",
    vol.Optional("config_entry_id"): str,
}
SCHEMA_MA_FAVORITE_STATE = {
    vol.Required("type"): "bubble_card_tools/ma_favorite_state",
    vol.Required("uri"): str,
    vol.Optional("config_entry_id"): str,
}
SCHEMA_TRANSLATE = {
    vol.Required("type"): "bubble_card_tools/translate",
    vol.Required("text"): str,
    vol.Required("target"): str,
}
SCHEMA_MA_FAVORITE_SET = {
    vol.Required("type"): "bubble_card_tools/ma_favorite_set",
    vol.Required("uri"): str,
    vol.Required("favorite"): bool,
    vol.Optional("media_type"): str,
    vol.Optional("library_item_id"): str,
    vol.Optional("config_entry_id"): str,
}

def async_register_api(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Define and register websocket commands."""

    @websocket_api.websocket_command(SCHEMA_LIST)
    @websocket_api.async_response
    async def ws_list(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        try:
            files = await hass.async_add_executor_job(list_modules, hass, entry)
            connection.send_result(msg["id"], {"files": files})
        except Exception as err:
            _LOGGER.debug("List failed: %s", err)
            connection.send_error(msg["id"], "list_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_READ)
    @websocket_api.async_response
    async def ws_read(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        name = msg["name"]
        try:
            data = await hass.async_add_executor_job(read_module, hass, entry, name)
            connection.send_result(msg["id"], data)
        except Exception as err:
            _LOGGER.debug("Read failed for %s: %s", name, err)
            connection.send_error(msg["id"], "read_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_READ_ALL)
    @websocket_api.async_response
    async def ws_read_all(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        names = msg.get("names")
        try:
            modules = await hass.async_add_executor_job(read_all_modules, hass, entry, names)
            connection.send_result(msg["id"], {"modules": modules})
        except Exception as err:
            _LOGGER.debug("Bulk read failed: %s", err)
            connection.send_error(msg["id"], "read_all_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_WRITE)
    @websocket_api.async_response
    async def ws_write(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        name = msg["name"]
        content = msg["content"]
        try:
            result = await hass.async_add_executor_job(write_module, hass, entry, name, content)
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("Write failed for %s: %s", name, err)
            connection.send_error(msg["id"], "write_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_DELETE)
    @websocket_api.async_response
    async def ws_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        name = msg["name"]
        try:
            result = await hass.async_add_executor_job(delete_module, hass, entry, name)
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("Delete failed for %s: %s", name, err)
            connection.send_error(msg["id"], "delete_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_MEDIA_BROWSE)
    @websocket_api.async_response
    async def ws_media_browse(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        from . import media_browse

        media_content_id = msg.get("media_content_id", "")
        try:
            result = await hass.async_add_executor_job(media_browse.browse, hass, media_content_id)
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("Media browse failed for %s: %s", media_content_id, err)
            connection.send_error(msg["id"], "browse_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_MA_QUEUE_ITEMS)
    @websocket_api.async_response
    async def ws_ma_queue_items(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        from . import ma_queue

        try:
            result = await ma_queue.get_items(
                hass,
                msg["queue_id"],
                limit=msg.get("limit", 500),
                offset=msg.get("offset", 0),
                config_entry_id=msg.get("config_entry_id"),
            )
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("MA queue items failed for %s: %s", msg.get("queue_id"), err)
            connection.send_error(msg["id"], "queue_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_MA_QUEUE_COMMAND)
    @websocket_api.async_response
    async def ws_ma_queue_command(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        from . import ma_queue

        try:
            result = await ma_queue.command(
                hass,
                msg["queue_id"],
                msg["command"],
                index=msg.get("index"),
                item_id=msg.get("item_id"),
                config_entry_id=msg.get("config_entry_id"),
            )
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("MA queue command failed for %s: %s", msg.get("queue_id"), err)
            connection.send_error(msg["id"], "queue_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_MA_RECOMMENDATIONS)
    @websocket_api.async_response
    async def ws_ma_recommendations(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        from . import ma_recommendations

        try:
            result = await ma_recommendations.get(
                hass,
                config_entry_id=msg.get("config_entry_id"),
            )
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("MA recommendations failed: %s", err)
            connection.send_error(msg["id"], "recommendations_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_MA_FAVORITE_STATE)
    @websocket_api.async_response
    async def ws_ma_favorite_state(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        from . import ma_favorites

        try:
            result = await ma_favorites.get_state(
                hass,
                msg["uri"],
                config_entry_id=msg.get("config_entry_id"),
            )
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("MA favorite state failed for %s: %s", msg.get("uri"), err)
            connection.send_error(msg["id"], "favorite_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_MA_FAVORITE_SET)
    @websocket_api.async_response
    async def ws_ma_favorite_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        from . import ma_favorites

        try:
            result = await ma_favorites.set_state(
                hass,
                msg["uri"],
                msg["favorite"],
                media_type=msg.get("media_type"),
                library_item_id=msg.get("library_item_id"),
                config_entry_id=msg.get("config_entry_id"),
            )
            connection.send_result(msg["id"], result)
        except Exception as err:
            _LOGGER.debug("MA favorite set failed for %s: %s", msg.get("uri"), err)
            connection.send_error(msg["id"], "favorite_failed", str(err))

    @websocket_api.websocket_command(SCHEMA_TRANSLATE)
    @websocket_api.async_response
    async def ws_translate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: Dict[str, Any]) -> None:
        from .translate import async_translate
        try:
            translated = await async_translate(hass, msg["text"], msg["target"])
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Translation command failed: %s", err)
            translated = None
        connection.send_result(msg["id"], {"translated": translated})

    websocket_api.async_register_command(hass, ws_ma_recommendations)
    websocket_api.async_register_command(hass, ws_ma_favorite_state)
    websocket_api.async_register_command(hass, ws_ma_favorite_set)
    websocket_api.async_register_command(hass, ws_ma_queue_items)
    websocket_api.async_register_command(hass, ws_ma_queue_command)
    websocket_api.async_register_command(hass, ws_media_browse)
    websocket_api.async_register_command(hass, ws_list)
    websocket_api.async_register_command(hass, ws_read)
    websocket_api.async_register_command(hass, ws_read_all)
    websocket_api.async_register_command(hass, ws_write)
    websocket_api.async_register_command(hass, ws_delete)
    websocket_api.async_register_command(hass, ws_translate)
