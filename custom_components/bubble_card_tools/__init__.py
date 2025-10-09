
"""Home Assistant integration for Bubble Card Tools (production)."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional, Tuple

import yaml

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_BASE_RELATIVE_PATH,
    MODULES_SUBDIR,
    ALLOWED_EXTS,
    DEFAULT_MAX_BYTES,
    EVENT_UPDATED,
    NAME_REGEX,
)

_LOGGER = logging.getLogger(__name__)

def get_base_dir(hass: HomeAssistant) -> Path:
    base = Path(hass.config.path(DEFAULT_BASE_RELATIVE_PATH)).resolve()
    return base

def ensure_base_dir(hass: HomeAssistant) -> Path:
    base = get_base_dir(hass)
    modules_dir = base / MODULES_SUBDIR
    if not base.exists():
        _LOGGER.debug("Creating base directory at %s", base)
        base.mkdir(parents=True, exist_ok=True)
    if not modules_dir.exists():
        _LOGGER.debug("Creating modules subdirectory at %s", modules_dir)
        modules_dir.mkdir(parents=True, exist_ok=True)
    return base

def is_valid_name(name: str) -> bool:
    return re.match(NAME_REGEX, name) is not None

def _resolve_target_path(hass: HomeAssistant, name: str) -> tuple[Path, Path]:
    if not is_valid_name(name):
        raise ValueError("Invalid name. Use 'name.yaml' or 'modules/name.yaml' with [A-Za-z0-9_-].")
    base_dir = ensure_base_dir(hass)
    target = (base_dir / name).resolve()
    if not str(target).startswith(str(base_dir)):
        raise ValueError("Invalid path. Name resolves outside base directory.")
    if target.suffix.lower() not in ALLOWED_EXTS:
        raise ValueError("Invalid extension. Only .yaml or .yml are allowed.")
    rel = target.relative_to(base_dir).as_posix()
    if "/" in rel and not rel.startswith(f"{MODULES_SUBDIR}/"):
        raise ValueError("Only the 'modules' subfolder is allowed.")
    return base_dir, target

def _parse_yaml(content: str) -> Any:
    try:
        return yaml.safe_load(content) if content.strip() else None
    except yaml.YAMLError as err:
        raise ValueError(f"YAML parse error: {err}")

def list_modules(hass: HomeAssistant, entry: Optional[ConfigEntry]) -> list[dict[str, Any]]:
    base_dir = ensure_base_dir(hass)
    files: list[dict[str, Any]] = []

    def add_path(p: Path) -> None:
        try:
            stat = p.stat()
        except OSError:
            return
        rel = p.relative_to(base_dir).as_posix()
        files.append({
            "name": rel,
            "size": stat.st_size,
            "updated_at": dt_util.utc_from_timestamp(stat.st_mtime).isoformat().replace("+00:00", "Z"),
        })

    for p in sorted(base_dir.glob("*.y*ml")):
        add_path(p)
    modules_dir = base_dir / MODULES_SUBDIR
    if modules_dir.exists():
        for p in sorted(modules_dir.glob("*.y*ml")):
            add_path(p)

    _LOGGER.debug("Listed %d modules in %s", len(files), base_dir)
    return files

def read_module(hass: HomeAssistant, entry: Optional[ConfigEntry], name: str) -> dict[str, Any]:
    _, target = _resolve_target_path(hass, name)
    if not target.exists():
        raise FileNotFoundError("Module not found.")
    content = target.read_text(encoding="utf-8")
    parsed = None
    try:
        parsed = _parse_yaml(content)
    except ValueError as err:
        _LOGGER.debug("YAML parse error for %s: %s", target.name, err)
    return {"name": target.relative_to(get_base_dir(hass)).as_posix(), "content": content, "parsed": parsed}

def _fire_updated(hass: HomeAssistant, action: str, rel_name: str) -> None:
    """Thread-safe event fire from executor thread."""
    data = {"action": action, "name": rel_name, "ts": dt_util.utcnow().isoformat().replace("+00:00", "Z")}
    # Schedule on the event loop to avoid thread-safety issues
    hass.loop.call_soon_threadsafe(hass.bus.async_fire, EVENT_UPDATED, data)

def write_module(hass: HomeAssistant, entry: Optional[ConfigEntry], name: str, content: str) -> dict[str, Any]:
    _, target = _resolve_target_path(hass, name)
    size = len(content.encode("utf-8"))
    if size > DEFAULT_MAX_BYTES:
        raise ValueError(f"Content too large. Max {DEFAULT_MAX_BYTES} bytes.")
    _ = _parse_yaml(content)
    _LOGGER.debug("Writing module %s (%d bytes)", target, size)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    rel = target.relative_to(get_base_dir(hass)).as_posix()
    _fire_updated(hass, "write", rel)
    return {"name": target.name, "status": "written"}

def delete_module(hass: HomeAssistant, entry: Optional[ConfigEntry], name: str) -> dict[str, Any]:
    _, target = _resolve_target_path(hass, name)
    if not target.exists():
        raise FileNotFoundError("Module not found.")
    _LOGGER.debug("Deleting module %s", target.name)
    target.unlink()
    rel = target.relative_to(get_base_dir(hass)).as_posix()
    _fire_updated(hass, "delete", rel)
    return {"name": target.name, "status": "deleted"}

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    ensure_base_dir(hass)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Bubble Card Tools")
    ensure_base_dir(hass)
    from . import websocket_api as wsapi
    wsapi.async_register_api(hass, entry)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Unloading Bubble Card Tools")
    return True
