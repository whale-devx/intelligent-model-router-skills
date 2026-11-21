"""Offline contract, policy, ranking, and packaging regression tests.

All model names and numbers are synthetic. Action tests clear the synthetic
marker ONLY to exercise the contract; this is not evidence about a real model.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "intelligent-model-router"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
from route import InputError, REQUEST_SCHEMA, route, validate  # noqa: E402
from discover import normalize  # noqa: E402

TODAY = date(2026, 11, 20)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.request = json.loads((SKILL / "assets" / "example-request.json").read_text())

    def run_route(self):
        return route(self.request, TODAY)

    def action_fixture(self):
        self.request["policy"]["authorized_actions"] = ["delegate", "switch", "invoke"]
        for model in self.request["models"]:
            model["access"] = "verified"
            model["access_source"] = "test-host-access-record"
        for row in self.request["evidence"]:
            row["synthetic"] = False

    def test_example_balanced(self):
        result = self.run_route()
        self.assertEqual(result["selected"]["id"], "example-b")
        self.assertEqual(result["action"], "recommend")
        self.assertEqual(result["execution_status"], "not_executed")
        self.assertIsNone(result["estimated_success_probability"])

    def test_quality_mode_deterministic_tie(self):
        self.request["policy"]["mode"] = "quality"
        self.assertEqual(self.run_route()["selected"]["id"], "example-a")

    def test_current_model_wins_quality_tie(self):
        self.request["policy"]["mode"] = "quality"
        self.request["task"]["current_candidate_id"] = "example-b"
        self.assertEqual(self.run_route()["selected"]["id"], "example-b")

    def test_economy_respects_quality_tolerance(self):
        self.request["policy"].update(mode="economy", quality_tolerance=0)
        self.assertEqual(self.run_route()["selected"]["id"], "example-b")
        self.request["policy"]["quality_tolerance"] = 1
        self.assertEqual(self.run_route()["selected"]["id"], "example-c")

    def test_latency_mode(self):
        self.request["policy"].update(mode="latency", quality_tolerance=1)
        self.assertEqual(self.run_route()["selected"]["id"], "example-c")

    def test_unknown_cost_is_not_free(self):
        self.request["models"][1].pop("estimated_cost_usd")
        self.assertEqual(self.run_route()["selected"]["id"], "example-a")

    def test_no_inventory(self):
        self.request["models"] = []
        self.assertEqual(self.run_route()["status"], "needs_inventory")

    def test_access_gates(self):
        for state in ("listed", "unknown", "unavailable"):
            with self.subTest(state=state):
                for model in self.request["models"]:
                    model["access"] = state
                self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_access_claim_needs_a_source_even_when_all_other_evidence_matches(self):
        self.action_fixture()
        for model in self.request["models"]:
            model["access_source"] = "   "
        decision = self.run_route()
        self.assertEqual(decision["status"], "no_eligible_models")
        self.assertTrue(all("access_source_missing" in row["reasons"] for row in decision["excluded"]))

    def test_demo_inventory_cannot_plan_delegation_with_otherwise_eligible_evidence(self):
        self.action_fixture()
        for model in self.request["models"]:
            model["access_source"] = "synthetic-fixture"
        decision = self.run_route()
        self.assertEqual((decision["status"], decision["action"]), ("selected", "recommend"))
        self.assertTrue(any("synthetic" in warning.lower() for warning in decision["warnings"]))

    def test_catalog_claim_excludes_only_its_endpoint(self):
        self.action_fixture()
        previous = self.run_route()["selected"]["id"]
        for model in self.request["models"]:
            if model["id"] == previous:
                model["access_source"] = "user-provided-catalog"
        decision = self.run_route()
        self.assertNotEqual(decision["selected"]["id"], previous)
        self.assertEqual(decision["excluded"], [{"id": previous, "reasons": ["access_source_catalog_only"]}])
        self.assertEqual((decision["action"], decision["execution_status"]), ("delegate", "not_executed"))

    def test_empty_provider_allowlist_denies_all(self):
        self.request["policy"]["allowed_providers"] = []
        self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_local_only_rejects_cloud_and_unknown(self):
        self.request["task"]["privacy"] = "local-only"
        self.request["models"][1]["local"] = None
        self.assertEqual(self.run_route()["status"], "no_eligible_models")
        self.request["models"][1]["local"] = True
        self.assertEqual(self.run_route()["selected"]["id"], "example-b")

    def test_context_includes_output_reserve(self):
        self.request["task"].update(input_tokens=31000, output_tokens=2000)
        self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_output_capacity(self):
        self.request["task"]["output_tokens"] = 9000
        self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_unknown_context_fails_closed(self):
        for model in self.request["models"]:
            model["context_window"] = None
        self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_tool_capability_required(self):
        self.request["task"]["required_capabilities"].append("computer-use")
        self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_budget_requires_upper_bound(self):
        for model in self.request["models"]:
            model.pop("cost_upper_bound_usd")
        self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_budget_and_latency_filters(self):
        self.request["policy"].update(max_cost_usd=0.011, max_latency_ms=1000)
        self.assertEqual(self.run_route()["selected"]["id"], "example-c")

    def test_cost_estimate_cannot_exceed_bound(self):
        self.request["models"][0]["cost_upper_bound_usd"] = 0
        with self.assertRaises(InputError):
            self.run_route()

    def test_stale_and_future_inventory(self):
        for stamp in ("2026-01-01", "2026-11-21"):
            with self.subTest(stamp=stamp):
                for model in self.request["models"]:
                    model["observed_at"] = stamp
                self.assertEqual(self.run_route()["status"], "no_eligible_models")

    def test_stale_and_future_evidence(self):
        for stamp in ("2026-01-01", "2026-11-21"):
            with self.subTest(stamp=stamp):
                for row in self.request["evidence"]:
                    row["observed_at"] = stamp
                self.assertEqual(self.run_route()["status"], "insufficient_evidence")

    def test_popularity_never_used_as_quality(self):
        for row in self.request["evidence"]:
            row["kind"] = "popularity"
        self.assertEqual(self.run_route()["status"], "insufficient_evidence")

    def test_language_and_task_match_exactly(self):
        for key, value in (("language", "th"), ("kind", "research")):
            original = self.request["task"][key]
            self.request["task"][key] = value
            self.assertEqual(self.run_route()["status"], "insufficient_evidence")
            self.request["task"][key] = original

    def test_missing_evidence_abstains(self):
        self.request["evidence"] = []
        result = self.run_route()
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["selected"])
        self.assertTrue(all(r["quality_score"] is None for r in result["rankings"]))

    def test_partial_cohort_not_imputed(self):
        self.request["evidence"].pop()
        self.assertEqual(self.run_route()["status"], "insufficient_evidence")

    def test_model_identity_exact_no_fuzzy_match(self):
        self.request["models"][0]["model_key"] += "-other-effort"
        self.assertEqual(self.run_route()["status"], "insufficient_evidence")

    def test_coverage_distinguishes_absent_identities_from_disjoint_cohorts(self):
        missing = self.request["models"][0]["model_key"]
        self.request["models"].append(dict(self.request["models"][0], id="alternate-endpoint"))
        for row in self.request["evidence"]:
            if row["model_key"] == missing:
                row["observed_at"] = "2020-01-01"
        coverage = self.run_route()["evidence_coverage"]
        self.assertEqual(coverage, {"eligible_identities": 3, "missing_model_keys": [missing],
                                    "incomplete_cohorts": 2, "complete_origins": 0, "required_origins": 2})
        # A fresh observation in another harness covers this identity alone.
        self.request["evidence"].append(dict(self.request["evidence"][0], harness="other",
                                             observed_at=TODAY.isoformat()))
        result = self.run_route()
        self.assertEqual(result["evidence_coverage"], dict(coverage, missing_model_keys=[], incomplete_cohorts=3))
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["selected"])
        self.assertTrue(all(row["quality_score"] is None for row in result["rankings"]))

    def test_coverage_counts_origins_and_filters_ineligible_models(self):
        self.request["models"][2]["access"] = "listed"
        self.request["policy"]["min_sources"] = 3
        self.request["evidence"] += [dict(r, source_id="mirror") for r in self.request["evidence"]]
        self.assertEqual(self.run_route()["evidence_coverage"],
                         {"eligible_identities": 2, "missing_model_keys": [], "incomplete_cohorts": 0,
                          "complete_origins": 2, "required_origins": 3})
        self.request["evidence"] = []
        self.assertEqual(self.run_route()["evidence_coverage"]["missing_model_keys"],
                         sorted(m["model_key"] for m in self.request["models"][:2]))

    def test_coverage_preserves_unicode_identity_through_cli_pipe(self):
        missing = "ตัวอย่าง/รุ่น-🌙"
        self.request["models"][0]["model_key"] = missing
        result = subprocess.run([sys.executable, str(SCRIPTS / "route.py"), "--input", "-",
                                 "--as-of", TODAY.isoformat()], input=json.dumps(self.request).encode(),
                                capture_output=True, env={**os.environ, "PYTHONIOENCODING": "ascii:strict"})
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(json.loads(result.stdout)["evidence_coverage"]["missing_model_keys"], [missing])

    def test_matching_discovery_placeholders_cannot_supply_quality(self):
        model = self.request["models"][0]
        old = model["model_key"]
        model["model_key"] = "unmapped:" + model["id"]
        for row in self.request["evidence"]:
            if row["model_key"] == old:
                row["model_key"] = model["model_key"]
        result = self.run_route()
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["selected"])
        self.assertEqual(result["ignored_evidence"]["unmapped_benchmark_identity"], 2)
        self.assertTrue(all(r["quality_score"] is None for r in result["rankings"]))

    def test_mirror_does_not_inflate_evidence(self):
        before = self.run_route()
        mirror = copy.deepcopy(self.request["evidence"])
        for row in mirror:
            row["source_id"] = "mirror"
        self.request["evidence"].extend(mirror)
        after = self.run_route()
        self.assertEqual(before["rankings"], after["rankings"])
        self.assertEqual(len(after["evidence"]), 2)
        self.assertEqual(after["ignored_evidence"]["duplicate_origin_record"], 6)

    def test_conflicting_duplicate_rejected(self):
        row = copy.deepcopy(self.request["evidence"][0])
        row["value"] = 999
        self.request["evidence"].append(row)
        with self.assertRaises(InputError):
            self.run_route()

    def test_one_source_url_with_conflicting_license_labels_is_ambiguous(self):
        rows = self.request["evidence"]
        original = rows[0]
        mirror = dict(original, source_id="z-mirror", source_url="https://example.invalid/mirror")
        for first, second in ((original, dict(original, license="other-label")),
                              (mirror, dict(mirror, source_id="zz-mirror", license="other-label"))):
            for pair in ((first, second), (second, first)):
                self.request["evidence"] = rows + list(pair)
                with self.subTest(url=first["source_url"]), self.assertRaisesRegex(InputError, "license"):
                    self.run_route()

    def test_mirror_citations_stay_with_the_scored_observation(self):
        before = self.run_route()
        row = self.request["evidence"][0]
        citation = {"source_id": "mirror", "source_url": "https://example.invalid/reprint",
                    "license": "fixture-reprint-label"}
        mirror = dict(row, **citation)
        self.request["evidence"] += [mirror, mirror, dict(row)]
        after = self.run_route()
        self.request["evidence"].reverse()
        self.assertEqual(self.run_route(), after)
        self.assertEqual(before["rankings"], after["rankings"])
        self.assertEqual(after["ignored_evidence"]["duplicate_origin_record"], 3)
        for index, cohort in enumerate(after["evidence"]):
            self.assertEqual(cohort["records"], before["evidence"][index]["records"])
            if cohort["origin_id"] == row["origin_id"]:
                self.assertEqual(cohort["additional_sources"], {row["model_key"]: [citation]})
            else:
                self.assertNotIn("additional_sources", cohort)

        self.request["policy"]["min_sources"] = 3
        below_minimum = self.run_route()
        self.assertEqual(below_minimum["status"], "insufficient_evidence")
        self.assertEqual(below_minimum["evidence_coverage"]["complete_origins"], 2)
        self.assertEqual(below_minimum["evidence"], after["evidence"])

    def test_mirrors_of_superseded_cohorts_stay_out_of_the_report(self):
        before = self.run_route()
        older = [dict(r, observed_at="2026-11-01", license="earlier-fixture-license")
                 for r in self.request["evidence"]]
        self.request["evidence"] += older + [dict(r, source_id="older-mirror") for r in older]
        self.assertEqual(self.run_route()["evidence"], before["evidence"])

    def test_latest_complete_cohort_per_origin(self):
        older = copy.deepcopy(self.request["evidence"])
        for row in older:
            row.update(cohort_id="old-v1", observed_at="2026-11-01", value=1-row["value"])
        self.request["evidence"].extend(older)
        self.assertEqual(self.run_route()["selected"]["id"], "example-b")
        self.assertEqual(len(self.run_route()["evidence"]), 2)

    def test_duplicate_endpoint_same_model_not_extra_vote(self):
        before = self.run_route()["rankings"][0]["quality_score"]
        model = copy.deepcopy(self.request["models"][0])
        model["id"] = "second-endpoint"
        self.request["models"].append(model)
        self.assertEqual(self.run_route()["rankings"][0]["quality_score"], before)

    def test_overlap_intervals_create_ties(self):
        for row in self.request["evidence"]:
            row.update(ci_lower=0, ci_upper=1)
        self.assertTrue(all(r["quality_score"] == .5 for r in self.run_route()["rankings"]))

    def test_invalid_interval(self):
        self.request["evidence"][0].update(ci_lower=.95, ci_upper=1)
        with self.assertRaises(InputError):
            self.run_route()

    def test_lower_is_better(self):
        for row in self.request["evidence"]:
            row["direction"] = "lower"
        self.assertEqual(self.run_route()["selected"]["id"], "example-c")

    def test_inconsistent_metric_direction(self):
        self.request["evidence"][0]["direction"] = "lower"
        with self.assertRaises(InputError):
            self.run_route()

    def test_synthetic_opt_in_and_execution_block(self):
        self.request["policy"]["allow_synthetic"] = False
        self.assertEqual(self.run_route()["status"], "insufficient_evidence")
        self.request["policy"]["allow_synthetic"] = True
        self.request["policy"]["authorized_actions"] = ["delegate"]
        for m in self.request["models"]:
            m["access"] = "verified"
        self.assertEqual(self.run_route()["action"], "recommend")

    def test_declared_access_never_plans_execution(self):
        self.action_fixture()
        for m in self.request["models"]:
            m["access"] = "declared"
        self.assertEqual(self.run_route()["action"], "recommend")

    def test_subagent_plan_requires_three_way_permission(self):
        self.action_fixture()
        self.assertEqual(self.run_route()["action"], "delegate")
        for location, field in ((self.request["host"], "actions"),
                                (self.request["policy"], "authorized_actions"),
                                (self.request["models"][1], "actions")):
            previous = location[field]
            location[field] = []
            self.assertEqual(self.run_route()["action"], "recommend")
            location[field] = previous

    def test_high_risk_requires_approval(self):
        self.action_fixture()
        for risk in ("high", "critical"):
            self.request["task"]["risk"] = risk
            self.assertTrue(self.run_route()["requires_approval"])

    def test_auto_switch_requires_boundary(self):
        self.action_fixture()
        self.request["task"].update(intent="auto", safe_boundary=True)
        self.assertEqual(self.run_route()["action"], "switch")
        self.request["task"]["safe_boundary"] = False
        self.assertEqual(self.run_route()["action"], "recommend")

    def test_no_unnecessary_switch(self):
        self.action_fixture()
        self.request["task"].update(intent="auto", current_candidate_id="example-b")
        self.assertEqual(self.run_route()["action"], "recommend")

    def test_depth_cap_for_subagent_and_auto(self):
        self.action_fixture()
        self.request["host"]["actions"] = ["delegate"]
        self.request["task"]["delegation_depth"] = 1
        for intent in ("subagent", "auto"):
            self.request["task"]["intent"] = intent
            self.assertEqual(self.run_route()["action"], "recommend")

    def test_input_order_does_not_change_selection(self):
        before = self.run_route()
        self.request["models"].reverse()
        self.request["evidence"].reverse()
        self.assertEqual(before, self.run_route())

    def test_invalid_scalar_and_unknown_fields(self):
        for value in (True, -1, float("inf"), float("nan"), "0.1"):
            self.request["policy"]["max_cost_usd"] = value
            with self.subTest(value=value), self.assertRaises(InputError):
                self.run_route()
        self.request["policy"].pop("max_cost_usd")
        self.request["api_key"] = "not-a-real-secret"
        with self.assertRaises(InputError):
            self.run_route()

    def test_duplicate_candidates_rejected(self):
        self.request["models"].append(copy.deepcopy(self.request["models"][0]))
        with self.assertRaises(InputError):
            self.run_route()

    def test_unsafe_source_urls_rejected(self):
        for url in ("http://example.com", "https://user:password@example.com", "https://example.com/?key=secret"):
            self.request["evidence"][0]["source_url"] = url
            with self.assertRaises(InputError):
                self.run_route()

    def test_request_not_mutated(self):
        before = copy.deepcopy(self.request)
        self.run_route()
        self.assertEqual(self.request, before)


class DiscoveryAndPackagingTests(unittest.TestCase):
    def test_catalog_does_not_grant_access(self):
        result = normalize({"data": [{"id": "example-model", "api_key": "discard-this"}]},
                           "openai-list", "example", "2026-11-20")
        model = result["models"][0]
        self.assertEqual(model["access"], "listed")
        self.assertEqual(model["capabilities"], [])
        self.assertIsNone(model["local"])
        self.assertNotIn("discard-this", json.dumps(result))

    def test_ollama_import_is_listed_not_verified(self):
        result = normalize({"models": [{"name": "example:latest"}]}, "ollama-tags", "local", "2026-11-20")
        self.assertIsNone(result["models"][0]["local"])
        self.assertEqual(result["models"][0]["access"], "listed")

    def test_empty_manual_inventory(self):
        self.assertEqual(normalize({"models": []}, "inventory", "manual", "2026-11-20"), {"models": []})

    def test_discovery_rejects_duplicate_ids(self):
        with self.assertRaises(InputError):
            normalize({"data": [{"id": "x"}, {"id": "x"}]}, "openai-list", "x", "2026-11-20")

    def test_skill_manifest_and_local_links(self):
        text = (SKILL / "SKILL.md").read_text()
        header = text.split("---", 2)[1]
        fields = dict(line.split(": ", 1) for line in header.strip().splitlines())
        self.assertEqual(fields["name"], SKILL.name)
        self.assertTrue(1 <= len(fields["description"]) <= 1024)
        self.assertLess(len(text.splitlines()), 200)
        self.assertNotIn("allowed-tools", fields)
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in target and not target.startswith("#"):
                self.assertTrue((SKILL / target).is_file(), target)

    def test_core_has_no_execution_or_network_imports(self):
        for path in SCRIPTS.glob("*.py"):
            tree = ast.parse(path.read_text())
            modules = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
            modules += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
            self.assertFalse(set(modules) & {"subprocess", "socket", "requests", "urllib.request", "os"})

    def test_cli_schema(self):
        completed = subprocess.run([sys.executable, str(SCRIPTS / "route.py"), "--schema"],
                                   capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout), REQUEST_SCHEMA)

    def test_cli_duplicate_keys_and_redacted_error(self):
        completed = subprocess.run([sys.executable, str(SCRIPTS / "route.py"), "--input", "-"],
                                   input='{"api_key":"do-not-echo", "api_key":"secret"}',
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["status"], "invalid_input")
        self.assertNotIn("do-not-echo", completed.stdout + completed.stderr)

    def test_cli_example(self):
        completed = subprocess.run([sys.executable, str(SCRIPTS / "route.py"), "--input",
                                   str(SKILL / "assets" / "example-request.json"), "--as-of", "2026-11-20"],
                                   capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout)["selected"]["id"], "example-b")

    def test_cli_discovery(self):
        completed = subprocess.run([sys.executable, str(SCRIPTS / "discover.py"), "--input", "-",
                                   "--format", "openai-list", "--provider", "example", "--observed-at", "2026-11-20"],
                                   input='{"data":[{"id":"fixture"}]}', capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout)["models"][0]["access"], "listed")

    def test_cli_raw_catalog_requires_its_original_date(self):
        for fmt, catalog in (("openai-list", {"data": [{"id": "fixture"}]}),
                             ("ollama-tags", {"models": [{"name": "fixture"}]})):
            with self.subTest(fmt=fmt):
                args = [sys.executable, str(SCRIPTS / "discover.py"), "--format", fmt, "--input", "-"]
                undated = subprocess.run(args, input=json.dumps(catalog), capture_output=True, text=True)
                self.assertNotEqual(undated.returncode, 0)
                self.assertIn("--observed-at", undated.stdout + undated.stderr)
                self.assertNotIn("models", json.loads(undated.stdout))
                dated = subprocess.run([*args, "--observed-at", "2021-02-03"], input=json.dumps(catalog),
                                       capture_output=True, text=True, check=True)
                self.assertEqual(json.loads(dated.stdout)["models"][0]["observed_at"], "2021-02-03")

    def test_cli_normalized_inventory_preserves_dates_without_an_import_date(self):
        models = json.loads((SKILL / "assets/example-request.json").read_text())["models"][:2]
        models[0]["observed_at"] = "2021-02-03"
        for extra in ([], ["--observed-at", "2026-11-20"]):
            args = [sys.executable, str(SCRIPTS / "discover.py"), "--format", "inventory", "--input", "-", *extra]
            imported = subprocess.run(args, input=json.dumps({"models": models}), capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(imported.stdout)["models"], models)

    def test_cli_oversized_input(self):
        completed = subprocess.run([sys.executable, str(SCRIPTS / "route.py"), "--input", "-"],
                                   input=" " * (2 * 1024 * 1024 + 1), capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1)

    def test_only_skill_folder_needed(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / "intelligent-model-router"
            shutil.copytree(SKILL, installed)
            completed = subprocess.run([sys.executable, str(installed / "scripts" / "route.py"), "--input",
                                       str(installed / "assets" / "example-request.json"), "--as-of", "2026-11-20"],
                                       cwd=directory, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(completed.stdout)["execution_status"], "not_executed")


if __name__ == "__main__":
    unittest.main()
