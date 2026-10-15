"""Az EXE saját NVIDIA-profiljának tranzakciós próbái driverírás nélkül."""
from __future__ import annotations

import copy
import ctypes
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from gpttranslator import nvidia_compat


VRR_ID = 0x10A879CF


def application(path: Path | str) -> dict:
    return {
        "path": str(path), "friendly": "GPTTranslator", "predefined": False,
        "launcher": "", "file_in_folder": "", "flags": 0, "command_line": "",
    }


def setting(value: int = 1, *, setting_id: int = VRR_ID) -> dict:
    return {"id": setting_id, "type": 0, "value": value, "location": 0, "predefined": False}


def canonical_path(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(path))


class FakeDRS:
    """Csak save() után látható a módosítás egy új session számára."""

    def __init__(self):
        self.profiles: dict[int, dict] = {}
        self.next_handle = 1
        self.operations: list[tuple] = []
        self.sessions = 0
        self.save_modes: list[str] = []

    @contextmanager
    def session(self):
        self.sessions += 1
        yield FakeSession(self)

    def add_profile(self, path: Path, *, value: int | None = None,
                    name: str = "Személyes profil", predefined: bool = False) -> dict:
        handle = self.next_handle
        self.next_handle += 1
        profile = {
            "handle": handle, "name": name, "predefined": predefined,
            "applications": [application(path)],
            "settings": [] if value is None else [setting(value)],
        }
        self.profiles[handle] = profile
        return profile

    def snapshot(self) -> dict:
        return copy.deepcopy(self.profiles)

    def writes(self) -> list[tuple]:
        return [op for op in self.operations if op[0] in {"create", "set", "delete", "save"}]


class FakeSession:
    def __init__(self, backend: FakeDRS):
        self.backend = backend
        self.profiles = backend.snapshot()

    @staticmethod
    def view(profile: dict) -> dict:
        result = copy.deepcopy(profile)
        result["num_apps"] = len(result["applications"])
        result["num_settings"] = len(result["settings"])
        result["override"] = next((copy.deepcopy(item) for item in result["settings"]
                                   if item["id"] == VRR_ID), None)
        return result

    def find_application(self, executable: str) -> dict | None:
        self.backend.operations.append(("find_application", executable))
        for profile in self.profiles.values():
            if any(canonical_path(app["path"]) == canonical_path(executable)
                   for app in profile["applications"]):
                return self.view(profile)
        return None

    def find_profile(self, name: str) -> dict | None:
        self.backend.operations.append(("find_profile", name))
        return next((self.view(profile) for profile in self.profiles.values()
                     if profile["name"] == name), None)

    def create_profile(self, name: str, executable: str) -> dict:
        handle = self.backend.next_handle
        self.backend.next_handle += 1
        profile = {
            "handle": handle, "name": name, "predefined": False,
            "applications": [application(executable)], "settings": [],
        }
        self.profiles[handle] = profile
        self.backend.operations.append(("create", name, executable))
        return self.view(profile)

    def set_force_off(self, profile: dict) -> None:
        target = self.profiles[profile["handle"]]
        target["settings"] = [item for item in target["settings"] if item["id"] != VRR_ID]
        target["settings"].append(setting())
        self.backend.operations.append(("set", target["name"], VRR_ID, 1))

    def delete_profile(self, profile: dict) -> None:
        target = self.profiles.pop(profile["handle"])
        self.backend.operations.append(("delete", target["name"]))

    def save(self) -> None:
        self.backend.operations.append(("save",))
        mode = self.backend.save_modes.pop(0) if self.backend.save_modes else "ok"
        if mode == "fail_before":
            raise nvidia_compat.NvApiError("SaveSettings", -1)
        if mode == "foreign_app_then_fail":
            next(iter(self.profiles.values()))["applications"].append(application("C:/other.exe"))
        if mode == "foreign_setting_then_fail":
            next(iter(self.profiles.values()))["settings"].append(setting(3, setting_id=0x12345678))
        self.backend.profiles = copy.deepcopy(self.profiles)
        if mode != "ok":
            raise nvidia_compat.NvApiError("SaveSettings", -1)


class NvidiaCompatibilityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.executable = self.root / "Program mappa" / "GPTTranslator.exe"
        self.executable.parent.mkdir()
        self.executable.write_bytes(b"MZ offline test fixture")
        self.state_dir = self.root / "driver-state"
        self.backend = FakeDRS()

    def configure(self, *, enabled: bool = True, executable: Path | None = None) -> dict:
        return nvidia_compat.configure_nvidia_compatibility(
            executable or self.executable, enabled=enabled,
            state_dir=self.state_dir, session_factory=self.backend.session,
        )

    def own_profile(self) -> dict:
        self.assertEqual(len(self.backend.profiles), 1)
        return next(iter(self.backend.profiles.values()))

    def seed_legacy_profile(self, executable: Path | None = None) -> tuple[dict, Path]:
        executable = executable or self.executable
        self.assertEqual(self.configure(executable=executable)["status"], "applied")
        profile = next(item for item in self.backend.profiles.values()
                       if canonical_path(item["applications"][0]["path"]) == canonical_path(executable))
        suffix = nvidia_compat.profile_name_for(executable).removeprefix(nvidia_compat.PROFILE_PREFIX)
        profile["name"] = nvidia_compat.LEGACY_PROFILE_PREFIX + suffix
        profile["applications"][0]["friendly"] = nvidia_compat.LEGACY_FRIENDLY_NAME
        state_path = self.state_dir / (suffix + ".json")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update(created_by=nvidia_compat.LEGACY_CREATOR, profile_name=profile["name"])
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.backend.operations.clear()
        return profile, state_path

    def test_legacy_owned_profile_is_recreated_with_new_profile_and_friendly_names(self):
        _legacy, state_path = self.seed_legacy_profile()
        result = self.configure()
        self.assertTrue(result["verified"]); self.assertTrue(result["changed"])
        self.assertEqual(result["legacy_profiles_migrated"], 1)
        profile = self.own_profile()
        self.assertEqual(profile["name"], nvidia_compat.profile_name_for(self.executable))
        self.assertEqual(profile["applications"], [application(self.executable.resolve())])
        self.assertEqual(profile["settings"], [setting()])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["created_by"], nvidia_compat.CREATOR)
        self.assertEqual(state["profile_name"], profile["name"])
        self.assertEqual([op[0] for op in self.backend.writes()], ["delete", "create", "set", "save"])
        self.backend.operations.clear()
        self.assertEqual(self.configure()["status"], "already_applied")
        self.assertEqual(self.backend.writes(), [])

    def test_old_executable_owned_profile_is_rebranded_before_new_executable_is_configured(self):
        old_executable = self.executable.with_name("Gamer Translator.exe")
        old_executable.write_bytes(b"MZ legacy fixture")
        self.seed_legacy_profile(old_executable)
        result = self.configure()
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["legacy_profiles_migrated"], 1)
        self.assertEqual(len(self.backend.profiles), 2)
        for profile in self.backend.profiles.values():
            self.assertTrue(profile["name"].startswith(nvidia_compat.PROFILE_PREFIX))
            self.assertEqual(profile["applications"][0]["friendly"], "GPTTranslator")

    def test_legacy_manual_or_modified_profile_is_never_migrated(self):
        for change in ("no_journal", "friendly", "extra_application", "extra_setting", "creator"):
            with self.subTest(change=change):
                self.backend = FakeDRS()
                self.state_dir = self.root / change
                profile, state_path = self.seed_legacy_profile()
                if change == "no_journal": state_path.unlink()
                elif change == "friendly": profile["applications"][0]["friendly"] = "Személyes név"
                elif change == "extra_application": profile["applications"].append(application(self.root / "other.exe"))
                elif change == "extra_setting": profile["settings"].append(setting(3, setting_id=0x12345678))
                else:
                    state = json.loads(state_path.read_text(encoding="utf-8")); state["created_by"] = "someone_else"
                    state_path.write_text(json.dumps(state), encoding="utf-8")
                before = self.backend.snapshot()
                self.configure()
                self.assertEqual(self.backend.snapshot(), before)
                self.assertEqual(self.backend.writes(), [])

    def test_legacy_profile_migration_never_overwrites_existing_new_name(self):
        self.seed_legacy_profile()
        self.backend.add_profile(self.root / "personal.exe", value=2, name=nvidia_compat.profile_name_for(self.executable))
        before = self.backend.snapshot()
        result = self.configure()
        self.assertEqual(result["legacy_profiles_skipped"], 1)
        self.assertEqual(self.backend.snapshot(), before); self.assertEqual(self.backend.writes(), [])

    def test_disabled_legacy_fix_removes_only_the_owned_profile_without_creating_new_one(self):
        self.seed_legacy_profile()
        result = self.configure(enabled=False)
        self.assertEqual(result["status"], "disabled"); self.assertTrue(result["changed"])
        self.assertEqual(self.backend.profiles, {})
        self.assertEqual([op[0] for op in self.backend.writes()], ["delete", "save"])

    def test_legacy_migration_save_failure_before_apply_is_retryable(self):
        _profile, state_path = self.seed_legacy_profile()
        self.backend.save_modes = ["fail_before"]
        self.assertEqual(self.configure()["status"], "failed")
        self.assertTrue(self.own_profile()["name"].startswith(nvidia_compat.LEGACY_PROFILE_PREFIX))
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["created_by"], nvidia_compat.LEGACY_CREATOR)
        self.assertTrue(state["brand_migration"]["target_absent"])
        self.assertTrue(self.configure()["verified"])
        self.assertTrue(self.own_profile()["name"].startswith(nvidia_compat.PROFILE_PREFIX))

    def test_legacy_migration_save_failure_after_apply_is_verified_and_recovered(self):
        _profile, state_path = self.seed_legacy_profile()
        self.backend.save_modes = ["fail_after"]
        result = self.configure()
        self.assertTrue(result["verified"]); self.assertEqual(result["legacy_profiles_migrated"], 1)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["created_by"], nvidia_compat.CREATOR)
        self.assertEqual(state["recovered_save_error"], -1)

    def test_legacy_migration_interruption_after_driver_save_recovers_without_second_write(self):
        _profile, state_path = self.seed_legacy_profile()
        real_persist = nvidia_compat._persist
        def interrupted(path, state, **kwargs):
            if state.get("created_by") == nvidia_compat.CREATOR and state.get("migrated_from_profile_name"):
                raise OSError("Mesterséges journallezárási hiba")
            return real_persist(path, state, **kwargs)
        with patch.object(nvidia_compat, "_persist", side_effect=interrupted):
            self.assertEqual(self.configure()["status"], "failed")
        self.assertTrue(self.own_profile()["name"].startswith(nvidia_compat.PROFILE_PREFIX))
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))["created_by"], nvidia_compat.LEGACY_CREATOR)
        self.backend.operations.clear()
        result = self.configure()
        self.assertTrue(result["verified"]); self.assertEqual(result["legacy_profiles_migrated"], 1)
        self.assertEqual(self.backend.writes(), [])

    def test_new_profile_contains_only_full_exe_path_and_vrr_force_off(self):
        with patch("ctypes.WinDLL", side_effect=AssertionError("Valódi driver betöltése"), create=True), \
                patch("ctypes.CDLL", side_effect=AssertionError("Valódi driver betöltése")):
            self.assertEqual(self.configure()["status"], "applied")
        profile = self.own_profile()
        self.assertFalse(profile["predefined"])
        self.assertEqual(profile["applications"], [application(self.executable.resolve())])
        self.assertEqual(profile["settings"], [setting()])
        self.assertGreaterEqual(self.backend.sessions, 2)
        self.assertTrue(list(self.state_dir.glob("*.json")))
        self.assertEqual([op[0] for op in self.backend.writes()], ["create", "set", "save"])

    def test_repeated_enable_is_idempotent_without_save(self):
        self.assertEqual(self.configure()["status"], "applied")
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure()["status"], "already_applied")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_existing_personal_force_off_profile_is_preserved_without_ownership(self):
        self.backend.add_profile(self.executable, value=1)
        before = self.backend.snapshot()
        self.assertEqual(self.configure()["status"], "already_configured")
        self.assertEqual(self.configure(enabled=False)["status"], "disabled")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_existing_personal_profile_with_other_value_is_never_overridden(self):
        for value in (None, 0, 2):
            with self.subTest(value=value):
                self.backend = FakeDRS()
                self.backend.add_profile(self.executable, value=value)
                before = self.backend.snapshot()
                self.assertEqual(self.configure()["status"], "existing_profile")
                self.assertEqual(self.backend.snapshot(), before)
                self.assertEqual(self.backend.writes(), [])

    def test_predefined_profile_is_preserved(self):
        self.backend.add_profile(self.executable, value=2, predefined=True)
        before = self.backend.snapshot()
        self.assertEqual(self.configure()["status"], "existing_profile")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_disable_deletes_only_verified_owned_singleton_profile(self):
        self.assertEqual(self.configure()["status"], "applied")
        other_exe = self.root / "Személyes.exe"
        other = self.backend.add_profile(other_exe, value=2)
        own_handle = next(key for key in self.backend.profiles if key != other["handle"])
        other_before = copy.deepcopy(other)
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "restored")
        self.assertNotIn(own_handle, self.backend.profiles)
        self.assertEqual(self.backend.profiles[other["handle"]], other_before)
        self.assertEqual([op[0] for op in self.backend.writes()], ["delete", "save"])
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "disabled")
        self.assertEqual(self.backend.writes(), [])

    def test_disable_without_prior_application_never_creates_a_profile(self):
        self.assertEqual(self.configure(enabled=False)["status"], "disabled")
        self.assertEqual(self.backend.profiles, {})
        self.assertEqual(self.backend.writes(), [])

    def test_added_application_blocks_owned_profile_deletion(self):
        self.assertEqual(self.configure()["status"], "applied")
        profile = self.own_profile()
        profile["applications"].append(application(self.root / "Másik alkalmazás.exe"))
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "ownership_unproven")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_added_personal_setting_blocks_owned_profile_deletion(self):
        self.assertEqual(self.configure()["status"], "applied")
        self.own_profile()["settings"].append(setting(7, setting_id=0x12345678))
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "ownership_unproven")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_changed_personal_vrr_value_is_preserved_when_disabling(self):
        self.assertEqual(self.configure()["status"], "applied")
        self.own_profile()["settings"][0]["value"] = 2
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "ownership_unproven")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_changed_personal_vrr_value_is_preserved_when_enabling_again(self):
        self.assertEqual(self.configure()["status"], "applied")
        self.own_profile()["settings"][0]["value"] = 2
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure()["status"], "ownership_unproven")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_save_failure_before_persistence_returns_failure_and_can_retry(self):
        self.backend.save_modes = ["fail_before"]
        result = self.configure()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(self.backend.profiles, {})
        self.assertGreaterEqual(self.backend.sessions, 2)
        self.assertEqual(self.configure()["status"], "applied")
        self.assertEqual(self.own_profile()["settings"], [setting()])

    def test_uncertain_save_result_is_reconciled_from_a_fresh_session(self):
        self.backend.save_modes = ["fail_after"]
        result = self.configure()
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["error_code"], -1)
        self.assertGreaterEqual(self.backend.sessions, 2)
        self.assertEqual(self.own_profile()["settings"], [setting()])
        self.backend.operations.clear()
        self.assertEqual(self.configure()["status"], "already_applied")
        self.assertEqual(self.backend.writes(), [])

    def test_uncertain_delete_result_is_reconciled_from_a_fresh_session(self):
        self.assertEqual(self.configure()["status"], "applied")
        self.backend.save_modes = ["fail_after"]
        result = self.configure(enabled=False)
        self.assertEqual(result["status"], "restored")
        self.assertEqual(result["error_code"], -1)
        self.assertEqual(self.backend.profiles, {})

    def test_failed_delete_before_persistence_preserves_owner_and_can_retry(self):
        self.assertEqual(self.configure()["status"], "applied")
        before = self.backend.snapshot()
        self.backend.save_modes = ["fail_before"]
        self.assertEqual(self.configure(enabled=False)["status"], "failed")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.configure(enabled=False)["status"], "restored")

    def test_uncertain_write_does_not_rollback_profile_with_foreign_additions(self):
        for mode in ("foreign_app_then_fail", "foreign_setting_then_fail"):
            with self.subTest(mode=mode):
                self.backend = FakeDRS()
                self.backend.save_modes = [mode]
                result = self.configure()
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(self.backend.profiles), 1)
                self.assertNotIn("delete", [op[0] for op in self.backend.writes()])
                before = self.backend.snapshot()
                self.backend.operations.clear()
                self.assertEqual(self.configure(enabled=False)["status"], "ownership_unproven")
                self.assertEqual(self.backend.snapshot(), before)
                self.assertEqual(self.backend.writes(), [])

    def test_each_full_path_has_distinct_ownership_and_never_matches_by_basename(self):
        other_exe = self.root / "Új kiadás" / self.executable.name
        other_exe.parent.mkdir()
        other_exe.write_bytes(b"MZ second offline fixture")
        self.assertEqual(self.configure()["status"], "applied")
        first_before = self.backend.snapshot()
        self.assertEqual(self.configure(executable=other_exe)["status"], "applied")
        self.assertEqual(len(self.backend.profiles), 2)
        self.assertEqual(len({item["name"] for item in self.backend.profiles.values()}), 2)
        self.assertEqual(len(list(self.state_dir.glob("*.json"))), 2)
        self.assertEqual(self.configure(enabled=False, executable=other_exe)["status"], "restored")
        self.assertEqual(self.backend.snapshot(), first_before)

    def test_corrupt_state_cannot_authorize_profile_deletion(self):
        self.assertEqual(self.configure()["status"], "applied")
        state_files = list(self.state_dir.glob("*.json"))
        self.assertEqual(len(state_files), 1)
        state_files[0].write_text("{broken", encoding="utf-8")
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "ownership_unproven")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_missing_state_cannot_authorize_profile_deletion_or_reacquisition(self):
        self.assertEqual(self.configure()["status"], "applied")
        for state_file in self.state_dir.glob("*.json"):
            state_file.unlink()
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "ownership_unproven")
        self.assertEqual(self.configure()["status"], "ownership_unproven")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_backend_failure_is_returned_without_leaking_exception_content(self):
        @contextmanager
        def failing_session():
            raise RuntimeError("private-path and private-user")
            yield

        result = nvidia_compat.configure_nvidia_compatibility(
            self.executable, state_dir=self.state_dir, session_factory=failing_session,
        )
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(self.backend.writes(), [])

    def test_unsupported_nvidia_backends_return_without_mutation(self):
        for status in (-2, -3, -6, -104):
            with self.subTest(status=status):
                @contextmanager
                def unavailable_session():
                    raise nvidia_compat.NvApiError("Initialize", status)
                    yield

                result = nvidia_compat.configure_nvidia_compatibility(
                    self.executable, state_dir=self.state_dir, session_factory=unavailable_session,
                )
                self.assertEqual(result["status"], "unsupported")
                self.assertEqual(self.backend.writes(), [])

    def test_driver_access_denial_is_nonfatal_and_never_retries_as_administrator(self):
        calls = []

        @contextmanager
        def denied_session():
            calls.append("session")
            raise nvidia_compat.NvApiError("LoadSettings", -175)
            yield

        result = nvidia_compat.configure_nvidia_compatibility(
            self.executable, state_dir=self.state_dir, session_factory=denied_session,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(calls, ["session"])
        self.assertEqual(self.backend.writes(), [])

    def test_baseline_storage_failure_occurs_before_any_driver_mutation(self):
        blocked_dir = self.root / "not-a-directory"
        blocked_dir.write_text("offline fixture", encoding="utf-8")
        result = nvidia_compat.configure_nvidia_compatibility(
            self.executable, state_dir=blocked_dir, session_factory=self.backend.session,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(self.backend.profiles, {})
        self.assertEqual(self.backend.writes(), [])

    def test_mismatched_journal_application_does_not_grant_ownership(self):
        self.assertEqual(self.configure()["status"], "applied")
        state_file = next(self.state_dir.glob("*.json"))
        saved = json.loads(state_file.read_text(encoding="utf-8"))
        saved["application"] = str(self.root / "másik.exe")
        state_file.write_text(json.dumps(saved), encoding="utf-8")
        before = self.backend.snapshot()
        self.backend.operations.clear()
        self.assertEqual(self.configure(enabled=False)["status"], "ownership_unproven")
        self.assertEqual(self.backend.snapshot(), before)
        self.assertEqual(self.backend.writes(), [])

    def test_source_run_skips_driver_loading_and_state_creation(self):
        with patch.object(nvidia_compat.sys, "frozen", False, create=True), \
                patch("ctypes.WinDLL", side_effect=AssertionError("Valódi driver betöltése"), create=True), \
                patch("ctypes.CDLL", side_effect=AssertionError("Valódi driver betöltése")):
            result = nvidia_compat.configure_nvidia_compatibility(
                self.executable, state_dir=self.state_dir,
            )
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "source_run")
        self.assertFalse(self.state_dir.exists())

    def test_unsupported_platform_skips_driver_loading_and_state_creation(self):
        with patch.object(nvidia_compat.sys, "frozen", True, create=True), \
                patch.object(nvidia_compat.sys, "platform", "linux"), \
                patch("ctypes.WinDLL", side_effect=AssertionError("Valódi driver betöltése"), create=True), \
                patch("ctypes.CDLL", side_effect=AssertionError("Valódi driver betöltése")):
            result = nvidia_compat.configure_nvidia_compatibility(
                self.executable, state_dir=self.state_dir,
            )
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["reason"], "platform")
        self.assertFalse(self.state_dir.exists())


class NvidiaSessionLifecycleTests(unittest.TestCase):
    def test_session_destroys_handle_before_unload_and_does_not_unload_twice(self):
        calls = []
        session = nvidia_compat.NvApiSession()
        session.handle = ctypes.c_void_p(17)
        session.initialized = True
        session.functions = {
            "DestroySession": lambda handle: calls.append(("destroy", handle.value)) or 0,
            "Unload": lambda: calls.append(("unload",)) or 0,
        }
        session.close()
        session.close()
        self.assertEqual(calls, [("destroy", 17), ("unload",)])
        self.assertIsNone(session.handle.value)
        self.assertFalse(session.initialized)

    def test_cleanup_failure_status_never_masks_original_nvapi_result(self):
        calls = []
        session = nvidia_compat.NvApiSession()
        session.handle = ctypes.c_void_p(19)
        session.initialized = True
        session.functions = {
            "DestroySession": lambda handle: calls.append(("destroy", handle.value)) or -1,
            "Unload": lambda: calls.append(("unload",)) or -1,
        }
        session.close()
        self.assertEqual(calls, [("destroy", 19), ("unload",)])
        self.assertIsNone(session.handle.value)
        self.assertFalse(session.initialized)


if __name__ == "__main__":
    unittest.main()
