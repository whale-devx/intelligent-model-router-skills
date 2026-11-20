#!/usr/bin/env python3
"""Import an explicitly supplied model inventory/catalog. Never scans or contacts hosts."""
from __future__ import annotations

import argparse
import json

from route import DATE, MODEL, InputError, obj, read_request, validate


def normalize(data: dict, format_name: str, provider: str, observed_at: str | None) -> dict:
    if observed_at is not None:
        validate(observed_at, DATE)
    if format_name == "inventory":
        schema = obj({"models": {"type": "array", "items": MODEL, "maxItems": 256}}, ("models",))
        validate(data, schema)
        models = data["models"]
    else:
        if observed_at is None:
            raise InputError("A raw catalog needs its original observation date")
        key, id_key = ("data", "id") if format_name == "openai-list" else ("models", "name")
        if not isinstance(data, dict) or not isinstance(data.get(key), list):
            raise InputError("Catalog must contain a model array")
        models = []
        for row in data[key]:
            if not isinstance(row, dict) or not isinstance(row.get(id_key), str):
                raise InputError("Catalog entry must have a model identifier")
            model_id = row[id_key]
            model = {"id": f"{provider}/{model_id}", "model_key": f"unmapped:{provider}/{model_id}",
                     "provider": provider, "api_model_id": model_id, "access": "listed",
                     "observed_at": observed_at, "access_source": "user-provided-catalog",
                     "capabilities": [], "actions": ["recommend"],
                     "context_window": None, "max_output_tokens": None,
                     "local": None}
            validate(model, MODEL)
            models.append(model)
    if len(models) > 256 or len({m["id"] for m in models}) != len(models):
        raise InputError("Too many models or duplicate candidate IDs")
    return {"models": sorted(models, key=lambda m: m["id"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Explicit local JSON file, or - for stdin")
    parser.add_argument("--format", required=True, choices=("inventory", "openai-list", "ollama-tags"))
    parser.add_argument("--provider", default="user-supplied", help="Catalog owner label, not a credential")
    parser.add_argument("--observed-at", metavar="YYYY-MM-DD",
                        help="Original observation date, required for openai-list and ollama-tags")
    args = parser.parse_args()
    if args.format != "inventory" and args.observed_at is None:
        print(json.dumps({"status": "invalid_input", "error": "Supply the catalog's original date with --observed-at YYYY-MM-DD."}))
        return 1
    try:
        output = normalize(read_request(args.input), args.format, args.provider, args.observed_at)
        print(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (InputError, ValueError, OSError, RecursionError, OverflowError):
        print(json.dumps({"status": "invalid_input", "error": "Invalid or unreadable inventory/catalog."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
