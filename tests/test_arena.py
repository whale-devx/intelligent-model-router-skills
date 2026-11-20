"""Exercise the offline adapter with a generated, synthetic Parquet fixture."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import importlib.util

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "skills/intelligent-model-router/scripts/adapters"))
import arena
from route import fresh
from datetime import date

ROW = dict(model_name="Demo (High)", organization="example", license=None, rating=1250.,
           rating_lower=1240., rating_upper=1260., variance=4., vote_count=100.,
           rank=1., category="english", leaderboard_publish_date="2026-11-19")
MAP = dict(model_name="Demo (High)", organization="example", host_id="demo",
           endpoint_id="abc", provider="example", api_model_id="demo-v1",
           configuration="high", model_key="demo/v1@high")


class ArenaTests(unittest.TestCase):
    def request(self, entries):
        return {"schema_version": "1.0", "host": {"id": "demo", "actions": ["recommend"]},
                "task": {"kind": "text", "language": "en", "risk": "low", "intent": "recommend",
                         "required_capabilities": []}, "evidence": [],
                "models": [{"id": e["endpoint_id"], "provider": e["provider"], "api_model_id": e["api_model_id"],
                            "model_key": e["model_key"], "access": "listed", "access_source": "fixture",
                            "observed_at": "2026-11-19", "actions": ["recommend"], "capabilities": [], "local": None}
                           for e in entries]}

    def normalize(self, **overrides):
        return arena.normalize([dict(ROW, **overrides)], arena.identities([MAP]))

    def test_normalization(self):
        report = self.normalize()
        record, = report["evidence"]
        self.assertEqual((record["value"], record["ci_lower"], record["ci_upper"],
                          record["sample_size"]), (1250, 1240, 1260, 100))
        self.assertEqual(record["kind"], "preference")
        self.assertEqual(record["direction"], "higher")
        self.assertIn(arena.REVISION, record["source_url"])
        self.assertEqual(report["lineage"][0]["mapping"], MAP)
        for as_of in (date(2026, 11, 18), date(2027, 11, 19)):
            self.assertFalse(fresh(record["observed_at"], as_of, 90))

    def test_missing_and_unmapped(self):
        self.assertEqual(self.normalize(rating=None)["missing_rating"], 1)
        self.assertEqual(self.normalize(model_name="Demo")["evidence"], [])
        self.assertEqual(self.normalize(category="coding")["evidence"], [])
        record, = self.normalize(rating_lower=None, rating_upper=None, vote_count=None)["evidence"]
        self.assertIsNone(record["sample_size"])
        self.assertIsNone(record["ci_lower"])

    def test_invalid(self):
        for changes in (dict(rating_lower=None), dict(vote_count=0.5),
                        dict(leaderboard_publish_date="unknown")):
            with self.assertRaises(ValueError):
                self.normalize(**changes)
        with self.assertRaises(ValueError):
            arena.normalize([ROW, ROW], arena.identities([MAP]))
        with self.assertRaises(ValueError):
            arena.identities([MAP, MAP])

    def test_reserved_key_and_ambiguous_or_conflicting_equivalences(self):
        with self.assertRaisesRegex(ValueError, "placeholder"):
            arena.identities([dict(MAP, model_key="unmapped:abc")])
        with self.assertRaises(arena.IdentityMismatch):
            arena.identities([dict(MAP, configuration=" ")])
        for change in ({"configuration": "low"}, {"model_key": "different-key"}, {"model_name": "Other"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                arena.identities([MAP, dict(MAP, endpoint_id="def", **change)])

    def test_request_checks_every_identity_field_and_rejects_duplicate_ids(self):
        group = arena.identities([MAP])
        for field in ("endpoint_id", "provider", "api_model_id", "model_key"):
            with self.subTest(field=field), self.assertRaises(arena.IdentityMismatch):
                arena.check_request(group, self.request([dict(MAP, **{field: "different"})]))
        request = self.request([MAP])
        request["host"]["id"] = "other-host"
        with self.assertRaises(arena.IdentityMismatch):
            arena.check_request(group, request)
        with self.assertRaises(arena.IdentityMismatch):
            arena.check_request(group, self.request([MAP, MAP]))

    def test_shared_key_requires_all_endpoints_and_emits_one_observation(self):
        other = dict(MAP, endpoint_id="second", provider="other", api_model_id="other-model-id")
        request = self.request([MAP, other, dict(MAP, endpoint_id="unrelated", model_key="elsewhere")])
        original = json.dumps(request)
        with self.assertRaises(arena.IdentityMismatch):
            arena.check_request(arena.identities([MAP]), request)
        group = arena.identities([other, MAP])
        self.assertEqual(arena.check_request(group, request), "matched")
        self.assertEqual(json.dumps(request), original)
        report = arena.normalize([ROW], group)
        self.assertEqual(report, arena.normalize([ROW], arena.identities([MAP, other])))
        self.assertEqual(len(report["evidence"]), 1)
        self.assertEqual(report["lineage"][0]["mapping"], MAP)
        self.assertEqual(report["lineage"][0]["equivalent_mappings"], [other])

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "optional Parquet reader unavailable")
    def test_parquet_boundary(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, mapping = root / "test.parquet", root / "mapping.json"
            mapping.write_text(json.dumps([MAP]), encoding="utf-8")
            for row in (ROW, {"rating": 1.0}):
                pq.write_table(pa.Table.from_pylist([row]), snapshot)
                with self.assertRaisesRegex(ValueError, "digest"):
                    arena.run(snapshot, mapping)
                digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
                with patch.object(arena, "DIGEST", digest), patch("socket.socket", side_effect=AssertionError):
                    if row is ROW:
                        standalone = arena.run(snapshot, mapping)
                        self.assertEqual(standalone, arena.run(snapshot, mapping))
                        self.assertEqual(standalone["request_identity_check"], "not_run")
                        request = root / "request.json"
                        request.write_text(json.dumps(self.request([MAP])), encoding="utf-8")
                        bound = arena.run(snapshot, mapping, request)
                        self.assertEqual(bound["evidence"], standalone["evidence"])
                        self.assertEqual(bound["request_identity_check"], "matched")
                        mapping.write_text(json.dumps([dict(MAP, model_name="Demo (Low)")]), encoding="utf-8")
                        with self.assertRaisesRegex(arena.IdentityMismatch, "absent"):
                            arena.run(snapshot, mapping, request)
                        mapping.write_text("[]", encoding="utf-8")
                        self.assertEqual(arena.run(snapshot, mapping, request)["request_identity_check"], "no_mappings")
                    else:
                        with self.assertRaisesRegex(ValueError, "schema"):
                            arena.run(snapshot, mapping)
