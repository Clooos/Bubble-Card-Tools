"""Authenticated image proxy for LAN-only media artwork.

Media integrations (Jellyfin…) hand the frontend DIRECT LAN URLs for their
thumbnails: remote devices (Nabu Casa / HTTPS) can neither reach them nor
display them (mixed content). Home Assistant itself CAN reach them — this
view fetches the image server-side and serves it on the HA origin.

Security posture:
- requires_auth: only authenticated HA users/tokens can use it,
- target hosts restricted to PRIVATE addresses (RFC1918, loopback, .local
  and single-label LAN hostnames) — this is a LAN artwork proxy, not an
  open relay,
- image content-types only, response size capped.
"""
from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

import aiohttp
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:  # newer HA exposes a typed app key
    from homeassistant.components.http import KEY_HASS  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - older cores
    KEY_HASS = "hass"  # type: ignore[assignment]

_LOGGER = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024  # 5 MiB is plenty for artwork
FETCH_TIMEOUT = aiohttp.ClientTimeout(total=15)


def _is_private_host(host: str) -> bool:
    """Only allow LAN targets: private/loopback IPs, .local, bare hostnames."""
    try:
        return ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback
    except ValueError:
        lowered = host.lower()
        return lowered.endswith(".local") or "." not in lowered


class BubbleImageProxyView(HomeAssistantView):
    """GET /api/bubble_card_tools/thumb?url=<encoded image url>."""

    url = "/api/bubble_card_tools/thumb"
    name = "api:bubble_card_tools:thumb"
    requires_auth = True

    async def get(self, request: web.Request) -> web.StreamResponse:
        hass: HomeAssistant = request.app[KEY_HASS]
        raw_url = request.query.get("url", "")
        parsed = urlparse(raw_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return web.Response(status=400, text="Invalid url")
        if not _is_private_host(parsed.hostname):
            return web.Response(status=403, text="Host not allowed")

        session = async_get_clientsession(hass)
        try:
            async with session.get(raw_url, timeout=FETCH_TIMEOUT) as resp:
                if resp.status != 200:
                    return web.Response(status=resp.status, text="Upstream error")
                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    return web.Response(status=415, text="Not an image")
                if (resp.content_length or 0) > MAX_BYTES:
                    return web.Response(status=413, text="Too large")
                # StreamReader.read(n) returns whatever is buffered (up to n),
                # NOT n bytes: iterate to EOF so the image is never truncated.
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        return web.Response(status=413, text="Too large")
                    chunks.append(chunk)
                body = b"".join(chunks)
                return web.Response(
                    body=body,
                    content_type=content_type.split(";")[0],
                    headers={"Cache-Control": "private, max-age=86400"},
                )
        except Exception as err:  # noqa: BLE001 - network errors -> 502
            _LOGGER.debug("Image proxy fetch failed for %s: %s", raw_url, err)
            return web.Response(status=502, text="Fetch failed")
