#!/usr/bin/env python3
"""Opt-in, read-only model discovery. No inference, credential scanning, or host startup.

Python 3.10+ standard library. See references/live-discovery.md for permission and
schema boundaries. A successful listing NEVER establishes model callability.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import math
import re
import socket
import ssl
import sys
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

MAX_BYTES = 2 * 1024 * 1024
MAX_MODELS = 256
PATHS = {"opencode-v2": "/api/model", "ollama": "/api/tags"}
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,191}\Z")
INSTANCE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
MESSAGES = {
    "permission_required": "Local-network access requires explicit authorization.",
    "invalid_input": "Invalid discovery options or unreadable input; consult --help.",
    "invalid_response": "Response does not match this adapter's supported schema.",
    "response_too_large": "Response exceeds the 2 MiB discovery limit.",
    "too_many_models": "More than 256 candidates; narrow the explicit provider/model filters.",
    "denied": "Host denied access; use approved host authentication or a local snapshot.",
    "rate_limited": "Host rate limit reached; no automatic retry was made.",
    "unsupported_api": "Endpoint not supported; check the explicit adapter and host version.",
    "redirect_blocked": "Redirect refused; no redirect target was contacted.",
    "unavailable": "The selected local host is unavailable; no other endpoint was tried.",
    "timeout": "Discovery exceeded its time limit; no automatic retry was made.",
    "stale_snapshot": "Snapshot is too old or future-dated; obtain a fresh authorized listing.",
    "scope_mismatch": "The returned host directory differs from the explicitly expected scope.",
}


class DiscoveryError(ValueError):
    """A bounded error code, never source text, paths, credentials, or HTTP bodies."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(MESSAGES[code])


def fail(code: str = "invalid_response") -> None:
    raise DiscoveryError(code)


def decode(raw: bytes, limit: int = MAX_BYTES) -> object:
    if len(raw) > limit:
        fail("response_too_large")
    def pairs(items: list[tuple]) -> dict:
        result = {}
        for key, value in items:
            if key in result:
                fail()
            result[key] = value
        return result
    def nonfinite(_: str) -> None:
        fail()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, float) and not math.isfinite(item):
                fail()
            if isinstance(item, dict):
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        return value
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        fail()


def token(value: object) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        fail()
    return value


def token_limit(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= 2**53 - 1:
        fail()
    # OpenCode's empty model reports zero until its capacity is known.
    return value or None


def opencode_provider_model_id(row: dict) -> str:
    if "api" not in row:
        return token(row.get("modelID"))
    api = row["api"]
    if not isinstance(api, dict) or api.get("type") not in ("native", "aisdk"):
        fail()
    model_id = token(api.get("id"))
    if "modelID" in row and token(row["modelID"]) != model_id:
        fail()
    return model_id


def string_list(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > 256:
        fail()
    values = [token(v) for v in value]
    if len(set(values)) != len(values):
        fail()
    return values


def stamp(value: str) -> str:
    try:
        if date.fromisoformat(value).isoformat() != value:
            fail("invalid_input")
    except (TypeError, ValueError):
        fail("invalid_input")
    return value


def base_candidate(instance: str, provider: str, model_id: str, observed: str, adapter: str) -> dict:
    # Escape each segment so an ID containing '/' cannot collide with another provider.
    identity = "/".join(quote(s, safe="._-") for s in (instance, provider, model_id))
    if len("unmapped:" + identity) > 512:
        fail()
    return {
        "id": identity, "model_key": "unmapped:" + identity,
        "provider": provider, "api_model_id": model_id,
        "access": "listed", "access_source": "host-catalog:" + adapter,
        "observed_at": observed, "capabilities": [], "actions": ["recommend"],
        "context_window": None, "max_output_tokens": None, "local": None,
    }


def normalize(data: object, adapter: str, instance: str, observed_at: str, *,
              providers: tuple[str, ...] = (), model_ids: tuple[str, ...] = (),
              expected_directory: str | None = None) -> dict:
    """Whitelist fields from a supported listing. No aliases, scores, or access inferred."""
    if adapter not in PATHS or not INSTANCE.fullmatch(instance):
        fail("invalid_input")
    stamp(observed_at)
    for value in (*providers, *model_ids):
        token(value)
    if not isinstance(data, dict):
        fail()
    scope_hash = None
    if adapter == "opencode-v2":
        location = data.get("location")
        if not isinstance(location, dict) or not isinstance(location.get("directory"), str):
            fail()
        directory = location["directory"]
        if not directory or len(directory) > 4096 or any(ord(c) < 32 for c in directory):
            fail()
        if expected_directory is not None and directory != expected_directory:
            fail("scope_mismatch")
        scope_hash = hashlib.sha256(directory.encode("utf-8")).hexdigest()
        rows = data.get("data")
    else:
        if expected_directory is not None:
            fail("invalid_input")
        rows = data.get("models")
    if not isinstance(rows, list) or len(rows) > 10000:
        fail()
    models, observations, seen = [], [], set()
    skipped = {"disabled": 0, "deprecated": 0, "non_chat": 0, "filtered": 0}
    for row in rows:
        if not isinstance(row, dict):
            fail()
        if adapter == "opencode-v2":
            provider, model_id = token(row.get("providerID")), token(row.get("id"))
        else:
            provider, model_id = "ollama", token(row.get("name"))
        pair = (provider, model_id)
        if pair in seen:
            fail()
        seen.add(pair)
        if (providers and provider not in providers) or (model_ids and model_id not in model_ids):
            skipped["filtered"] += 1
            continue
        model = base_candidate(instance, provider, model_id, observed_at, adapter)
        note = {"id": model["id"], "configuration_verified": False}
        if adapter == "opencode-v2":
            if type(row.get("enabled")) is not bool:
                fail()
            if not row["enabled"]:
                skipped["disabled"] += 1
                continue
            if row.get("status") not in ("active", "alpha", "beta", "deprecated"):
                fail()
            if row["status"] == "deprecated":
                skipped["deprecated"] += 1
                continue
            if row.get("type", "chat") != "chat":
                skipped["non_chat"] += 1
                continue
            note["provider_model_id"] = opencode_provider_model_id(row)
            note["host_model_id"] = model_id
            note["lifecycle"] = row["status"]
            caps, limit, variants = row.get("capabilities"), row.get("limit"), row.get("variants")
            if not isinstance(caps, dict) or not isinstance(limit, dict) or not isinstance(variants, list):
                fail()
            if type(caps.get("tools")) is not bool or len(variants) > 256:
                fail()
            inputs, outputs = string_list(caps.get("input")), string_list(caps.get("output"))
            capabilities = ["input:" + s for s in inputs] + ["output:" + s for s in outputs]
            if "text" in inputs and "text" in outputs:
                capabilities.append("text")
            if "image" in inputs:
                capabilities.append("vision")
            if caps["tools"]:
                capabilities.append("tools")
            model["capabilities"] = sorted(set(capabilities))
            if len(model["capabilities"]) > 256:
                fail()
            context, input_limit = token_limit(limit.get("context")), token_limit(limit.get("input"))
            model["context_window"] = min(context, input_limit) if context and input_limit else context
            model["max_output_tokens"] = token_limit(limit.get("output"))
            ids = []
            for variant in variants:
                if not isinstance(variant, dict):
                    fail()
                ids.append(token(variant.get("id")))
            if len(set(ids)) != len(ids):
                fail()
            note["variant_ids"] = sorted(ids)
            note["reported_input_limit"] = input_limit
            # Do not copy body, settings, headers, costs, API keys, or provider options.
        else:
            if "model" in row and row["model"] != model_id:
                fail()
            digest = row.get("digest")
            if digest is not None:
                if not isinstance(digest, str) or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest):
                    fail()
                note["digest"] = digest
            details = row.get("details", {})
            if not isinstance(details, dict):
                fail()
            if details.get("quantization_level"):
                note["quantization"] = token(details["quantization_level"])
            # /api/tags does not attest tools, context, local inference, or permission.
        models.append(model)
        observations.append(note)
        if len(models) > MAX_MODELS:
            fail("too_many_models")
    return {
        "discovery_schema_version": "1.0", "status": "discovered" if models else "no_models",
        "adapter": adapter, "instance_id": instance, "observed_at": observed_at,
        "host_version": None, "scope_sha256": scope_hash,
        "inventory": {"models": sorted(models, key=lambda m: m["id"])},
        "observations": sorted(observations, key=lambda m: m["id"]), "skipped": skipped,
        "warnings": ["Listing is not entitlement or proof of callability.",
                     "Benchmark identity and configuration remain unmapped.",
                     "Loopback transport does not prove local inference or a zero price.",
                     "Host catalog snapshots may be cached or precede plugin settlement."],
        "execution_status": "not_executed",
    }


def endpoint(value: str) -> tuple[str, str, int]:
    if not isinstance(value, str) or len(value) > 128 or any(c.isspace() for c in value):
        fail("invalid_input")
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or parsed.hostname not in ("127.0.0.1", "::1")
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or "?" in value or "#" in value or "%" in value or parsed.port is None):
            fail("invalid_input")
        port = parsed.port
        if not 1 <= port <= 65535:
            fail("invalid_input")
        return parsed.scheme, parsed.hostname, port
    except (ValueError, TypeError):
        fail("invalid_input")


def basic_auth(raw: bytes) -> str:
    if len(raw) > 8192:
        fail("invalid_input")
    data = decode(raw, 8192)
    if not isinstance(data, dict) or set(data) != {"username", "password"}:
        fail("invalid_input")
    user, password = data["username"], data["password"]
    if any(not isinstance(v, str) or not v or len(v) > 2048 or any(ord(c) < 32 for c in v)
           for v in (user, password)) or ":" in user:
        fail("invalid_input")
    return "Basic " + base64.b64encode((user + ":" + password).encode("utf-8")).decode("ascii")


def fetch_listing(base_url: str, adapter: str, *, allow_network: bool = False,
                  timeout: float = 5, authorization: str | None = None) -> object:
    """Exactly one bounded GET to an explicit loopback IP; no proxy, redirects or retry."""
    if not allow_network:
        fail("permission_required")
    if adapter not in PATHS or type(timeout) not in (float, int) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        fail("invalid_input")
    scheme, host, port = endpoint(base_url)
    headers = {"Accept": "application/json", "Accept-Encoding": "identity", "Cache-Control": "no-cache"}
    if authorization is not None:
        if len(authorization) > 8192 or not re.fullmatch(r"Basic [A-Za-z0-9+/]+=*", authorization):
            fail("invalid_input")
        headers["Authorization"] = authorization
    if scheme == "https":
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ssl.create_default_context())
    else:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
    timer = None
    expired = threading.Event()
    try:
        started = time.monotonic()
        conn.connect()
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            fail("timeout")
        wire = conn.sock
        wire.settimeout(remaining)
        def abort() -> None:
            expired.set()
            try:
                wire.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        timer = threading.Timer(remaining, abort)
        timer.daemon = True
        timer.start()
        conn.request("GET", PATHS[adapter], headers=headers)
        response = conn.getresponse()
        if response.status in (401, 403):
            fail("denied")
        if response.status == 429:
            fail("rate_limited")
        if response.status in (404, 405, 410):
            fail("unsupported_api")
        if 300 <= response.status < 400:
            fail("redirect_blocked")
        if response.status != 200:
            fail("unavailable")
        content_type = response.getheader("Content-Type", "").split(";", 1)[0].lower().strip()
        if content_type != "application/json" or response.getheader("Content-Encoding", "identity") != "identity":
            fail()
        length = response.getheader("Content-Length")
        if length is not None:
            if not length.isdecimal():
                fail()
            if int(length) > MAX_BYTES:
                fail("response_too_large")
        raw = response.read(MAX_BYTES + 1)
        if expired.is_set():
            fail("timeout")
        if len(raw) > MAX_BYTES:
            fail("response_too_large")
        if length is not None and len(raw) != int(length):
            fail()
        return decode(raw)
    except (TimeoutError, socket.timeout):
        fail("timeout")
    except (OSError, http.client.HTTPException, UnicodeError):
        fail("timeout" if expired.is_set() else "unavailable")
    finally:
        if timer is not None:
            timer.cancel()
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, choices=tuple(PATHS))
    parser.add_argument("--instance-id", required=True, help="Non-secret stable label for this host/project")
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--base-url", help="Explicit http(s)://127.0.0.1:PORT or http(s)://[::1]:PORT")
    sources.add_argument("--input", help="Explicit local listing JSON or - for stdin; no network")
    parser.add_argument("--allow-local-network", action="store_true", help="Authorize this one listing request")
    parser.add_argument("--auth-stdin", action="store_true", help="Read host Basic auth JSON from stdin, never argv/env")
    parser.add_argument("--observed-at", help="Required snapshot observation date; prohibited for live listing")
    parser.add_argument("--max-age-days", type=int, default=7, help="Snapshot freshness limit")
    parser.add_argument("--expected-directory", help="OpenCode response scope must match this exact directory")
    parser.add_argument("--provider", action="append", default=[], help="Exact provider filter (repeatable)")
    parser.add_argument("--model", action="append", default=[], help="Exact host model-ID filter (repeatable)")
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args(argv)
    try:
        if not INSTANCE.fullmatch(args.instance_id) or args.max_age_days < 0:
            fail("invalid_input")
        for value in args.provider + args.model:
            token(value)
        today = datetime.now(timezone.utc).date()
        if args.base_url:
            if not args.allow_local_network:
                fail("permission_required")
            endpoint(args.base_url)  # Validate destination before touching auth stdin.
            if args.observed_at is not None:
                fail("invalid_input")
            auth = basic_auth(sys.stdin.buffer.read(8193)) if args.auth_stdin else None
            data = fetch_listing(args.base_url, args.adapter, allow_network=True,
                                 timeout=args.timeout, authorization=auth)
            observed, mode = today.isoformat(), "live"
        else:
            if args.allow_local_network or args.auth_stdin or args.observed_at is None:
                fail("invalid_input")
            observed, mode = stamp(args.observed_at), "snapshot"
            if not 0 <= (today - date.fromisoformat(observed)).days <= args.max_age_days:
                fail("stale_snapshot")
            if args.input == "-":
                raw = sys.stdin.buffer.read(MAX_BYTES + 1)
            else:
                with Path(args.input).open("rb") as stream:
                    raw = stream.read(MAX_BYTES + 1)
            data = decode(raw)
        report = normalize(data, args.adapter, args.instance_id, observed,
                           providers=tuple(args.provider), model_ids=tuple(args.model),
                           expected_directory=args.expected_directory)
        report["source_mode"] = mode
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except DiscoveryError as exc:
        code = exc.code
    except (ValueError, OSError, RecursionError, OverflowError, UnicodeError):
        code = "invalid_input"
    print(json.dumps({"discovery_schema_version": "1.0", "status": code,
                      "inventory": {"models": []}, "error": MESSAGES[code],
                      "execution_status": "not_executed"}))
    return 2 if code in ("permission_required", "denied", "rate_limited", "unavailable", "timeout", "stale_snapshot") else 1


if __name__ == "__main__":
    raise SystemExit(main())
