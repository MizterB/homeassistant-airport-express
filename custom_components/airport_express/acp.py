"""ACP (Apple Configuration Protocol) client for AirPort Express devices."""

from __future__ import annotations

import asyncio
import plistlib
import socket
import struct
import zlib
from dataclasses import dataclass
from typing import Any

import aiohttp

ACP_PORT = 5009
ACP_VERSION = 0x00030001
ACP_MAGIC = b"acpp"

CMD_GETPROP = 0x14
CMD_SETPROP = 0x15

AIRPLAY_PORT = 7000
AIRPLAY_STATUS_FLAG_PLAYING = 0x800

_STATIC_KEY = bytes.fromhex("5b6faf5d9d5b0e1351f2da1de7e8d673")
_HDR = struct.Struct("!4s8I12x32s48x")  # 128 bytes
_PROP_ELEM = struct.Struct("!4s2I")  # 12 bytes per property element


class ACPError(Exception):
    """ACP protocol error."""


@dataclass
class DeviceProperties:
    """Parsed ACP device properties."""

    name: str | None = None
    model: str | None = None
    firmware: str | None = None
    serial: str | None = None
    mac: str | None = None
    uptime_seconds: int = 0
    wan_ip: str | None = None


@dataclass
class AirPlayStatus:
    """AirPlay session status from HTTP /info."""

    playing: bool = False
    status_flags: int = 0


def _keystream(length: int) -> bytes:
    return bytes(((i + 0x55) & 0xFF) ^ _STATIC_KEY[i % 16] for i in range(length))


def _make_key(password: str) -> bytes:
    pw = (password.encode("utf-8") + b"\x00" * 32)[:32]
    return bytes(a ^ b for a, b in zip(_keystream(32), pw))


def _build_header(cmd: int, password: str, body: bytes = b"", flags: int = 4) -> bytes:
    key = _make_key(password)
    body_cs = zlib.adler32(body) if body else 1
    tmp = _HDR.pack(ACP_MAGIC, ACP_VERSION, 0, body_cs, len(body), flags, 0, cmd, 0, key)
    hdr_cs = zlib.adler32(tmp)
    return _HDR.pack(ACP_MAGIC, ACP_VERSION, hdr_cs, body_cs, len(body), flags, 0, cmd, 0, key)


def _prop_request_element(name: str) -> bytes:
    return _PROP_ELEM.pack(name.encode("ascii"), 0, 4) + b"\x00\x00\x00\x00"


def _prop_set_element(name: str, int_value: int) -> bytes:
    return _PROP_ELEM.pack(name.encode("ascii"), 0, 4) + struct.pack(">I", int_value)


def _parse_prop_body(body: bytes) -> dict[str, bytes | ACPError]:
    props: dict[str, bytes | ACPError] = {}
    offset = 0
    while offset + 12 <= len(body):
        name_b, flags, size = _PROP_ELEM.unpack_from(body, offset)
        offset += 12
        value = body[offset : offset + size]
        offset += size
        if name_b == b"\x00\x00\x00\x00":
            break
        name = name_b.decode("ascii", errors="replace")
        if flags & 1:
            err = struct.unpack(">I", value[:4])[0] if len(value) >= 4 else 0
            props[name] = ACPError(f"property error 0x{err:08x}")
        else:
            props[name] = value
    return props


def _decode_prop(props: dict, name: str) -> str | None:
    v = props.get(name)
    if v is None or isinstance(v, ACPError):
        return None
    try:
        return v.rstrip(b"\x00").decode("utf-8")
    except UnicodeDecodeError:
        return v.hex()


def _decode_ip(props: dict, name: str) -> str | None:
    v = props.get(name)
    if v is None or isinstance(v, ACPError) or len(v) < 4:
        return None
    return f"{v[0]}.{v[1]}.{v[2]}.{v[3]}"


def _decode_mac(props: dict, name: str) -> str | None:
    v = props.get(name)
    if v is None or isinstance(v, ACPError) or len(v) < 6:
        return None
    return ":".join(f"{b:02x}" for b in v[:6])


async def _acp_exchange(
    host: str, password: str, cmd: int, body: bytes, flags: int = 4, timeout: float = 10
) -> tuple[int, bytes]:
    """Open a TCP connection, send an ACP request, receive one response."""
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    try:
        await asyncio.wait_for(
            loop.sock_connect(sock, (host, ACP_PORT)), timeout=timeout
        )
        packet = _build_header(cmd, password, body, flags) + body
        await loop.sock_sendall(sock, packet)

        # Receive 128-byte header
        raw = b""
        while len(raw) < 128:
            chunk = await asyncio.wait_for(
                loop.sock_recv(sock, 128 - len(raw)), timeout=timeout
            )
            if not chunk:
                raise ACPError("Connection closed unexpectedly")
            raw += chunk

        if raw[:4] != ACP_MAGIC:
            raise ACPError(f"Bad ACP magic: {raw[:4]!r}")

        _, _, _, _, body_size, _, _, _, error_code, _ = _HDR.unpack(raw)

        if body_size == 0xFFFFFFFF:
            # Streaming response — read until timeout
            resp_body = b""
            try:
                while True:
                    chunk = await asyncio.wait_for(
                        loop.sock_recv(sock, 4096), timeout=2
                    )
                    if not chunk:
                        break
                    resp_body += chunk
            except asyncio.TimeoutError:
                pass
        elif body_size > 0:
            resp_body = b""
            while len(resp_body) < body_size:
                chunk = await asyncio.wait_for(
                    loop.sock_recv(sock, body_size - len(resp_body)), timeout=timeout
                )
                if not chunk:
                    raise ACPError("Connection closed unexpectedly")
                resp_body += chunk
        else:
            resp_body = b""

        return error_code, resp_body
    finally:
        sock.close()


async def async_get_properties(host: str, password: str) -> DeviceProperties:
    """Fetch device properties via ACP getprop."""
    body = b""
    for prop in ("syNm", "syVs", "syAM", "sySN", "laMA", "syUT", "waIP"):
        body += _prop_request_element(prop)

    error, resp = await _acp_exchange(host, password, CMD_GETPROP, body)
    if error:
        raise ACPError(f"getprop failed (error 0x{error:08x})")

    props = _parse_prop_body(resp)

    uptime_b = props.get("syUT", b"\x00\x00\x00\x00")
    uptime_s = 0
    if isinstance(uptime_b, bytes) and len(uptime_b) >= 4:
        uptime_s = struct.unpack(">I", uptime_b[:4])[0]

    return DeviceProperties(
        name=_decode_prop(props, "syNm"),
        model=_decode_prop(props, "syAM"),
        firmware=_decode_prop(props, "syVs"),
        serial=_decode_prop(props, "sySN"),
        mac=_decode_mac(props, "laMA"),
        uptime_seconds=uptime_s,
        wan_ip=_decode_ip(props, "waIP"),
    )


async def async_get_airplay_status(
    host: str, session: aiohttp.ClientSession | None = None
) -> AirPlayStatus:
    """Fetch AirPlay status via HTTP /info on port 7000."""
    url = f"http://{host}:{AIRPLAY_PORT}/info"
    close_session = False
    try:
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            data = await resp.read()
            info = plistlib.loads(data)
            flags = info.get("statusFlags", 0)
            return AirPlayStatus(
                playing=bool(flags & AIRPLAY_STATUS_FLAG_PLAYING),
                status_flags=flags,
            )
    except Exception as err:
        raise ACPError(f"AirPlay query failed: {err}") from err
    finally:
        if close_session and session is not None:
            await session.close()


async def async_reboot(host: str, password: str) -> None:
    """Reboot the device by setting property acRB=0."""
    body = _prop_set_element("acRB", 0)
    try:
        error, _ = await _acp_exchange(host, password, CMD_SETPROP, body, flags=0, timeout=5)
        if error:
            raise ACPError(f"Reboot failed (error 0x{error:08x})")
    except (asyncio.TimeoutError, ACPError, OSError):
        # Device likely dropped connection because it's restarting — that's fine
        pass


async def async_validate_connection(host: str, password: str) -> str:
    """Validate connection by fetching device name. Returns the name."""
    body = _prop_request_element("syNm")
    error, resp = await _acp_exchange(host, password, CMD_GETPROP, body)
    if error:
        raise ACPError(f"Connection validation failed (error 0x{error:08x})")
    props = _parse_prop_body(resp)
    name = _decode_prop(props, "syNm")
    if not name:
        raise ACPError("Could not read device name")
    return name
