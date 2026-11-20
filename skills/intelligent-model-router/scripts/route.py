#!/usr/bin/env python3
"""Offline, provider-neutral routing plans. No network, credentials, or execution.

Python 3.10+. All scores are relative ranking heuristics, never probabilities.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

VERSION = "0.1.0-alpha.1"
MAX_BYTES = 2 * 1024 * 1024


class InputError(ValueError):
    """A request violates the public contract."""


def obj(properties: dict, required: tuple = ()) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(required), "additionalProperties": False}


def enum(*values: str) -> dict:
    return {"type": "string", "enum": list(values)}


def number(nullable: bool = False, minimum: float | None = 0) -> dict:
    result = {"type": ["number", "null"] if nullable else "number"}
    if minimum is not None:
        result["minimum"] = minimum
    return result


TEXT = {"type": "string", "minLength": 1, "maxLength": 512}
DATE = {"type": "string", "format": "date"}
BOOL = {"type": "boolean"}
INT = {"type": "integer", "minimum": 0}
STRINGS = {"type": "array", "items": TEXT, "uniqueItems": True, "maxItems": 256}
ACTIONS = {"type": "array", "items": enum("recommend", "delegate", "switch", "invoke"),
           "uniqueItems": True, "maxItems": 4}
MODEL = obj({
    "id": TEXT, "model_key": TEXT, "provider": TEXT, "api_model_id": TEXT,
    "access": enum("verified", "declared", "listed", "unknown", "unavailable"),
    "observed_at": DATE, "access_source": TEXT,
    "capabilities": STRINGS, "actions": ACTIONS,
    "context_window": {"type": ["integer", "null"], "minimum": 1},
    "max_output_tokens": {"type": ["integer", "null"], "minimum": 1},
    "local": {"type": ["boolean", "null"]},
    "estimated_cost_usd": number(True), "cost_upper_bound_usd": number(True),
    "estimated_latency_ms": number(True),
}, ("id", "model_key", "provider", "api_model_id", "access", "observed_at",
    "access_source", "capabilities", "actions", "local"))
EVIDENCE = obj({
    "source_id": TEXT, "origin_id": TEXT, "cohort_id": TEXT, "model_key": TEXT,
    "task": TEXT, "language": TEXT, "metric": TEXT, "harness": TEXT,
    "kind": enum("capability", "preference", "popularity"),
    "direction": enum("higher", "lower"), "value": number(minimum=None),
    "ci_lower": number(True, None), "ci_upper": number(True, None),
    "sample_size": {"type": ["integer", "null"], "minimum": 1},
    "observed_at": DATE, "source_url": TEXT, "license": TEXT, "synthetic": BOOL,
}, ("source_id", "origin_id", "cohort_id", "model_key", "task", "language",
    "metric", "harness", "kind", "direction", "value", "observed_at",
    "source_url", "license", "synthetic"))
REQUEST_SCHEMA = obj({
    "schema_version": enum("1.0"),
    "host": obj({"id": TEXT, "actions": ACTIONS}, ("id", "actions")),
    "task": obj({
        "kind": TEXT, "language": TEXT,
        "intent": enum("recommend", "auto", "subagent"),
        "risk": enum("low", "medium", "high", "critical"),
        "required_capabilities": STRINGS, "input_tokens": INT, "output_tokens": INT,
        "privacy": enum("any", "local-only"), "safe_boundary": BOOL,
        "delegation_depth": INT, "current_candidate_id": TEXT,
    }, ("kind", "language", "intent", "risk", "required_capabilities")),
    "policy": obj({
        "mode": enum("quality", "balanced", "economy", "latency"),
        "allowed_providers": STRINGS, "authorized_actions": ACTIONS,
        "max_cost_usd": number(True), "max_latency_ms": number(True),
        "max_evidence_age_days": INT, "max_access_age_days": INT,
        "max_delegation_depth": INT,
        "min_sources": {"type": "integer", "minimum": 1},
        "quality_tolerance": {"type": "number", "minimum": 0, "maximum": 1},
        "allow_synthetic": BOOL,
    }),
    "models": {"type": "array", "items": MODEL, "maxItems": 256},
    "evidence": {"type": "array", "items": EVIDENCE, "maxItems": 10000},
}, ("schema_version", "host", "task", "models", "evidence"))
REQUEST_SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
REQUEST_SCHEMA["title"] = "Intelligent Model Router request v1.0"


def validate(value: Any, schema: dict = REQUEST_SCHEMA, path: str = "$") -> None:
    """Validate the finite JSON Schema subset used by this module's own schema."""
    types = schema["type"]
    types = [types] if isinstance(types, str) else types
    actual = ("null" if value is None else "boolean" if type(value) is bool else
              "integer" if type(value) is int else "number" if type(value) is float else
              "string" if isinstance(value, str) else "array" if isinstance(value, list)
              else "object" if isinstance(value, dict) else "invalid")
    if actual not in types and not (actual == "integer" and "number" in types):
        raise InputError(f"{path}: incorrect type")
    if value is None:
        return
    if "enum" in schema and value not in schema["enum"]:
        raise InputError(f"{path}: unsupported value")
    if actual in ("integer", "number"):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise InputError(f"{path}: non-finite or excessively large number")
        if value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            raise InputError(f"{path}: number out of range")
    if actual == "string":
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 512):
            raise InputError(f"{path}: invalid string length")
        if any(ord(c) < 32 for c in value):
            raise InputError(f"{path}: control characters are not allowed")
        if schema.get("format") == "date":
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError:
                raise InputError(f"{path}: expected YYYY-MM-DD") from None
    if actual == "array":
        if len(value) > schema.get("maxItems", 10000):
            raise InputError(f"{path}: too many items")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise InputError(f"{path}: duplicate items")
        for i, child in enumerate(value):
            validate(child, schema["items"], f"{path}[{i}]")
    if actual == "object":
        if set(value) - set(schema["properties"]):
            raise InputError(f"{path}: unknown fields (credentials and prompts are not accepted)")
        if set(schema["required"]) - set(value):
            raise InputError(f"{path}: missing required fields")
        for key, child in value.items():
            validate(child, schema["properties"][key], f"{path}.{key}")


def fresh(stamp: str, today: date, days: int) -> bool:
    return 0 <= (today - date.fromisoformat(stamp)).days <= days


def eligibility(model: dict, task: dict, policy: dict, today: date) -> list[str]:
    reasons = []
    if model["access"] not in ("verified", "declared"):
        reasons.append("access_not_established")
    if not fresh(model["observed_at"], today, policy.get("max_access_age_days", 7)):
        reasons.append("access_stale_or_future")
    if "allowed_providers" in policy and model["provider"] not in policy["allowed_providers"]:
        reasons.append("provider_not_allowed")
    if not set(task["required_capabilities"]) <= set(model["capabilities"]):
        reasons.append("required_capability_missing")
    if task.get("privacy", "any") == "local-only" and model["local"] is not True:
        reasons.append("local_execution_required")
    tokens = task.get("input_tokens", 0) + task.get("output_tokens", 0)
    if tokens and (model.get("context_window") is None or model["context_window"] < tokens):
        reasons.append("context_capacity_insufficient_or_unknown")
    if task.get("output_tokens", 0) and (model.get("max_output_tokens") is None or
                                        model["max_output_tokens"] < task["output_tokens"]):
        reasons.append("output_capacity_insufficient_or_unknown")
    if policy.get("max_cost_usd") is not None and (model.get("cost_upper_bound_usd") is None or
                                                 model["cost_upper_bound_usd"] > policy["max_cost_usd"]):
        reasons.append("cost_bound_exceeded_or_unknown")
    if policy.get("max_latency_ms") is not None and (model.get("estimated_latency_ms") is None or
                                                    model["estimated_latency_ms"] > policy["max_latency_ms"]):
        reasons.append("latency_estimate_exceeded_or_unknown")
    return reasons


def common_evidence(records: list[dict], keys: set[str], task: dict, policy: dict,
                    today: date) -> tuple[list[dict], dict[str, int]]:
    """Keep complete, comparable cohorts; one latest cohort per evidence origin."""
    groups: dict[tuple, dict[str, dict]] = defaultdict(dict)
    ignored: dict[str, int] = defaultdict(int)
    for row in sorted(records, key=lambda r: (r["source_id"], r["source_url"])):
        url = urlsplit(row["source_url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query:
            raise InputError("evidence: use a canonical HTTPS source URL without credentials or query parameters")
        lo, hi = row.get("ci_lower"), row.get("ci_upper")
        if (lo is None) != (hi is None) or (lo is not None and not lo <= row["value"] <= hi):
            raise InputError("evidence: invalid confidence interval")
        if row["kind"] == "popularity":
            ignored["popularity_is_not_quality"] += 1
            continue
        if row["model_key"] not in keys or row["task"] != task["kind"] or row["language"] != task["language"]:
            ignored["task_language_or_model_mismatch"] += 1
            continue
        if row["synthetic"] and not policy.get("allow_synthetic", False):
            ignored["synthetic_not_allowed"] += 1
            continue
        if not fresh(row["observed_at"], today, policy.get("max_evidence_age_days", 90)):
            ignored["stale_or_future_evidence"] += 1
            continue
        group = tuple(row[k] for k in ("origin_id", "cohort_id", "metric", "harness", "observed_at", "kind"))
        existing = groups[group].get(row["model_key"])
        if existing:
            fields = ("value", "direction", "ci_lower", "ci_upper", "sample_size", "synthetic")
            if any(existing.get(k) != row.get(k) for k in fields):
                raise InputError("evidence: conflicting records for one origin/cohort/model")
            ignored["duplicate_origin_record"] += 1
            continue
        groups[group][row["model_key"]] = row
    origins: dict[str, list[tuple[tuple, dict]]] = defaultdict(list)
    for group, rows in groups.items():
        if set(rows) != keys:
            ignored["incomplete_cohort"] += len(rows)
            continue
        if len({r["direction"] for r in rows.values()}) != 1:
            raise InputError("evidence: inconsistent metric directions within a cohort")
        origins[group[0]].append((group, rows))
    chosen = []
    for origin in sorted(origins):
        options = sorted(origins[origin], key=lambda x: (x[0][4], x[0]))
        group, rows = options[-1]
        ignored["superseded_cohort"] += sum(len(r) for _, r in options[:-1])
        chosen.append({"origin_id": origin, "cohort_id": group[1], "rows": rows})
    return chosen, {k: v for k, v in sorted(ignored.items()) if v}


def pair_score(left: dict, right: dict) -> float:
    if left.get("ci_lower") is not None and right.get("ci_lower") is not None:
        if max(left["ci_lower"], right["ci_lower"]) <= min(left["ci_upper"], right["ci_upper"]):
            return 0.5  # Conservative overlap heuristic, not a significance test.
    if left["value"] == right["value"]:
        return 0.5
    win = left["value"] > right["value"]
    return float(win if left["direction"] == "higher" else not win)


def route(request: dict, today: date | None = None) -> dict:
    validate(request)
    today = today or datetime.now(timezone.utc).date()
    models, task, policy = request["models"], request["task"], request.get("policy", {})
    if len({m["id"] for m in models}) != len(models):
        raise InputError("models: duplicate candidate IDs")
    for m in models:
        cost, bound = m.get("estimated_cost_usd"), m.get("cost_upper_bound_usd")
        if cost is not None and bound is not None and cost > bound:
            raise InputError("models: cost estimate exceeds supplied upper bound")
    result = {"schema_version": "1.0", "engine_version": VERSION, "as_of": today.isoformat(),
              "status": "needs_inventory", "selected": None, "action": "recommend",
              "execution_status": "not_executed", "requires_approval": False,
              "estimated_success_probability": None, "rankings": [], "excluded": [],
              "evidence": [], "ignored_evidence": {}, "warnings": [], "reasons": []}
    if not models:
        result["reasons"].append("Provide an authorized host inventory or a user-declared model list.")
        return result
    eligible = []
    for m in models:
        reasons = eligibility(m, task, policy, today)
        if reasons:
            result["excluded"].append({"id": m["id"], "reasons": reasons})
        else:
            eligible.append(m)
    result["excluded"].sort(key=lambda x: x["id"])
    result["status"] = "no_eligible_models"
    if not eligible:
        return result
    keys = {m["model_key"] for m in eligible}
    cohorts, ignored = common_evidence(request["evidence"], keys, task, policy, today)
    result["ignored_evidence"] = ignored
    result["evidence"] = [{"origin_id": c["origin_id"], "cohort_id": c["cohort_id"],
                           "records": [c["rows"][k] for k in sorted(keys)]} for c in cohorts]
    if len(cohorts) < policy.get("min_sources", 1):
        result["status"] = "insufficient_evidence"
        result["rankings"] = [{"id": m["id"], "quality_score": None} for m in sorted(eligible, key=lambda x: x["id"])]
        result["reasons"].append("Not enough independent, fresh, complete comparison cohorts; no winner inferred.")
        return result
    quality = {k: sum(sum(pair_score(c["rows"][k], c["rows"][other]) for other in keys if other != k)
                       / (len(keys) - 1) if len(keys) > 1 else 0.5 for c in cohorts) / len(cohorts) for k in keys}
    if any(r["kind"] == "preference" for c in cohorts for r in c["rows"].values()):
        result["warnings"].append("Preference evidence measures comparative preference, not task correctness.")
    current = task.get("current_candidate_id")
    ranked = sorted(eligible, key=lambda m: (-quality[m["model_key"]], m["id"] != current, m["id"]))
    top = quality[ranked[0]["model_key"]]
    near = [m for m in ranked if quality[m["model_key"]] >= top - policy.get("quality_tolerance", 0.05)]
    selected = ranked[0]
    if sum(quality[m["model_key"]] == top for m in ranked) > 1:
        result["warnings"].append("Top quality scores are tied; efficiency preferences or a deterministic tiebreak decide.")
    mode = policy.get("mode", "quality")
    field = "estimated_latency_ms" if mode == "latency" else "estimated_cost_usd"
    if mode != "quality":
        if all(m.get(field) is not None for m in near):
            selected = min(near, key=lambda m: (m[field], -quality[m["model_key"]], m["id"] != current, m["id"]))
            result["reasons"].append(f"Minimized {field} within the configured quality tolerance.")
        else:
            result["warnings"].append("Efficiency data incomplete; used quality ranking, not an assumed zero cost/latency.")
    result["rankings"] = [{"id": m["id"], "quality_score": round(quality[m["model_key"]], 6),
                           "estimated_cost_usd": m.get("estimated_cost_usd"),
                           "estimated_latency_ms": m.get("estimated_latency_ms")} for m in ranked]
    result["status"] = "selected"
    result["selected"] = {k: selected[k] for k in ("id", "model_key", "provider", "api_model_id", "access")}
    result["reasons"].append("Passed eligibility gates; ranked only against the supplied eligible inventory.")
    result["warnings"].append("Quality scores are cohort-relative heuristics, not success probabilities or calibrated confidence.")
    if any(r["synthetic"] for c in cohorts for r in c["rows"].values()):
        result["warnings"].append("SYNTHETIC EVIDENCE: demonstration only; execution plans disabled.")
        return result
    if len(keys) == 1:
        result["warnings"].append("Only one model identity is eligible; no comparative advantage established.")
    if any(r.get("ci_lower") is None for c in cohorts for r in c["rows"].values()):
        result["warnings"].append("Some evidence lacks confidence intervals; small score gaps may not be meaningful.")
    if selected["access"] != "verified":
        result["warnings"].append("User-declared access: verify callability before execution.")
        return result
    permitted = set(request["host"]["actions"]) & set(selected["actions"]) & set(policy.get("authorized_actions", []))
    if task.get("delegation_depth", 0) >= policy.get("max_delegation_depth", 1):
        permitted.discard("delegate")
    if task["intent"] == "subagent":
        if "delegate" in permitted:
            result["action"] = "delegate"
    elif task["intent"] == "auto" and selected["id"] != current:
        if task.get("safe_boundary", False):
            result["action"] = next((a for a in ("switch", "invoke", "delegate") if a in permitted), "recommend")
        else:
            result["warnings"].append("No safe task boundary declared; automatic handoff not planned.")
    result["requires_approval"] = result["action"] != "recommend" and task["risk"] in ("high", "critical")
    if result["action"] == "recommend":
        result["reasons"].append("Recommendation only: the requested host action is unavailable, unauthorized, unnecessary, or unsafe.")
    else:
        result["reasons"].append("Host action is a plan only. Recheck access, policy, budget and tool permissions before dispatch.")
    return result


def no_duplicate_keys(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("JSON: duplicate object keys")
        result[key] = value
    return result


def read_request(path: str) -> dict:
    if path == "-":
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    else:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError("Request exceeds 2 MiB")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Request JSON file, or - for stdin")
    parser.add_argument("--as-of", help="Reproducible evaluation date, YYYY-MM-DD; default UTC today")
    parser.add_argument("--schema", action="store_true", help="Print the request JSON Schema")
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(REQUEST_SCHEMA, indent=2))
        return 0
    if not args.input:
        parser.error("--input is required unless --schema is used")
    try:
        today = date.fromisoformat(args.as_of) if args.as_of else None
        result = route(read_request(args.input), today)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result["status"] == "selected" else 2
    except (InputError, ValueError, OSError, RecursionError, OverflowError):
        # Do not echo attacker-controlled input, filesystem paths, or secrets.
        print(json.dumps({"status": "invalid_input", "execution_status": "not_executed",
                          "error": "Request invalid or unreadable; validate against --schema and the contract."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
