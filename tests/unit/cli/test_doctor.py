"""Unit tests for the ``ts-doctor`` cli module.

These tests call the helper functions directly rather than going through
:func:`run_script`, so failures show up as exceptions in pytest output
instead of JSON envelopes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tech_scout.cli.doctor import (
    _check_directory,
    _check_import,
    _check_locale_templates,
    _check_packaged_templates,
    _check_python_version,
    _check_writable_root,
    _wrap,
    main,
)
from tech_scout.locales import get_locale


class TestSmallCheckHelpers:
    def test_python_version_ok(self) -> None:
        status, msg = _check_python_version()
        assert status == "ok"
        assert msg.startswith("Python ")

    def test_import_existing_package(self) -> None:
        status, _msg = _check_import("pydantic")
        assert status == "ok"

    def test_import_missing_package(self) -> None:
        status, msg = _check_import("definitely_not_a_real_package_xyzzy")
        assert status == "error"
        assert "import definitely_not_a_real_package_xyzzy failed" in msg

    def test_check_directory_existing(self, tmp_path: Path) -> None:
        status, _msg = _check_directory(tmp_path, must_exist=True)
        assert status == "ok"

    def test_check_directory_missing_must_exist(self, tmp_path: Path) -> None:
        status, _msg = _check_directory(tmp_path / "missing", must_exist=True)
        assert status == "error"

    def test_check_directory_missing_optional(self, tmp_path: Path) -> None:
        status, _msg = _check_directory(tmp_path / "missing", must_exist=False)
        assert status == "warning"

    def test_check_directory_is_a_file(self, tmp_path: Path) -> None:
        f = tmp_path / "file"
        f.write_text("x", encoding="utf-8")
        status, _msg = _check_directory(f, must_exist=True)
        assert status == "error"

    def test_check_writable_root_existing(self, tmp_path: Path) -> None:
        status, _msg = _check_writable_root(tmp_path)
        assert status == "ok"

    def test_check_writable_root_creatable(self, tmp_path: Path) -> None:
        # Parent exists, target does not — doctor should warn (will be created)
        status, _msg = _check_writable_root(tmp_path / "future")
        assert status == "warning"

    def test_check_writable_root_orphan(self, tmp_path: Path) -> None:
        status, _msg = _check_writable_root(tmp_path / "no" / "parent" / "either")
        assert status == "error"

    def test_check_writable_root_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "blocker"
        f.write_text("x", encoding="utf-8")
        status, _msg = _check_writable_root(f)
        assert status == "error"

    def test_packaged_templates_check_ok(self) -> None:
        check = _check_packaged_templates()
        assert check["status"] == "ok"
        assert check["name"] == "packaged_templates"

    def test_locale_templates_present(self, tmp_path: Path) -> None:
        spec = get_locale("en")
        # Use the real packaged templates dir
        from tech_scout.output import packaged_templates_root

        results = _check_locale_templates(packaged_templates_root(), spec)
        assert all(r["status"] == "ok" for r in results)

    def test_locale_templates_missing_subdir(self, tmp_path: Path) -> None:
        spec = get_locale("en")
        results = _check_locale_templates(tmp_path / "no-templates", spec)
        assert any(r["status"] == "error" for r in results)

    def test_wrap_packs_status(self) -> None:
        out = _wrap("name", ("ok", "msg"))
        assert out == {"name": "name", "status": "ok", "message": "msg"}


class TestDoctorMain:
    def test_main_returns_summary_in_normal_environment(self) -> None:
        result = main()
        assert "platform" in result
        assert "python" in result
        assert "checks" in result
        assert "locales" in result
        # Locale templates checks must appear
        names = {c["name"] for c in result["checks"]}
        assert "locale_en_templates" in names
        assert "locale_tr_templates" in names

    def test_main_raises_when_required_check_fails(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force a failure by making `ts_doctor` think the templates dir is gone.
        from tech_scout.cli import doctor as doctor_module

        def fake_check_packaged() -> dict[str, str]:
            return {
                "name": "packaged_templates",
                "status": "error",
                "message": "simulated absence",
            }

        monkeypatch.setattr(
            doctor_module,
            "_check_packaged_templates",
            fake_check_packaged,
        )

        from tech_scout.domain.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            main()

    def test_main_includes_new_categories(self) -> None:
        result = main()
        for check in result["checks"]:
            assert "category" in check
            assert check["category"] in {
                "runtime",
                "paths",
                "packaging",
                "locales",
                "output",
                "smoke",
            }
        assert set(result["by_category"].keys()) == {
            "runtime",
            "paths",
            "packaging",
            "locales",
            "output",
            "smoke",
        }


class TestCategorize:
    def test_attaches_category_key(self) -> None:
        from tech_scout.cli.doctor import _categorize

        check = {"name": "x", "status": "ok", "message": "y"}
        out = _categorize("runtime", check)
        assert out["category"] == "runtime"
        assert "category" not in check  # original not mutated


class TestEnvOverrides:
    def test_redacts_sensitive_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from tech_scout.cli.doctor import _env_overrides

        monkeypatch.setenv("TECH_SCOUT_API_KEY", "supersecret")
        monkeypatch.setenv("TECH_SCOUT_SOME_TOKEN", "abc")
        monkeypatch.setenv("TECH_SCOUT_SECRET_VALUE", "xyz")
        monkeypatch.setenv("TECH_SCOUT_LOG_LEVEL", "DEBUG")

        out = _env_overrides()
        assert out["TECH_SCOUT_API_KEY"] == "<redacted>"
        assert out["TECH_SCOUT_SOME_TOKEN"] == "<redacted>"
        assert out["TECH_SCOUT_SECRET_VALUE"] == "<redacted>"
        assert out["TECH_SCOUT_LOG_LEVEL"] == "DEBUG"

    def test_ignores_non_tech_scout_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from tech_scout.cli.doctor import _env_overrides

        monkeypatch.setenv("OTHER_PROJECT_KEY", "stuff")
        out = _env_overrides()
        assert "OTHER_PROJECT_KEY" not in out


class TestWriteProbe:
    def test_success_in_writable_dir(self, tmp_path: Path) -> None:
        from tech_scout.cli.doctor import _check_write_probe

        result = _check_write_probe(tmp_path)
        assert result["status"] == "ok"

    def test_creates_missing_dir(self, tmp_path: Path) -> None:
        from tech_scout.cli.doctor import _check_write_probe

        result = _check_write_probe(tmp_path / "nested" / "deep")
        assert result["status"] == "ok"

    def test_path_is_a_file_errors(self, tmp_path: Path) -> None:
        from tech_scout.cli.doctor import _check_write_probe

        f = tmp_path / "not-a-dir"
        f.write_text("x", encoding="utf-8")
        result = _check_write_probe(f)
        assert result["status"] == "error"


class TestDiskSpace:
    def test_returns_ok_for_real_temp(self, tmp_path: Path) -> None:
        from tech_scout.cli.doctor import _check_disk_space

        result = _check_disk_space(tmp_path)
        assert result["status"] == "ok"

    def test_warns_when_free_space_low(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from tech_scout.cli import doctor as doctor_module

        class FakeUsage:
            free = 1024 * 1024  # 1 MB free

        monkeypatch.setattr(
            doctor_module.shutil,
            "disk_usage",
            lambda *_args, **_kwargs: FakeUsage(),
        )
        result = doctor_module._check_disk_space(tmp_path)
        assert result["status"] == "warning"
        assert "MB free" in result["message"]


class TestSmokeChecks:
    def test_template_smoke_render_passes(self) -> None:
        from tech_scout.cli.doctor import _check_template_smoke_render
        from tech_scout.config.settings import get_settings

        results = list(_check_template_smoke_render(get_settings()))
        assert results
        ok_locales = {
            r["name"]
            for r in results
            if r["status"] == "ok" and r["name"].startswith("template_smoke_")
        }
        assert "template_smoke_en" in ok_locales
        assert "template_smoke_tr" in ok_locales

    def test_audit_lock_probe_succeeds(self) -> None:
        from tech_scout.cli.doctor import _check_audit_lock_probe

        result = _check_audit_lock_probe()
        assert result["status"] == "ok"

    def test_slug_roundtrip_succeeds(self) -> None:
        from tech_scout.cli.doctor import _check_slug_roundtrip

        result = _check_slug_roundtrip()
        assert result["status"] == "ok"
