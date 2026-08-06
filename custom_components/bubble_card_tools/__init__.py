
"""Home Assistant integration for Bubble Card Tools (production)."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional, Tuple

import yaml

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_BASE_RELATIVE_PATH,
    MODULES_SUBDIR,
    EXTRA_MODULE_URL_SUBDIR,
    ALLOWED_EXTS,
    DEFAULT_MAX_BYTES,
    EVENT_UPDATED,
    NAME_REGEX,
)

_LOGGER = logging.getLogger(__name__)

# There is nothing to configure in YAML: the integration is set up from its
# config entry, and async_setup only creates the base folder.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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

def read_all_modules(hass: HomeAssistant, entry: Optional[ConfigEntry], names: Optional[list[str]] = None) -> list[dict[str, Any]]:
    """Read many module files in a single call.

    When ``names`` is given, only those files are read; otherwise every module
    file is returned (same enumeration as ``list_modules``). A missing or
    invalid entry is skipped rather than failing the whole batch, so one bad
    file cannot break a cold boot. This collapses the ~50 per-file WS reads a
    cold client does into one round-trip.
    """
    base_dir = get_base_dir(hass)
    if names is None:
        names = [f["name"] for f in list_modules(hass, entry)]
    results: list[dict[str, Any]] = []
    for name in names:
        try:
            _, target = _resolve_target_path(hass, name)
            if not target.exists():
                continue
            content = target.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
        # Deliberately NOT parsing YAML here: a module's `code` field is the
        # whole (hundreds of KB) bundle, so parsing every file server-side and
        # ALSO shipping the parsed tree would duplicate the payload and add
        # seconds of parse time to a cold boot. Ship raw content only; the
        # client parses (it already did on the per-file path).
        results.append({
            "name": target.relative_to(base_dir).as_posix(),
            "content": content,
        })
    _LOGGER.debug("Bulk-read %d module files", len(results))
    return results

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
    # Disk work (exists/mkdir) must stay off the event loop.
    await hass.async_add_executor_job(ensure_base_dir, hass)
    return True


def _extract_extra_modules(hass: HomeAssistant, extra_dir: Path) -> None:
    """Extract any ``extra_module_url`` JS declared inside stored module YAMLs.

    A module file may carry an ``extra_module_url`` string alongside its
    ``code`` field; it is written out as ``<module-stem>.js`` so the folder
    scan in :func:`_provision_extra_dir` serves and registers it. This
    lets a plain module install provision an early frontend module with no
    extra file for the user to drop in. BCT stays generic: it has no knowledge
    of what the extracted JS does.
    """
    base_dir = get_base_dir(hass)
    candidates = list(base_dir.glob("*.y*ml"))
    modules_dir = base_dir / MODULES_SUBDIR
    if modules_dir.exists():
        candidates += list(modules_dir.glob("*.y*ml"))

    for path in candidates:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        # Module files have a single root key (the module name) -> its object.
        for value in data.values():
            js = value.get("extra_module_url") if isinstance(value, dict) else None
            if not isinstance(js, str) or not js.strip():
                continue
            out = extra_dir / f"{path.stem}.js"
            try:
                if not out.exists() or out.read_text(encoding="utf-8") != js:
                    out.write_text(js, encoding="utf-8")
                    _LOGGER.debug("Extracted extra_module_url JS to %s", out.name)
            except OSError:
                pass


def _provision_extra_dir(hass: HomeAssistant) -> tuple[Path, list[tuple[str, int]]]:
    """Blocking half of the extra_module_url registration (executor only).

    Creates the folders, extracts any JS embedded in installed module YAMLs,
    and returns the folder plus the (name, mtime) list of JS files to serve.
    Everything that touches the disk lives here so the async half never
    blocks the event loop.
    """
    base_dir = ensure_base_dir(hass)
    extra_dir = base_dir / EXTRA_MODULE_URL_SUBDIR
    if not extra_dir.exists():
        extra_dir.mkdir(parents=True, exist_ok=True)

    # Provision JS carried inside installed module YAMLs before scanning.
    _extract_extra_modules(hass, extra_dir)

    js_files: list[tuple[str, int]] = []
    for path in sorted(extra_dir.glob("*.js")):
        try:
            js_files.append((path.name, int(path.stat().st_mtime)))
        except OSError:
            continue
    return extra_dir, js_files


async def _register_extra_module_urls(hass: HomeAssistant) -> None:
    """Serve and early-register any JS placed in the extra_module_url folder.

    Files dropped in ``<base>/extra_module_url/*.js`` are served over HTTP and
    registered with the frontend as ES module URLs (``extra_module_url``), so
    they execute during the frontend bootstrap, before the Lovelace panel and
    its cards render. This is a generic hook for early frontend code; BCT has
    no knowledge of what the modules do.

    Registration happens at setup, so an integration reload (or a restart)
    picks up newly deployed or changed files. The ``?v=<mtime>`` query busts
    the browser cache when a file is redeployed; the previous versioned URL of
    the same file is unregistered so index.html never accumulates stale
    entries. A failure here is swallowed by the caller so it can never block
    the rest of the integration.

    The disk scan runs in the executor (:func:`_provision_extra_dir`): reading
    the module YAMLs from the event loop trips Home Assistant's blocking-call
    detector.
    """
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.components.frontend import add_extra_js_url

    try:
        from homeassistant.components.frontend import remove_extra_js_url
    except ImportError:  # very old HA: accumulating one stale URL is harmless
        remove_extra_js_url = None

    extra_dir, js_files = await hass.async_add_executor_job(_provision_extra_dir, hass)

    url_prefix = f"/{DOMAIN}/{EXTRA_MODULE_URL_SUBDIR}"

    # Public static serving of the folder (register the path once per process).
    # cache_headers=True: the URLs are mtime-versioned (?v=), so long-lived
    # browser caching is safe AND essential — without it every page load
    # refetches the module over the network, and on remote access that delay
    # pushes its execution past the first paint (the HA launch screen becomes
    # visible before the module can act). Served from disk cache, a module
    # executes before the first paint.
    if not hass.data.get(f"{DOMAIN}_extra_static"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(url_prefix, str(extra_dir), True)]
        )
        hass.data[f"{DOMAIN}_extra_static"] = True

    # Register each JS module, one live URL per file: on a redeploy (new
    # mtime -> new URL) the previous URL is unregistered first.
    registered = hass.data.get(f"{DOMAIN}_extra_js")
    if not isinstance(registered, dict):  # migrate the pre-1.1 set shape
        registered = hass.data[f"{DOMAIN}_extra_js"] = {}
    for name, mtime in js_files:
        url = f"{url_prefix}/{name}?v={mtime}"
        old = registered.get(name)
        if old == url:
            continue
        if old and remove_extra_js_url is not None:
            try:
                remove_extra_js_url(hass, old)
            except Exception:  # noqa: BLE001
                pass
        add_extra_js_url(hass, url)
        registered[name] = url
        _LOGGER.debug("Registered extra module URL: %s", url)

def _register_media_mime_types() -> None:
    """Register common media container mime types missing from Python's map.

    Home Assistant's Jellyfin media_source silently drops any item whose
    file path has no guessable mime type (mimetypes.guess_type), which
    hides whole seasons of .mkv episodes from media browsers. Registering
    the missing types here fixes browsing for the whole HA process.
    """
    import mimetypes

    for mime, ext in (
        ("video/x-matroska", ".mkv"),
        ("audio/x-matroska", ".mka"),
        ("video/x-m4v", ".m4v"),
        ("video/mp2t", ".ts"),
        ("video/mp2t", ".m2ts"),
        ("audio/opus", ".opus"),
        ("video/ogg", ".ogv"),
        ("audio/aac", ".aac"),
        ("video/x-flv", ".flv"),
        ("video/x-ms-wmv", ".wmv"),
    ):
        if not mimetypes.guess_type(f"media{ext}")[0]:
            mimetypes.add_type(mime, ext)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Bubble Card Tools")
    await hass.async_add_executor_job(ensure_base_dir, hass)
    _register_media_mime_types()
    # Serve + early-register frontend modules dropped in the extra_module_url
    # folder. Never fatal: a failure must not stop the WS API / proxy below.
    try:
        await _register_extra_module_urls(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to register extra module URLs")
    from . import websocket_api as wsapi
    wsapi.async_register_api(hass, entry)
    # Authenticated LAN artwork proxy (see image_proxy.py). Guarded so an
    # integration reload does not register the view twice.
    if not hass.data.get(f"{DOMAIN}_image_proxy"):
        from .image_proxy import BubbleImageProxyView
        hass.http.register_view(BubbleImageProxyView())
        hass.data[f"{DOMAIN}_image_proxy"] = True
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Unloading Bubble Card Tools")
    return True
