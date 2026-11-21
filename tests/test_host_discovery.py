"""Synthetic protocol fixtures and real loopback HTTP tests, not live-host certification."""
from __future__ import annotations

import base64
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ADAPTERS = ROOT / "skills/intelligent-model-router/scripts/adapters"
sys.path.insert(0, str(ADAPTERS))
import discover_host as d

TODAY = datetime.now(timezone.utc).date().isoformat()


def opencode_row(model="fixture-model", provider="fixture-provider"):
    return {"id": model, "modelID": "provider-api-model", "providerID": provider,
            "enabled": True, "status": "active", "type": "chat",
            "capabilities": {"tools": True, "input": ["text", "image"], "output": ["text"]},
            "variants": [{"id": "high", "settings": {"secret": "do-not-copy"}}],
            "limit": {"context": 32000, "input": 24000, "output": 4096},
            "headers": {"Authorization": "do-not-copy"}, "settings": {"apiKey": "do-not-copy"},
            "cost": [{"input": 0, "output": 0}]}


def opencode(rows=None):
    return {"location": {"directory": "/synthetic/project"}, "data": rows if rows is not None else [opencode_row()]}


def opencode_release_listing(api):
    """A complete OpenCode v1.19.6 GET /api/model response."""
    directory = "/synthetic/project"
    return {
        "location": {"directory": directory, "project": {"id": "fixture", "directory": directory}},
        "data": [{
            "id": "host-alias", "providerID": "fixture-provider", "name": "Example", "api": api,
            "request": {"headers": {"X-Example": "private-marker"}, "body": {}},
            "capabilities": {"tools": False, "input": [], "output": []}, "variants": [],
            "time": {"released": 0}, "cost": [], "status": "active", "enabled": True,
            "limit": {"context": 0, "output": 0},
        }],
    }


def ollama():
    return {"models": [{"name": "fixture:cloud", "model": "fixture:cloud",
                        "digest": "a" * 64, "details": {"quantization_level": "Q4_K_M"},
                        "remote_host": "https://cloud.invalid", "api_key": "do-not-copy"}]}


class NormalizationTests(unittest.TestCase):
    def test_opencode_1_19_6_nested_api_and_zero_limits(self):
        transports = (
            {"type": "aisdk", "id": "underlying-model", "package": "private-marker"},
            {"type": "native", "id": "underlying-model", "settings": {"key": "private-marker"}},
        )
        for api in transports:
            with self.subTest(transport=api["type"]):
                out = d.normalize(opencode_release_listing(api), "opencode-v2", "release", TODAY)
                model, = out["inventory"]["models"]
                note, = out["observations"]
                self.assertEqual(model["api_model_id"], "host-alias")
                self.assertEqual(note["provider_model_id"], "underlying-model")
                self.assertEqual((model["access"], model["actions"]), ("listed", ["recommend"]))
                self.assertFalse(note["configuration_verified"])
                self.assertIsNone(model["context_window"])
                self.assertIsNone(model["max_output_tokens"])
                self.assertNotIn("private-marker", json.dumps(out))

    def test_opencode_explicit_zero_input_limit_keeps_context_unknown(self):
        listing = opencode_release_listing({"type": "native", "id": "underlying-model", "settings": {}})
        listing["data"][0]["limit"] = {"context": 4096, "input": 0, "output": 256}
        model, = d.normalize(listing, "opencode-v2", "release", TODAY)["inventory"]["models"]
        self.assertIsNone(model["context_window"])
        self.assertEqual(model["max_output_tokens"], 256)

    def test_opencode_rejects_conflicting_or_malformed_provider_identity(self):
        row = opencode_row()
        for api in (None, {}, {"type": "native", "id": "conflicting"}, {"type": "other", "id": row["modelID"]}):
            with self.subTest(api=api), self.assertRaises(d.DiscoveryError):
                d.normalize(opencode([dict(row, api=api)]), "opencode-v2", "release", TODAY)
        row["api"] = {"type": "native", "id": row["modelID"]}
        out = d.normalize(opencode([row]), "opencode-v2", "release", TODAY)
        self.assertEqual(out["observations"][0]["provider_model_id"], row["modelID"])

    def test_opencode_retains_exact_host_and_provider_identifiers(self):
        result = d.normalize(opencode(), "opencode-v2", "host-a", TODAY)
        model = result["inventory"]["models"][0]
        self.assertEqual(model["api_model_id"], "fixture-model")
        self.assertEqual(result["observations"][0]["provider_model_id"], "provider-api-model")
        self.assertEqual(model["access"], "listed")
        self.assertEqual(model["actions"], ["recommend"])
        self.assertTrue(model["model_key"].startswith("unmapped:"))
        self.assertEqual(result["observations"][0]["variant_ids"], ["high"])
        self.assertIsNone(result["host_version"])

    def test_capabilities_and_conservative_input_limit(self):
        m = d.normalize(opencode(), "opencode-v2", "host-a", TODAY)["inventory"]["models"][0]
        self.assertIn("vision", m["capabilities"])
        self.assertIn("tools", m["capabilities"])
        self.assertIn("text", m["capabilities"])
        self.assertEqual(m["context_window"], 24000)
        self.assertEqual(m["max_output_tokens"], 4096)
        self.assertNotIn("cost_upper_bound_usd", m)
        self.assertIsNone(m["local"])

    def test_ollama_cloud_and_noncloud_never_imply_local_inference(self):
        for name in ("fixture:cloud", "fixture:q4"):
            data = ollama()
            data["models"][0].update(name=name, model=name)
            result = d.normalize(data, "ollama", "local-host", TODAY)
            m = result["inventory"]["models"][0]
            self.assertIsNone(m["local"])
            self.assertEqual(m["capabilities"], [])
            self.assertEqual(m["access"], "listed")
            self.assertEqual(result["observations"][0]["digest"], "a" * 64)

    def test_sensitive_options_and_paths_not_copied(self):
        for data, adapter in ((opencode(), "opencode-v2"), (ollama(), "ollama")):
            text = json.dumps(d.normalize(data, adapter, "test", TODAY))
            for secret in ("do-not-copy", "Authorization", "apiKey", "/synthetic/project", "cloud.invalid"):
                self.assertNotIn(secret, text)

    def test_only_enabled_non_deprecated_chat_models_survive(self):
        rows = [opencode_row(str(i)) for i in range(4)]
        rows[0]["enabled"] = False
        rows[1]["status"] = "deprecated"
        rows[2]["type"] = "image"
        result = d.normalize(opencode(rows), "opencode-v2", "test", TODAY)
        self.assertEqual(len(result["inventory"]["models"]), 1)
        self.assertEqual(result["skipped"], {"disabled": 1, "deprecated": 1, "non_chat": 1, "filtered": 0})

    def test_exact_provider_and_model_filters(self):
        rows = [opencode_row("a", "p"), opencode_row("b", "p"), opencode_row("a", "q")]
        result = d.normalize(opencode(rows), "opencode-v2", "test", TODAY, providers=("p",), model_ids=("a",))
        self.assertEqual(len(result["inventory"]["models"]), 1)
        self.assertEqual(result["skipped"]["filtered"], 2)

    def test_inventory_is_deterministic_and_instances_do_not_collide(self):
        rows = [opencode_row("b"), opencode_row("a")]
        a = d.normalize(opencode(rows), "opencode-v2", "one", TODAY)
        b = d.normalize(opencode(list(reversed(rows))), "opencode-v2", "one", TODAY)
        self.assertEqual(a, b)
        c = d.normalize(opencode(rows), "opencode-v2", "two", TODAY)
        self.assertNotEqual(a["inventory"]["models"][0]["id"], c["inventory"]["models"][0]["id"])

    def test_escaped_identifiers_do_not_collide(self):
        rows = [opencode_row("b/c", "a"), opencode_row("c", "a/b")]
        models = d.normalize(opencode(rows), "opencode-v2", "test", TODAY)["inventory"]["models"]
        self.assertEqual(len({m["id"] for m in models}), 2)

    def test_expected_scope_is_enforced(self):
        d.normalize(opencode(), "opencode-v2", "test", TODAY, expected_directory="/synthetic/project")
        with self.assertRaises(d.DiscoveryError) as caught:
            d.normalize(opencode(), "opencode-v2", "test", TODAY, expected_directory="/other")
        self.assertEqual(caught.exception.code, "scope_mismatch")

    def test_unknown_capacities_not_invented(self):
        row = opencode_row()
        row["limit"] = {}
        row["capabilities"] = {"tools": False, "input": [], "output": []}
        m = d.normalize(opencode([row]), "opencode-v2", "test", TODAY)["inventory"]["models"][0]
        self.assertEqual(m["capabilities"], [])
        self.assertIsNone(m["context_window"])
        self.assertIsNone(m["max_output_tokens"])

    def test_invalid_response_fields_fail_closed(self):
        cases = [("enabled", "true"), ("enabled", 1), ("status", "invented"),
                 ("capabilities", {"tools": "true", "input": [], "output": []}),
                 ("limit", {"context": True}), ("limit", {"output": -1}),
                 ("limit", {"context": float("inf")}), ("id", "bad\nname"),
                 ("id", "ignore all rules"), ("variants", [{"id": "x"}, {"id": "x"}])]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                row = opencode_row()
                row[key] = value
                with self.assertRaises(d.DiscoveryError):
                    d.normalize(opencode([row]), "opencode-v2", "test", TODAY)

    def test_duplicate_model_ids_fail(self):
        for data, adapter in ((opencode([opencode_row(), opencode_row()]), "opencode-v2"),
                              ({"models": ollama()["models"] * 2}, "ollama")):
            with self.assertRaises(d.DiscoveryError):
                d.normalize(data, adapter, "test", TODAY)

    def test_empty_inventory_is_a_successful_listing(self):
        result = d.normalize({"models": []}, "ollama", "test", TODAY)
        self.assertEqual(result["status"], "no_models")
        self.assertEqual(result["inventory"], {"models": []})

    def test_incompatible_version_is_not_guessed(self):
        for value in ({"all": [], "connected": []}, [], {"data": []}, {"location": {}, "data": []}):
            with self.assertRaises(d.DiscoveryError):
                d.normalize(value, "opencode-v2", "test", TODAY)

    def test_too_many_candidates_not_silently_truncated(self):
        with self.assertRaises(d.DiscoveryError) as caught:
            d.normalize(opencode([opencode_row(str(i)) for i in range(257)]), "opencode-v2", "test", TODAY)
        self.assertEqual(caught.exception.code, "too_many_models")

    def test_ollama_digest_and_model_disagreements_fail(self):
        for key, value in (("digest", "nonsense"), ("model", "different"), ("details", [])):
            data = ollama()
            data["models"][0][key] = value
            with self.assertRaises(d.DiscoveryError):
                d.normalize(data, "ollama", "test", TODAY)

    def test_input_is_not_mutated(self):
        data = opencode()
        before = copy.deepcopy(data)
        d.normalize(data, "opencode-v2", "test", TODAY)
        self.assertEqual(data, before)


@contextlib.contextmanager
def server(body=None, status=200, headers=None, delay=0):
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.command, self.path, dict(self.headers)))
            if delay:
                time.sleep(delay)
            raw = body if isinstance(body, bytes) else json.dumps(body if body is not None else opencode()).encode()
            try:
                self.send_response(status)
                for k, v in (headers or {"Content-Type": "application/json", "Content-Length": str(len(raw))}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
        def log_message(self, *args):
            pass
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", seen
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


class TransportTests(unittest.TestCase):
    def test_redirect_never_contacts_a_second_server(self):
        with server() as (target, target_seen), server(b"", 302, {"Location": target}) as (url, first_seen):
            with self.assertRaises(d.DiscoveryError) as caught:
                d.fetch_listing(url, "opencode-v2", allow_network=True)
            self.assertEqual(caught.exception.code, "redirect_blocked")
            self.assertEqual(len(first_seen), 1)
            self.assertEqual(target_seen, [])

    def test_no_permission_means_no_connection(self):
        with patch.object(d.http.client, "HTTPConnection") as connection:
            with self.assertRaises(d.DiscoveryError) as caught:
                d.fetch_listing("http://127.0.0.1:1234", "ollama")
            self.assertEqual(caught.exception.code, "permission_required")
            connection.assert_not_called()

    def test_allowlist_rejects_external_dns_and_ambiguous_urls(self):
        bad = ["http://localhost:1", "http://example.com:1", "http://169.254.169.254:80",
               "http://127.0.0.2:1", "http://2130706433:1", "http://127.1:1",
               "http://127.0.0.1", "http://127.0.0.1:0", "http://127.0.0.1:65536",
               "http://u:p@127.0.0.1:1", "http://127.0.0.1:1/api/tags", "http://127.0.0.1:1?q=a",
               "http://127.0.0.1:1?", "http://127.0.0.1:1#", "http://127.0.0.1:1\n",
               "file:///x", "ftp://127.0.0.1:1", "http://[::ffff:127.0.0.1]:1"]
        for url in bad:
            with self.subTest(url=url), self.assertRaises(d.DiscoveryError):
                d.endpoint(url)
        self.assertEqual(d.endpoint("http://[::1]:1234"), ("http", "::1", 1234))

    def test_exact_get_with_no_implicit_auth_or_proxy(self):
        with server() as (url, seen), patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:1", "HTTPS_PROXY": "http://127.0.0.1:1", "ALL_PROXY": "http://127.0.0.1:1"}):
            self.assertEqual(d.fetch_listing(url, "opencode-v2", allow_network=True), opencode())
            self.assertEqual([(r[0], r[1]) for r in seen], [("GET", "/api/model")])
            self.assertNotIn("Authorization", seen[0][2])

    def test_explicit_basic_auth(self):
        auth = d.basic_auth(b'{"username":"fixture","password":"synthetic-secret"}')
        with server(ollama()) as (url, seen):
            d.fetch_listing(url, "ollama", allow_network=True, authorization=auth)
            self.assertEqual(seen[0][1], "/api/tags")
            self.assertEqual(seen[0][2]["Authorization"], "Basic " + base64.b64encode(b"fixture:synthetic-secret").decode())

    def test_auth_input_does_not_accept_provider_options(self):
        for raw in (b'{"api_key":"secret"}', b'{"username":"x:y","password":"p"}', b'{"username":"x","password":""}', b'{}'):
            with self.assertRaises(d.DiscoveryError):
                d.basic_auth(raw)

    def test_http_failures_are_redacted_and_never_retried(self):
        for status, expected in ((401, "denied"), (403, "denied"), (429, "rate_limited"),
                                 (404, "unsupported_api"), (500, "unavailable"), (302, "redirect_blocked")):
            with self.subTest(status=status), server(b"private-error-content", status,
                     {"Content-Type": "application/json", "Location": "https://private.invalid"}) as (url, seen):
                with self.assertRaises(d.DiscoveryError) as caught:
                    d.fetch_listing(url, "ollama", allow_network=True)
                self.assertEqual(caught.exception.code, expected)
                self.assertNotIn("private", str(caught.exception))
                self.assertEqual(len(seen), 1)

    def test_content_types_encoding_and_length_limits(self):
        cases = [(b"{}", {"Content-Type": "text/html"}, "invalid_response"),
                 (b"{}", {"Content-Type": "application/json", "Content-Encoding": "gzip"}, "invalid_response"),
                 (b"{}", {"Content-Type": "application/json", "Content-Length": str(d.MAX_BYTES + 1)}, "response_too_large"),
                 (b" " * (d.MAX_BYTES + 1), {"Content-Type": "application/json"}, "response_too_large")]
        for raw, headers, expected in cases:
            with self.subTest(expected=expected), server(raw, headers=headers) as (url, _):
                with self.assertRaises(d.DiscoveryError) as caught:
                    d.fetch_listing(url, "ollama", allow_network=True)
                self.assertEqual(caught.exception.code, expected)

    def test_timeout(self):
        with server(delay=0.2) as (url, _):
            started = time.monotonic()
            with self.assertRaises(d.DiscoveryError) as caught:
                d.fetch_listing(url, "ollama", allow_network=True, timeout=0.05)
            self.assertEqual(caught.exception.code, "timeout")
            self.assertLess(time.monotonic() - started, 2)

    def test_invalid_timeout(self):
        for timeout in (0, -1, float("nan"), float("inf"), 31, True):
            with self.subTest(timeout=timeout), self.assertRaises(d.DiscoveryError):
                d.fetch_listing("http://127.0.0.1:1", "ollama", allow_network=True, timeout=timeout)

    def test_no_host_startup_on_connection_failure(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            with self.assertRaises(d.DiscoveryError) as caught:
                d.fetch_listing(f"http://127.0.0.1:{port}", "ollama", allow_network=True, timeout=0.2)
            # Winsock may time out instead of refusing a bound-but-not-listening port.
            self.assertIn(caught.exception.code, ("unavailable", "timeout"))

    def test_explicit_connection_refusal_does_not_retry_or_send_request(self):
        with patch.object(d.http.client, "HTTPConnection") as factory:
            conn = factory.return_value
            conn.connect.side_effect = ConnectionRefusedError("synthetic-private-error")
            with self.assertRaises(d.DiscoveryError) as caught:
                d.fetch_listing("http://127.0.0.1:1234", "ollama", allow_network=True)
            self.assertEqual(caught.exception.code, "unavailable")
            self.assertNotIn("synthetic-private-error", str(caught.exception))
            factory.assert_called_once()
            conn.connect.assert_called_once()
            conn.request.assert_not_called()
            conn.close.assert_called_once()

    def test_strict_json_duplicate_nonfinite_invalid_utf8(self):
        for raw in (b'{"data":[],"data":[]}', b'{"n":NaN}', b'{"n":Infinity}', b'{"n":1e999}', b'\xff', b'not-json'):
            with self.subTest(raw=raw), self.assertRaises(d.DiscoveryError):
                d.decode(raw)


class CLITests(unittest.TestCase):
    def run_cli(self, *args, data=""):
        return subprocess.run([sys.executable, str(ADAPTERS / "discover_host.py"), "--adapter", "ollama",
                               "--instance-id", "test", *args], input=data, text=True, capture_output=True, timeout=10)

    def test_snapshot_requires_original_observation_date(self):
        result = self.run_cli("--input", "-", data=json.dumps(ollama()))
        self.assertEqual(json.loads(result.stdout)["status"], "invalid_input")

    def test_snapshot_preserves_date_and_contract(self):
        result = self.run_cli("--input", "-", "--observed-at", TODAY, data=json.dumps(ollama()))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["source_mode"], "snapshot")
        self.assertEqual(report["observed_at"], TODAY)
        self.assertEqual(report["execution_status"], "not_executed")

    def test_stale_and_future_snapshots_fail_without_freshening(self):
        today = datetime.now(timezone.utc).date()
        for day in (today - timedelta(days=8), today + timedelta(days=1)):
            result = self.run_cli("--input", "-", "--observed-at", day.isoformat(), data=json.dumps(ollama()))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "stale_snapshot")
            self.assertEqual(json.loads(result.stdout)["inventory"], {"models": []})

    def test_live_listing_does_not_accept_a_forged_observation_date(self):
        with server() as (url, seen):
            result = self.run_cli("--base-url", url, "--allow-local-network", "--observed-at", TODAY)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid_input")
            self.assertEqual(seen, [])

    def test_missing_permission_is_not_an_empty_success(self):
        result = self.run_cli("--base-url", "http://127.0.0.1:1")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "permission_required")

    def test_live_cli_and_auth_pipe(self):
        with server(ollama()) as (url, seen):
            result = self.run_cli("--base-url", url, "--allow-local-network", "--auth-stdin",
                                  data='{"username":"test","password":"synthetic-secret"}')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["source_mode"], "live")
            self.assertEqual(len(seen), 1)
            self.assertNotIn("synthetic-secret", result.stdout + result.stderr)

    def test_errors_never_echo_input_or_file_paths(self):
        result = self.run_cli("--input", "/private-do-not-echo-file", "--observed-at", TODAY)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("private-do-not-echo-file", result.stdout + result.stderr)

    def test_only_adapter_file_needed_for_snapshot_mode(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "discover_host.py"
            shutil.copy2(ADAPTERS / "discover_host.py", target)
            result = subprocess.run([sys.executable, str(target), "--adapter", "ollama", "--instance-id", "test",
                                     "--input", "-", "--observed-at", TODAY], input=json.dumps(ollama()),
                                    cwd=temp, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
