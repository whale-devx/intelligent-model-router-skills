#!/usr/bin/env python3
"""Validate this project's installable skill, not host behavior or security certification."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

NAME = "intelligent-model-router"
REQUIRED = {
    "SKILL.md", "LICENSE", "scripts/route.py", "scripts/discover.py",
    "references/contract.md", "references/host-protocol.md", "references/sources.md",
    "assets/example-request.json", "assets/inventory-template.json",
}
FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")


class PackageError(ValueError):
    """Invalid package or a violated project packaging rule."""


class UniqueLoader(yaml.SafeLoader):
    """Safe YAML with duplicate keys rejected rather than silently overwritten."""

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise PackageError("Non-string or duplicate frontmatter key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def frontmatter(text: str, directory_name: str) -> dict:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise PackageError("SKILL.md must start with delimited YAML frontmatter")
    header, body = text[4:].split("\n---\n", 1)
    if len(header) > 16384 or not body.strip():
        raise PackageError("Oversized frontmatter or empty skill instructions")
    try:
        # Anchors/aliases are unnecessary for this package; reject expansion risks.
        for event in yaml.parse(header):
            if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None):
                raise PackageError("YAML anchors and aliases are not allowed in this package")
        data = yaml.load(header, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise PackageError("Invalid YAML frontmatter") from exc
    if not isinstance(data, dict) or set(data) - FIELDS:
        raise PackageError("Unsupported frontmatter fields")
    name = data.get("name")
    if (not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
            or len(name) > 64 or name != directory_name):
        raise PackageError("Invalid skill name or directory/name mismatch")
    for key, maximum in (("description", 1024), ("compatibility", 500)):
        value = data.get(key)
        if key == "description" or key in data:
            if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                raise PackageError(f"Invalid {key}")
    if data.get("license") != "Apache-2.0":
        raise PackageError("This project requires its Apache-2.0 license declaration")
    if "allowed-tools" in data and not isinstance(data["allowed-tools"], str):
        raise PackageError("allowed-tools must be a string, not a permission grant")
    if "metadata" in data:
        metadata = data["metadata"]
        if not isinstance(metadata, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in metadata.items()
        ):
            raise PackageError("metadata must map strings to strings")
    return data


def normalized_bytes(path: Path) -> bytes:
    value = path.read_bytes()
    return value if b"\x00" in value else value.replace(b"\r\n", b"\n")


def manifest(root: Path) -> dict[str, str]:
    """Per-file SHA-256. Text line endings normalize to LF; not a skills-lock hash."""
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise PackageError("Skill root is not a directory")
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink():
            raise PackageError("Nested symlinks are not allowed in this package")
        if "__pycache__" in relative.parts:
            continue
        if any(part.startswith(".") or part.lower() in {"auth.json", "credentials.json"}
               for part in relative.parts):
            raise PackageError("Hidden files or credential-like filenames in skill package")
        if path.is_dir():
            continue
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            raise PackageError("Unsupported file type or oversized package file")
        result[relative.as_posix()] = hashlib.sha256(normalized_bytes(path)).hexdigest()
        if len(result) > 256:
            raise PackageError("Too many package files")
    return result


def check_links(root: Path, files: dict[str, str]) -> int:
    """Check inline Markdown local file targets. Not a full Markdown/anchor validator."""
    count = 0
    for relative in files:
        if not relative.endswith(".md"):
            continue
        path = root / relative
        text = path.read_text(encoding="utf-8")
        # Inline links in fenced code are examples, not navigation.
        text = re.sub(r"(?ms)^```[^\n]*\n.*?^```\s*$", "", text)
        for match in LINK.finditer(text):
            target = match.group(1).strip().split(' "', 1)[0].strip("<>")
            parts = urlsplit(target)
            if parts.scheme:
                if parts.scheme not in {"https", "http", "mailto"}:
                    raise PackageError("Unsupported link scheme")
                continue
            if parts.netloc:
                raise PackageError("Protocol-relative links are not allowed")
            if not parts.path:
                continue
            destination = (path.parent / unquote(parts.path)).resolve()
            if not destination.is_relative_to(root) or not destination.is_file():
                raise PackageError(f"Broken or escaping local reference in {relative}")
            count += 1
    return count


def validate_package(root: Path, expected_license: Path | None = None) -> dict:
    root = root.resolve(strict=True)
    files = manifest(root)
    missing = REQUIRED - set(files)
    if missing:
        raise PackageError("Missing package files: " + ", ".join(sorted(missing)))
    metadata = frontmatter((root / "SKILL.md").read_text(encoding="utf-8"), root.name)
    if metadata["name"] != NAME:
        raise PackageError("Unexpected project skill identity")
    if expected_license is not None and normalized_bytes(root / "LICENSE") != normalized_bytes(expected_license):
        raise PackageError("Bundled license differs from repository license")
    count = check_links(root, files)
    return {"status": "passed", "skill": NAME, "file_count": len(files),
            "local_file_links_checked": count, "files_sha256_lf": files,
            "host_activation": "not_tested", "model_execution": "not_tested"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-license", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate_package(args.path, args.expected_license), indent=2))
        return 0
    except (PackageError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
