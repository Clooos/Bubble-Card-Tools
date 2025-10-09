
"""WebSocket API for Bubble Card Tools."""
from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry

from . import list_modules, read_module, write_module, delete_module

_LOGGER = logging.getLogger(__name__)

SCHEMA_LIST = {vol.Required("type"): "bubble_card_tools/list_modules"}
SCHEMA_READ = {vol.Required("type"): "bubble_card_tools/read_module", vol.Required("name"): str}
SCHEMA_WRITE = {vol.Required("type"): "bubble_card_tools/write_module", vol.Required("name"): str, vol.Required("content"): str}
SCHEMA_DELETE = {vol.Required("type"): "bubble_card_tools/delete_module", vol.Required("name"): str}

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

    websocket_api.async_register_command(hass, ws_list)
    websocket_api.async_register_command(hass, ws_read)
    websocket_api.async_register_command(hass, ws_write)
    websocket_api.async_register_command(hass, ws_delete)
