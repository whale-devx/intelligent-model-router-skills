"""Exercise the offline adapter with a generated, synthetic Parquet fixture."""
import hashlib
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

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "optional Parquet reader unavailable")
    def test_parquet_boundary(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        import json
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
                        self.assertEqual(arena.run(snapshot, mapping), arena.run(snapshot, mapping))
                    else:
                        with self.assertRaisesRegex(ValueError, "schema"):
                            arena.run(snapshot, mapping)
