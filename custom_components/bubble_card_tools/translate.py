"""Server-side text translation for Bubble Card's Module Store content.

The browser cannot always translate by itself: the on-device Translator API
requires a secure context (HTTPS) and third-party endpoints enforce CORS.
Home Assistant has neither constraint, so the frontend asks this integration
over the local WebSocket and the outbound request happens here, with a
persistent disk cache shared by every browser and device.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, Optional

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORE_VERSION = 1
STORE_KEY = "bubble_card_tools.translations"
MAX_ENTRIES = 2000
SAVE_DELAY = 10  # seconds
ENDPOINT = "https://translate.googleapis.com/translate_a/single"
RATE_LIMIT_COOLDOWN = 300  # seconds

EDGE_AUTH = "https://edge.microsoft.com/translate/auth"
EDGE_ENDPOINT = "https://api-edge.cognitive.microsofttranslator.com/translate"
EDGE_TOKEN_TTL = 8 * 60  # tokens last ~10 minutes

_store: Optional[Store] = None
_cache: Optional[Dict[str, str]] = None
_rate_limited_until: float = 0.0
_edge_token: Optional[str] = None
_edge_token_expires: float = 0.0


async def _get_cache(hass: HomeAssistant) -> Dict[str, str]:
    global _store, _cache
    if _cache is None:
        _store = Store(hass, STORE_VERSION, STORE_KEY)
        _cache = await _store.async_load() or {}
    return _cache


def _cache_key(text: str, target: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return f"{target}:{digest}"


async def _translate_google(session: aiohttp.ClientSession, text: str, target: str) -> Optional[str]:
    global _rate_limited_until
    if time.monotonic() < _rate_limited_until:
        return None
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": target,
        "dt": "t",
        "ie": "UTF-8",
        "oe": "UTF-8",
        "q": text,
    }
    try:
        async with session.get(
            ENDPOINT,
            params=params,
            timeout=aiohttp.ClientTimeout(total=10),
            allow_redirects=False,  # a redirect means the anti-abuse page
        ) as resp:
            if resp.status in (302, 429):
                _rate_limited_until = time.monotonic() + RATE_LIMIT_COOLDOWN
                return None
            if resp.status != 200:
                return None
            data: Any = await resp.json(content_type=None)
        return "".join(
            segment[0] for segment in (data[0] or []) if segment and segment[0]
        ) or None
    except Exception as err:  # noqa: BLE001 - network errors are expected
        _LOGGER.debug("Google translation request failed: %s", err)
        return None


async def _translate_edge(session: aiohttp.ClientSession, text: str, target: str) -> Optional[str]:
    """Microsoft Edge's free translation service: separate infrastructure,
    so it keeps working when the Google endpoint rate-limits this IP."""
    global _edge_token, _edge_token_expires
    try:
        if not _edge_token or time.monotonic() > _edge_token_expires:
            async with session.get(
                EDGE_AUTH, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return None
                _edge_token = (await resp.text()).strip()
                _edge_token_expires = time.monotonic() + EDGE_TOKEN_TTL

        async with session.post(
            EDGE_ENDPOINT,
            params={"api-version": "3.0", "from": "en", "to": target},
            headers={"Authorization": f"Bearer {_edge_token}"},
            json=[{"Text": text}],
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 401:
                _edge_token = None  # expired early: refetched on next call
                return None
            if resp.status != 200:
                return None
            data: Any = await resp.json(content_type=None)
        return data[0]["translations"][0]["text"] or None
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Edge translation request failed: %s", err)
        return None


async def async_translate(hass: HomeAssistant, text: str, target: str) -> Optional[str]:
    """Translate English text to `target`, with a persistent cache."""
    if not text or not target:
        return None

    cache = await _get_cache(hass)
    key = _cache_key(text, target)
    if key in cache:
        return cache[key]

    session = async_get_clientsession(hass)
    # Edge first: noticeably better output quality than the Google endpoint.
    translated = await _translate_edge(session, text, target)
    if not translated:
        translated = await _translate_google(session, text, target)
    if not translated:
        return None

    cache[key] = translated
    while len(cache) > MAX_ENTRIES:
        cache.pop(next(iter(cache)))
    if _store is not None:
        _store.async_delay_save(lambda: dict(_cache or {}), SAVE_DELAY)

    return translated
