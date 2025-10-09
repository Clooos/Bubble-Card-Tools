
"""Config flow for Bubble Card Tools (single instance, no options)."""
from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Bubble Card Tools", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
