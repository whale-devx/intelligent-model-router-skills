#!/usr/bin/env python3
"""Run real npx installer checks in disposable homes; never start an AI host."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from validate_package import NAME, PackageError, manifest, validate_package

CLI_VERSION = "1.9.0"
MIN_NODE = (22, 20, 0)
TARGETS = {"codex": ".agents", "claude-code": ".claude"}


def isolated_env(root: Path, cache: Path, inherited: dict[str, str]) -> dict[str, str]:
    """Environment allowlist: no provider keys, GitHub tokens, proxies, or user config."""
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "SYSTEMDRIVE"}
    env = {k: v for k, v in inherited.items() if k.upper() in allowed}
    home, temp = root / "home", root / "tmp"
    for directory in (home, temp, cache, home / ".config", home / "AppData" / "Roaming",
                      home / "AppData" / "Local"):
        directory.mkdir(parents=True, exist_ok=True)
    empty = root / "empty-config"
    empty.write_text("", encoding="utf-8")
    global_config = root / "empty-global-npm-config"
    global_config.write_text("", encoding="utf-8")
    env.update({
        "HOME": str(home), "USERPROFILE": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_CACHE_HOME": str(home / ".cache"), "XDG_STATE_HOME": str(home / ".local/state"),
        "APPDATA": str(home / "AppData/Roaming"), "LOCALAPPDATA": str(home / "AppData/Local"),
        "CODEX_HOME": str(home / ".codex"), "CLAUDE_CONFIG_DIR": str(home / ".claude"),
        "TMP": str(temp), "TEMP": str(temp), "TMPDIR": str(temp),
        "NPM_CONFIG_USERCONFIG": str(empty), "NPM_CONFIG_GLOBALCONFIG": str(global_config),
        "NPM_CONFIG_CACHE": str(cache), "NPM_CONFIG_PREFIX": str(root / "npm-prefix"),
        "NPM_CONFIG_REGISTRY": "https://registry.npmjs.org/", "NPM_CONFIG_IGNORE_SCRIPTS": "true",
        "NPM_CONFIG_AUDIT": "false", "NPM_CONFIG_FUND": "false",
        "NPM_CONFIG_UPDATE_NOTIFIER": "false", "NPM_CONFIG_FETCH_RETRIES": "1",
        "NPM_CONFIG_FETCH_TIMEOUT": "60000",
        "GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
        "DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1", "CI": "true", "NO_COLOR": "1",
        "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8",
    })
    return env


def npx_command() -> list[str]:
    """Use the real npx JS entrypoint, avoiding cmd.exe argument interpolation on Windows."""
    node, npx = shutil.which("node"), shutil.which("npx")
    if not node or not npx:
        raise PackageError("Node.js and npx must be installed for the integration check")
    executable = Path(npx).resolve()
    entry = executable if executable.suffix == ".js" else executable.parent / "node_modules/npm/bin/npx-cli.js"
    if not entry.is_file():
        raise PackageError("Unsupported npm layout: cannot locate the npx JS entrypoint")
    return [node, str(entry)]


def run(command: list[str], cwd: Path, env: dict[str, str], log: list[dict]) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, encoding="utf-8",
                            errors="replace", capture_output=True, timeout=180, check=False)
    log.append({"argv": command, "exit_code": result.returncode,
                "stdout": result.stdout[-12000:], "stderr": result.stderr[-12000:]})
    if result.returncode:
        raise PackageError(f"Command failed with exit code {result.returncode}; see step log")
    return result.stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PackageError(message)


def source_url(repository: str, revision: str) -> str:
    require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)), "Invalid repository")
    require(bool(re.fullmatch(r"[a-f0-9]{40}", revision)), "GitHub tests require a full commit SHA")
    return f"https://github.com/{repository}/tree/{revision}/skills/{NAME}"


def check_case(root: Path, cache: Path, source: str, expected: dict[str, str],
               prefix: list[str], agent: str, scope: str, method: str) -> dict:
    case = {"agent_target": agent, "scope": scope, "method": method, "status": "failed", "steps": []}
    env = isolated_env(root, cache, dict(os.environ))
    project = root / "project"
    project.mkdir()
    cli = prefix + ["--yes", f"skills@{CLI_VERSION}"]
    try:
        command = cli + ["add", source, "--skill", NAME, "--agent", agent, "--yes"]
        if scope == "global":
            command.append("--global")
        if method == "copy":
            command.append("--copy")
        run(command, project, env, case["steps"])
        base = Path(env["HOME"]) if scope == "global" else project
        installed = base / TARGETS[agent] / "skills" / NAME
        require(installed.is_dir(), "Installer did not create the expected target skill directory")
        require(installed.resolve().is_relative_to(root.resolve()), "Installation escaped disposable case directory")
        validate_package(installed)
        require(manifest(installed) == expected, "Installed file manifest differs from reviewed source")
        listing = cli + ["list", "--agent", agent]
        if scope == "global":
            listing.append("--global")
        require(NAME in run(listing, project, env, case["steps"]), "skills list did not report the installed skill")
        # Execute outside both the repository and installed skill folder.
        outside = root / "outside"
        outside.mkdir()
        decision = json.loads(run([
            sys.executable, str(installed / "scripts/route.py"), "--input",
            str(installed / "assets/example-request.json"), "--as-of", "2026-11-20",
        ], outside, env, case["steps"]))
        require(decision.get("status") == "selected" and decision.get("selected", {}).get("id") == "example-b",
                "Installed route helper returned an unexpected synthetic decision")
        require(decision.get("action") == "recommend" and decision.get("execution_status") == "not_executed"
                and "estimated_success_probability" in decision and decision["estimated_success_probability"] is None,
                "Synthetic routing must remain non-executing with no invented probability")
        inventory = json.loads(run([
            sys.executable, str(installed / "scripts/discover.py"), "--input",
            str(installed / "assets/inventory-template.json"), "--format", "inventory",
        ], outside, env, case["steps"]))
        require(inventory == {"models": []}, "Installed discovery helper did not preserve empty inventory")
        require(manifest(installed) == expected, "Executing helpers changed installed package content")
        case.update(status="passed", files_verified=len(expected),
                    target_kind="symlink" if installed.is_symlink() else "directory",
                    helper_execution="synthetic_only", host_activation="not_tested", delegation="not_tested")
    except (PackageError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        case["error"] = str(exc)
    return case


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("local", "github"), default="local")
    parser.add_argument("--repository", default="whale-devx/intelligent-model-router-skills")
    parser.add_argument("--ref", default="", help="Exact public source commit, required with --source github")
    parser.add_argument("--output", type=Path, default=Path(".router-local/install-smoke.json"))
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    report = {"schema_version": "1.0", "status": "failed", "cli_version": CLI_VERSION,
              "source_mode": args.source, "source_repository": args.repository, "source_ref": args.ref or None,
              "observed_at": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
              "python": platform.python_version(), "cases": [], "setup_steps": [],
              "host_activation": "not_tested", "model_discovery": "not_tested", "delegation": "not_tested",
              "privacy": {"disposable_home": True, "inherited_environment": "allowlist",
                          "installer_telemetry_disabled": True, "npm_lifecycle_scripts_disabled": True}}
    scratch_text = ""
    try:
        expected = validate_package(repo / "skills" / NAME, repo / "LICENSE")["files_sha256_lf"]
        report["source_files_sha256_lf"] = expected
        with tempfile.TemporaryDirectory(prefix="imr-install-") as scratch:
            scratch_text = scratch
            root = Path(scratch)
            cache = root / "npm-cache"
            env = isolated_env(root / "setup", cache, dict(os.environ))
            prefix = npx_command()
            version = run([prefix[0], "--version"], root, env, report["setup_steps"]).strip()
            require(tuple(map(int, version.lstrip("v").split("."))) >= MIN_NODE, "Node.js >=22.20.0 is required")
            report["node"] = version
            report["checkout_commit"] = run(["git", "rev-parse", "HEAD"], repo, env, report["setup_steps"]).strip()
            npm = [prefix[0], str(Path(prefix[1]).with_name("npm-cli.js"))]
            report["npm"] = run(npm + ["--version"], root, env, report["setup_steps"]).strip()
            registry = json.loads(run(npm + ["view", f"skills@{CLI_VERSION}", "version", "dist.integrity", "--json"],
                                      root, env, report["setup_steps"]))
            require(registry.get("version") == CLI_VERSION and bool(registry.get("dist.integrity")),
                    "Registry version/integrity could not be verified")
            report["cli_registry_metadata"] = registry
            source = str(repo) if args.source == "local" else source_url(args.repository, args.ref)
            discovery = run(prefix + ["--yes", f"skills@{CLI_VERSION}", "add", source, "--list"],
                            root, env, report["setup_steps"])
            require(NAME in discovery, "Installer discovery did not find the skill")
            for agent in TARGETS:
                for scope in ("project", "global"):
                    for method in ("default", "copy"):
                        case_root = root / f"{agent}-{scope}-{method}"
                        case = check_case(case_root, cache, source, expected, prefix, agent, scope, method)
                        report["cases"].append(case)
                        print(f"{agent} / {scope} / {method}: {case['status']}", flush=True)
            require(manifest(repo / "skills" / NAME) == expected, "Source skill was modified during testing")
            require(all(case["status"] == "passed" for case in report["cases"]), "One or more installation cases failed")
            report["status"] = "passed"
    except (PackageError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report["error"] = str(exc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Logs contain only this public skill and synthetic data. Remove machine-specific temp paths.
    encoded = json.dumps(report, indent=2, ensure_ascii=False)
    if scratch_text:
        encoded = encoded.replace(json.dumps(scratch_text)[1:-1], "<scratch>")
    args.output.write_text(encoded + "\n", encoding="utf-8")
    print(f"Report: {args.output}; status: {report['status']}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
