"""Offline unit tests. These fixtures do not certify an installer or live AI host."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_package import NAME, REQUIRED, PackageError, frontmatter, manifest, validate_package
from install_smoke import check_case, isolated_env, source_url

HEADER = f"---\nname: {NAME}\ndescription: Select models for tasks.\nlicense: Apache-2.0\n---\n"


def fixture(parent: Path) -> Path:
    root = parent / NAME
    for filename in REQUIRED:
        path = root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    (root / "SKILL.md").write_text(HEADER + "# Skill\nSee [contract](references/contract.md).\n", encoding="utf-8")
    (root / "references/contract.md").write_text("# Contract\n", encoding="utf-8")
    (root / "assets/inventory-template.json").write_text('{"models": []}\n', encoding="utf-8")
    return root


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = fixture(self.parent)

    def test_complete_package(self):
        result = validate_package(self.root)
        self.assertEqual(result["file_count"], len(REQUIRED))
        self.assertEqual(result["local_file_links_checked"], 1)
        self.assertEqual(result["host_activation"], "not_tested")

    def test_missing_each_required_file(self):
        for filename in REQUIRED:
            with self.subTest(filename=filename):
                path = self.root / filename
                original = path.read_bytes()
                path.unlink()
                with self.assertRaises(PackageError):
                    validate_package(self.root)
                path.write_bytes(original)

    def test_directory_is_not_a_required_file(self):
        path = self.root / "scripts/route.py"
        path.unlink()
        path.mkdir()
        with self.assertRaises(PackageError):
            validate_package(self.root)

    def test_name_constraints(self):
        for name in ("UPPER", "bad--name", "-bad", "bad-", "x" * 65, "wrong-directory", True):
            with self.subTest(name=name), self.assertRaises(PackageError):
                frontmatter(HEADER.replace(NAME, str(name)) + "Instructions", NAME)

    def test_metadata_duplicate_key(self):
        with self.assertRaises(PackageError):
            frontmatter(HEADER.replace("description:", f"name: {NAME}\ndescription:") + "Body", NAME)

    def test_nested_duplicate_key(self):
        text = HEADER.replace("license:", "metadata:\n  a: one\n  a: two\nlicense:")
        with self.assertRaises(PackageError):
            frontmatter(text + "Body", NAME)

    def test_invalid_yaml(self):
        with self.assertRaises(PackageError):
            frontmatter(HEADER.replace("description: Select models for tasks.", "description: [") + "Body", NAME)

    def test_missing_delimiter_and_body(self):
        for text in ("# no frontmatter", HEADER, HEADER.replace("---\n", "", 1)):
            with self.subTest(text=text), self.assertRaises(PackageError):
                frontmatter(text, NAME)

    def test_scalar_types_and_limits(self):
        for value in ("true", "null", "123", "[]", '""', "x" * 1025):
            with self.subTest(value=value), self.assertRaises(PackageError):
                frontmatter(HEADER.replace("Select models for tasks.", value) + "Body", NAME)

    def test_compatibility_limit(self):
        with self.assertRaises(PackageError):
            frontmatter(HEADER.replace("license:", "compatibility: " + "x" * 501 + "\nlicense:") + "Body", NAME)

    def test_unsupported_field(self):
        with self.assertRaises(PackageError):
            frontmatter(HEADER.replace("license:", "unknown: value\nlicense:") + "Body", NAME)

    def test_metadata_requires_string_values(self):
        with self.assertRaises(PackageError):
            frontmatter(HEADER.replace("license:", "metadata:\n  version: 1\nlicense:") + "Body", NAME)

    def test_multiline_yaml_supported(self):
        value = HEADER.replace("Select models for tasks.", ">\n  Select models\n  for tasks.")
        self.assertIn("for tasks.", frontmatter(value + "Body", NAME)["description"])

    def test_aliases_rejected(self):
        with self.assertRaises(PackageError):
            frontmatter(HEADER.replace("description:", "extra: &a [a]\ndescription:") + "Body", NAME)

    def test_license_must_match_root(self):
        license_file = self.parent / "LICENSE"
        license_file.write_text("different", encoding="utf-8")
        with self.assertRaises(PackageError):
            validate_package(self.root, license_file)
        license_file.write_bytes((self.root / "LICENSE").read_bytes())
        self.assertEqual(validate_package(self.root, license_file)["status"], "passed")

    def test_line_endings_have_same_digest(self):
        before = manifest(self.root)
        for filename in before:
            path = self.root / filename
            lf = path.read_bytes().replace(b"\r\n", b"\n")
            path.write_bytes(lf.replace(b"\n", b"\r\n"))
        self.assertEqual(before, manifest(self.root))
        validate_package(self.root)

    def test_content_modification_changes_manifest(self):
        before = manifest(self.root)
        (self.root / "scripts/route.py").write_text("changed", encoding="utf-8")
        self.assertNotEqual(before, manifest(self.root))

    def test_bytecode_cache_excluded(self):
        before = manifest(self.root)
        path = self.root / "scripts/__pycache__/route.cpython.pyc"
        path.parent.mkdir()
        path.write_bytes(b"\x00bytecode")
        self.assertEqual(before, manifest(self.root))

    def test_hidden_and_credential_filenames(self):
        for filename in (".env", ".env.local", "auth.json", "credentials.json", ".npmrc"):
            with self.subTest(filename=filename):
                path = self.root / filename
                path.write_text("synthetic", encoding="utf-8")
                with self.assertRaises(PackageError):
                    manifest(self.root)
                path.unlink()

    def test_oversized_file(self):
        (self.root / "huge.txt").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        with self.assertRaises(PackageError):
            manifest(self.root)

    def test_broken_and_escaping_references(self):
        (self.parent / "outside.md").write_text("outside", encoding="utf-8")
        for target in ("missing.md", "../outside.md", "%2e%2e/outside.md", "//example.com/file", "javascript:alert"):
            with self.subTest(target=target):
                (self.root / "SKILL.md").write_text(HEADER + f"[bad]({target})", encoding="utf-8")
                with self.assertRaises(PackageError):
                    validate_package(self.root)

    def test_external_links_and_fenced_examples(self):
        text = HEADER + "[spec](https://agentskills.io/specification)\n```md\n[example](missing.md)\n```\n"
        (self.root / "SKILL.md").write_text(text, encoding="utf-8")
        self.assertEqual(validate_package(self.root)["local_file_links_checked"], 0)

    def test_nested_symlink_rejected(self):
        link = self.root / "linked.md"
        try:
            link.symlink_to(self.root / "SKILL.md")
        except OSError:
            self.skipTest("OS does not grant symlink creation")
        with self.assertRaises(PackageError):
            manifest(self.root)


class IsolationTests(unittest.TestCase):
    def test_secrets_and_runtime_overrides_not_inherited(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            inherited = {"PATH": os.environ.get("PATH", ""), "OPENAI_API_KEY": "fake",
                         "GH_TOKEN": "fake", "NPM_TOKEN": "fake", "NODE_OPTIONS": "fake",
                         "PYTHONPATH": "fake", "HTTP_PROXY": "fake", "HOME": "/real-home"}
            env = isolated_env(root / "case", root / "cache", inherited)
            for key in ("OPENAI_API_KEY", "GH_TOKEN", "NPM_TOKEN", "NODE_OPTIONS", "PYTHONPATH", "HTTP_PROXY"):
                self.assertNotIn(key, env)
            self.assertTrue(Path(env["HOME"]).is_relative_to(root))
            self.assertEqual(env["DISABLE_TELEMETRY"], "1")
            self.assertEqual(env["NPM_CONFIG_IGNORE_SCRIPTS"], "true")
            self.assertEqual(Path(env["NPM_CONFIG_USERCONFIG"]).read_text(), "")
            self.assertNotEqual(env["NPM_CONFIG_USERCONFIG"], env["NPM_CONFIG_GLOBALCONFIG"])
            self.assertEqual(Path(env["NPM_CONFIG_GLOBALCONFIG"]).read_text(), "")

    def test_remote_revision_is_exact(self):
        self.assertIn("/tree/" + "a" * 40, source_url("owner/repo", "a" * 40))
        for repository, revision in (("owner/repo", "main"), ("owner/repo;echo", "a" * 40),
                                     ("https://example.org", "a" * 40), ("owner/repo", "x" * 40)):
            with self.subTest(repository=repository), self.assertRaises(PackageError):
                source_url(repository, revision)

    def fake_case(self, mode):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            original = fixture(root / "source")
            expected = manifest(original)
            case_root = root / "case"
            installed = case_root / "project/.agents/skills" / NAME
            decision = {"status": "selected", "selected": {"id": "example-b"}, "action": "recommend",
                        "execution_status": "not_executed", "estimated_success_probability": None}

            def fake_run(command, cwd, env, log):
                if "add" in command:
                    if mode != "missing":
                        shutil.copytree(original, installed)
                        if mode == "corrupt":
                            (installed / "LICENSE").write_text("changed", encoding="utf-8")
                    return "installed"
                if "list" in command:
                    return "" if mode == "not-listed" else NAME
                if any(str(item).endswith("route.py") for item in command):
                    if mode == "executes":
                        decision["execution_status"] = "executed"
                    return json.dumps(decision)
                return '{"models": []}'

            with patch("install_smoke.run", side_effect=fake_run):
                return check_case(case_root, root / "cache", str(original), expected,
                                  ["node", "npx-cli.js"], "codex", "project", "copy")

    def test_mocked_installer_case_success(self):
        result = self.fake_case("good")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["host_activation"], "not_tested")

    def test_mocked_installer_failures_recorded(self):
        for mode in ("missing", "corrupt", "not-listed", "executes"):
            with self.subTest(mode=mode):
                result = self.fake_case(mode)
                self.assertEqual(result["status"], "failed")
                self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
