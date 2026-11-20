"""Integration with the unchanged router contract; all catalog rows are synthetic."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/intelligent-model-router/scripts"
sys.path.insert(0, str(SCRIPTS))
from route import MODEL, route, validate
from discover import normalize as import_catalog
from test_host_discovery import d, opencode, ollama, TODAY


class DiscoveryContractTests(unittest.TestCase):
    def request(self, models):
        return {"schema_version": "1.0", "host": {"id": "synthetic-host", "actions": ["delegate", "switch"]},
                "task": {"kind": "coding", "language": "en", "intent": "subagent", "risk": "low",
                         "required_capabilities": []},
                "policy": {"authorized_actions": ["delegate", "switch"]}, "models": models, "evidence": []}

    def test_both_adapters_produce_model_contract_records(self):
        for adapter, data in (("opencode-v2", opencode()), ("ollama", ollama())):
            models = d.normalize(data, adapter, "synthetic-host", TODAY)["inventory"]["models"]
            for model in models:
                validate(model, MODEL)
            decision = route(self.request(models), date.fromisoformat(TODAY))
            self.assertEqual(decision["status"], "no_eligible_models")
            self.assertEqual(decision["action"], "recommend")
            self.assertEqual(decision["execution_status"], "not_executed")

    def test_untrusted_catalog_cannot_grant_execution_or_prices(self):
        data = opencode()
        data["data"][0].update(access="verified", actions=["invoke", "delegate"], local=True,
                               model_key="benchmark-match", cost_upper_bound_usd=0)
        models = d.normalize(data, "opencode-v2", "synthetic-host", TODAY)["inventory"]["models"]
        self.assertEqual(models[0]["access"], "listed")
        self.assertEqual(models[0]["actions"], ["recommend"])
        self.assertNotIn("cost_upper_bound_usd", models[0])
        self.assertEqual(route(self.request(models))["action"], "recommend")

    def test_local_only_gate_survives_even_a_manual_access_declaration(self):
        models = d.normalize(ollama(), "ollama", "synthetic-host", TODAY)["inventory"]["models"]
        models[0]["access"] = "declared"  # Synthetic scenario, not an access verification.
        request = self.request(models)
        request["task"]["privacy"] = "local-only"
        result = route(request, date.fromisoformat(TODAY))
        self.assertEqual(result["status"], "no_eligible_models")
        self.assertIn("local_execution_required", result["excluded"][0]["reasons"])

    def test_empty_inventory_remains_needs_inventory(self):
        models = d.normalize({"models": []}, "ollama", "synthetic-host", TODAY)["inventory"]["models"]
        self.assertEqual(route(self.request(models))["status"], "needs_inventory")

    def test_changing_access_alone_cannot_promote_any_bundled_catalog_source(self):
        imports = [
            d.normalize(opencode(), "opencode-v2", "synthetic-host", TODAY)["inventory"],
            d.normalize(ollama(), "ollama", "synthetic-host", TODAY)["inventory"],
            import_catalog({"data": [{"id": "fixture"}]}, "openai-list", "example", TODAY),
            import_catalog(ollama(), "ollama-tags", "ollama", TODAY),
        ]
        for inventory in imports:
            for access in ("declared", "verified"):
                model = dict(inventory["models"][0], access=access)
                with self.subTest(source=model["access_source"], access=access):
                    result = route(self.request([model]), date.fromisoformat(TODAY))
                    self.assertEqual(result["status"], "no_eligible_models")
                    self.assertIsNone(result["selected"])
                    self.assertIn("access_source_catalog_only", result["excluded"][0]["reasons"])

    def test_legacy_offline_ollama_import_does_not_assert_local_execution(self):
        models = import_catalog(ollama(), "ollama-tags", "ollama", TODAY)["models"]
        self.assertIsNone(models[0]["local"])
        self.assertEqual(models[0]["access"], "listed")


if __name__ == "__main__":
    unittest.main()
