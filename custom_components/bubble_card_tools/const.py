
"""Constants for Bubble Card Tools integration."""

from __future__ import annotations

DOMAIN = "bubble_card_tools"

DEFAULT_BASE_RELATIVE_PATH = "bubble_card"  # => /config/bubble_card
MODULES_SUBDIR = "modules"

ALLOWED_EXTS = {".yaml", ".yml"}
DEFAULT_MAX_BYTES = 256 * 1024  # 256 KB

EVENT_UPDATED = f"{DOMAIN}.updated"

NAME_REGEX = r"^(?:modules/)?[A-Za-z0-9_-]+\.(?:ya?ml)$"
