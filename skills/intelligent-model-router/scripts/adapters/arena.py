"""Offline adapter for an audited Arena text leaderboard snapshot."""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from route import DATE, EVIDENCE, MAX_BYTES, TEXT, UNMAPPED_PREFIX, no_duplicate_keys, validate

REVISION = "d3517dc2bbc13f82d925d8524f9c5cb5e4563d36"
DIGEST = "239038f6719d356628af34320a07b46c8e24d410ccfa0fbb26b39e7e9a4b000f"
DATASET = "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/blob/" + REVISION
SOURCE = DATASET + "/text/latest-00000-of-00001.parquet"
SOURCE_NOTICE = (
    f"Arena Leaderboard Dataset by Arena ({DATASET}/README.md). "
    "Licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). "
    f"The importer uses the pinned raw text leaderboard ({SOURCE}). "
    "It selects mapped English observations and emits normalized fields for routing."
)
FIELDS = {"model_name", "organization", "license", "rating", "rating_lower", "rating_upper",
          "variance", "vote_count", "rank", "category", "leaderboard_publish_date"}
IDENTITY = {"organization", "model_name", "model_key", "host_id", "endpoint_id", "provider",
            "api_model_id", "configuration"}


class IdentityMismatch(ValueError):
    """An identity check failed. Messages never include caller-supplied values."""


def read_local(path, limit):
    if str(path).startswith(("\\\\", "//")) or not path.is_file():
        raise ValueError("expected local file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("input too large")
    return data


def identities(items):
    if not isinstance(items, list) or len(items) > 1000:
        raise ValueError("expected mapping array")
    result = {}
    keys = {}
    endpoints = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != IDENTITY:
            raise ValueError("invalid identity mapping")
        for value in item.values():
            validate(value, TEXT)
            if not value.strip():
                raise IdentityMismatch("Mapping identifiers and configuration must contain text.")
        identity = item["organization"], item["model_name"]
        endpoint = item["host_id"], item["endpoint_id"]
        key = item["model_key"]
        if key.startswith(UNMAPPED_PREFIX):
            raise IdentityMismatch("A discovery placeholder cannot be a benchmark identity.")
        if endpoint in endpoints or (key in keys and keys[key] != identity):
            raise ValueError("ambiguous identity mapping")
        group = result.setdefault(identity, [])
        if group and (group[0]["model_key"] != key or group[0]["configuration"] != item["configuration"]):
            raise ValueError("conflicting configurations for one Arena identity")
        endpoints.add(endpoint)
        keys[key] = identity
        group.append(item)
    for group in result.values():
        group.sort(key=lambda entry: (entry["host_id"], entry["endpoint_id"]))
    return result


def check_request(mapping, request):
    """Bind each imported model key to all endpoints carrying it in this request."""
    validate(request)
    if len({m["id"] for m in request["models"]}) != len(request["models"]):
        raise IdentityMismatch("Duplicate endpoint IDs in request.")
    mapped = {(e["host_id"], e["endpoint_id"], e["provider"], e["api_model_id"], e["model_key"])
              for group in mapping.values() for e in group}
    keys = {group[0]["model_key"] for group in mapping.values()}
    actual = {(request["host"]["id"], m["id"], m["provider"], m["api_model_id"], m["model_key"])
              for m in request["models"] if m["model_key"] in keys}
    if actual != mapped:
        raise IdentityMismatch("Mapped endpoints differ from the request. Review host, endpoint, provider, API ID and model key.")
    return "matched" if mapped else "no_mappings"


def normalize(rows, mapping):
    evidence = []
    lineage = []
    seen = set()
    unmapped = missing = 0
    for row in rows:
        if row["category"] != "english":
            continue
        identity = row["organization"], row["model_name"]
        stamp = row["leaderboard_publish_date"]
        if not all(identity):
            unmapped += 1
            continue
        for field in identity:
            validate(field, TEXT)
        validate(stamp, DATE)
        if (identity, stamp) in seen:
            raise ValueError("duplicate Arena observation")
        seen.add((identity, stamp))
        if identity not in mapping:
            unmapped += 1
            continue
        if row["rating"] is None:
            missing += 1
            continue
        count = row["vote_count"]
        if count is not None and (count < 1 or not float(count).is_integer()):
            raise ValueError("invalid vote count")
        lo, hi = row["rating_lower"], row["rating_upper"]
        if (lo is None) != (hi is None) or (lo is not None and not lo <= row["rating"] <= hi):
            raise ValueError("invalid rating bounds")
        primary, *equivalent = mapping[identity]
        record = dict(source_id="lmarena-ai/leaderboard-dataset", origin_id="arena/text",
                      cohort_id=f"arena/text/latest/english/{REVISION}/{stamp}",
                      task="text", language="en", metric="rating", harness="arena/text",
                      model_key=primary["model_key"], kind="preference", direction="higher",
                      value=row["rating"], ci_lower=lo, ci_upper=hi,
                      sample_size=int(count) if count is not None else None, observed_at=stamp,
                      source_url=SOURCE, license="CC-BY-4.0", synthetic=False)
        validate(record, EVIDENCE)
        evidence.append(record)
        lineage.append(dict(mapping=primary, observed_at=stamp, category="english",
                            model_license=row["license"], reasoning_effort=None,
                            benchmark_model_revision=None, evaluation_harness_version=None))
        if equivalent:
            lineage[-1]["equivalent_mappings"] = equivalent
    missing_identities = mapping.keys() - {identity for identity, _ in seen}
    return dict(evidence=evidence, lineage=lineage, unmapped=unmapped, missing_rating=missing,
                unmatched_mappings=len(missing_identities),
                source_url=SOURCE, revision=REVISION, sha256=DIGEST, attribution="Arena",
                source_notice=SOURCE_NOTICE)


def run(snapshot, mappings, request=None):
    data = read_local(snapshot, 635072)
    if hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError("unsupported snapshot digest")
    mapping = identities(json.loads(read_local(mappings, 1024 * 1024),
                                    object_pairs_hook=no_duplicate_keys))
    binding = "not_run"
    if request is not None:
        binding = check_request(mapping, json.loads(read_local(request, MAX_BYTES),
                                                    object_pairs_hook=no_duplicate_keys))
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(io.BytesIO(data))
    if set(parquet.schema_arrow.names) != FIELDS:
        raise ValueError("incompatible text schema")
    rows = (row for batch in parquet.iter_batches(batch_size=256) for row in batch.to_pylist())
    report = normalize(rows, mapping)
    if request is not None and report["unmatched_mappings"]:
        raise IdentityMismatch("A mapped Arena identity is absent from the English snapshot.")
    report["request_identity_check"] = binding
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("mappings", type=Path)
    parser.add_argument("--request", type=Path, help="Check mapped endpoint identities against this local v1 request")
    args = parser.parse_args()
    try:
        report = run(args.snapshot, args.mappings, args.request)
        print(json.dumps(report, sort_keys=True, allow_nan=False))
    except ImportError:
        sys.exit("Install the optional pyarrow==22.0.0 reader.")
    except IdentityMismatch as exc:
        sys.exit(str(exc))
    except (ValueError, OSError, OverflowError, RecursionError):
        sys.exit("Invalid local Arena snapshot, mapping or request. Check the pin, schema and endpoint identities.")
