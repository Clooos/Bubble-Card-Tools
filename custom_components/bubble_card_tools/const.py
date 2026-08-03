
"""Constants for Bubble Card Tools integration."""

from __future__ import annotations

DOMAIN = "bubble_card_tools"

DEFAULT_BASE_RELATIVE_PATH = "bubble_card"  # => /config/bubble_card
MODULES_SUBDIR = "modules"
# JS files dropped here are served over HTTP and registered with the frontend
# as `extra_module_url` entries, so they load during the frontend bootstrap
# (before the Lovelace panel and its cards). Generic early-frontend-module
# hook: BCT does not care what those modules do.
EXTRA_MODULE_URL_SUBDIR = "extra_module_url"

ALLOWED_EXTS = {".yaml", ".yml"}
DEFAULT_MAX_BYTES = 256 * 1024  # 256 KB

EVENT_UPDATED = f"{DOMAIN}.updated"

NAME_REGEX = r"^(?:modules/)?[A-Za-z0-9_-]+\.(?:ya?ml)$"
