"""Az átnevezés profilmegőrzése elkülönített, helyi fixture-ökön."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication

import main
from gpttranslator import settings_store as module
from gpttranslator.settings_store import LEGACY_DATA_DIRECTORY_NAMES, ProfileMigrationError, SettingsStore


class BrandMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / LEGACY_DATA_DIRECTORY_NAMES["local"]
        self.target = self.root / "GPTTranslator"

    def fixture(self):
        document = {
            "settings": {"promptTemplate": "Saját fordítási szabály.", "monitoringEnabled": False},
            "lastTranslatedText": "Korábbi magyar fordítás.",
            "lastRunStatus": {"at": "2026-10-15T10:00:00+00:00", "message": "Kész."},
        }
        files = {
            "settings.json": json.dumps(document, ensure_ascii=False).encode("utf-8"),
            "browser/storage/Cookies": b"helyi fixture cookie adatbazis",
            "browser/storage/Local Storage/leveldb/000001.log": b"helyi munkamenet fixture",
            "browser/cache/Cache/fixture": b"gyorsitotar",
            "ocr/model.onnx": b"helyi OCR modell",
            "nvidia-compat/state.json": b'{"fixture":true}',
            "logs/history.jsonl": b'{"event":"fixture"}\n',
        }
        for name, content in files.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return files

    def guard(self):
        guard = main.ProfileMigrationGuard(self.target, (self.source,))
        self.addCleanup(guard.release)
        return guard

    def lock(self, path):
        lock = QLockFile(str(path))
        lock.setStaleLockTime(0)
        self.assertTrue(lock.tryLock(0))
        self.addCleanup(lock.unlock)
        return lock

    def test_guarded_migration_preserves_settings_translation_browser_models_and_original(self):
        files = self.fixture()
        source_hashes = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        guard = self.guard()
        guard.prepare()
        for name, expected in source_hashes.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((self.target / name).read_bytes()).hexdigest(), expected)
                self.assertEqual(hashlib.sha256((self.source / name).read_bytes()).hexdigest(), expected)
        self.assertFalse((self.target / "instance.lock").exists())
        store = SettingsStore(self.target)
        self.assertEqual(store.load_settings().prompt_template, "Saját fordítási szabály.")
        self.assertFalse(store.load_settings().monitoring_enabled)
        self.assertEqual(store.load_last_translated_text(), "Korábbi magyar fordítás.")
        self.assertEqual(store.load_last_run_status().message, "Kész.")
        self.assertEqual(store.browser_dir / "storage", self.target / "browser" / "storage")

    def test_running_legacy_profile_is_never_copied_or_activated(self):
        self.fixture()
        self.lock(self.source / "instance.lock")
        with patch.object(main, "SingleInstanceController") as ipc:
            with self.assertRaisesRegex(ProfileMigrationError, "korábbi alkalmazás még fut"):
                self.guard().prepare()
        ipc.assert_not_called()
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.root.glob(".GPTTranslator-migration-*")), [])

    def test_legacy_lock_is_held_for_new_process_lifetime_and_released_afterwards(self):
        self.fixture()
        guard = self.guard()
        guard.prepare()
        competing = QLockFile(str(self.source / "instance.lock"))
        competing.setStaleLockTime(0)
        self.assertFalse(competing.tryLock(0))
        guard.release()
        self.assertTrue(competing.tryLock(0))
        competing.unlock()

    def test_existing_new_profile_is_preserved_without_merging_legacy_files(self):
        self.fixture()
        self.target.mkdir()
        saved = b'{"lastTranslatedText":"uj profil"}'
        (self.target / "settings.json").write_bytes(saved)
        self.guard().prepare()
        self.assertEqual((self.target / "settings.json").read_bytes(), saved)
        self.assertFalse((self.target / "ocr").exists())
        self.assertTrue((self.source / "browser/storage/Cookies").exists())

    def test_diagnostics_only_partial_target_cannot_silently_start_an_empty_profile(self):
        self.fixture()
        (self.target / "logs").mkdir(parents=True)
        (self.target / "logs/failure.jsonl").write_bytes(b"indulasi hiba fixture")
        with self.assertRaisesRegex(ProfileMigrationError, "nem indít üres profilt"):
            self.guard().prepare()
        self.assertFalse((self.target / "browser").exists())
        self.assertEqual((self.target / "logs/failure.jsonl").read_bytes(), b"indulasi hiba fixture")
        self.assertTrue((self.source / "browser/storage/Cookies").exists())

    def test_running_new_profile_can_reach_its_own_single_instance_ipc(self):
        self.fixture()
        self.target.mkdir()
        self.lock(self.target / "instance.lock")
        self.lock(self.source / "instance.lock")  # A futó új példány ezt is tarthatja.
        guard = self.guard()
        with patch.object(main, "migrate_legacy_app_data") as migrate:
            guard.prepare()
        migrate.assert_not_called()
        self.assertEqual(guard.legacy_locks, [])
        # A normál startup ezután csak az új profilhash új nevű IPC-jét érheti el.
        controller = main.SingleInstanceController("GPTTranslatorMigrationTest", self.target)
        with patch.object(controller, "_notify_existing_instance", return_value=True) as notify:
            self.assertFalse(controller.ensure_primary_instance())
        notify.assert_called_once()

    def test_incomplete_copy_is_not_published_and_source_is_preserved(self):
        files = self.fixture()
        guard = self.guard()

        def broken_copy(source, target, **_kwargs):
            (Path(target) / "partial").write_bytes(b"felbemaradt")
            raise OSError("Szimulált lemezhiba")

        with patch.object(module.shutil, "copytree", side_effect=broken_copy):
            with self.assertRaises(ProfileMigrationError):
                guard.prepare()
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.root.glob(".GPTTranslator-migration-*")), [])
        for name, expected in files.items():
            self.assertEqual((self.source / name).read_bytes(), expected)
        self.assertEqual(guard.legacy_locks, [])
        # A hiba után új indítás folytathatja az eredeti, ép profilból.
        guard.prepare()
        self.assertTrue((self.target / "browser/storage/Cookies").exists())

    def test_failed_publication_keeps_original_and_leaves_no_partial_new_profile(self):
        files = self.fixture()
        with patch.object(module.Path, "rename", side_effect=OSError("Szimulált átnevezési hiba")):
            with self.assertRaises(ProfileMigrationError):
                self.guard().prepare()
        self.assertFalse(self.target.exists())
        self.assertEqual((self.source / "settings.json").read_bytes(), files["settings.json"])
        self.assertEqual(list(self.root.glob(".GPTTranslator-migration-*")), [])

    def test_new_target_content_appearing_during_copy_is_not_overwritten(self):
        self.fixture()
        copytree = shutil.copytree

        def raced_copy(source, target, *args, **kwargs):
            result = copytree(source, target, *args, **kwargs)
            if Path(source) == self.source:
                self.target.mkdir()
                (self.target / "unexpected.txt").write_text("Megőrzendő.", encoding="utf-8")
            return result

        with patch.object(module.shutil, "copytree", side_effect=raced_copy):
            with self.assertRaises(ProfileMigrationError):
                self.guard().prepare()
        self.assertEqual((self.target / "unexpected.txt").read_text(encoding="utf-8"), "Megőrzendő.")
        self.assertFalse((self.target / "browser").exists())

    def test_simultaneous_migrations_do_not_touch_the_target(self):
        self.fixture()
        self.lock(self.root / ".GPTTranslator.migration.lock")
        with self.assertRaisesRegex(ProfileMigrationError, "már folyamatban"):
            self.guard().prepare()
        self.assertFalse(self.target.exists())

    def test_local_and_home_default_paths_find_only_their_compatibility_sources(self):
        home = self.root / "home"
        home.mkdir()
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)}), patch.object(module.Path, "home", return_value=home):
            self.assertEqual(module.default_app_data_dir(), self.target)
            self.assertEqual(module.legacy_app_data_dirs(self.target), (
                self.source.resolve(), (home / LEGACY_DATA_DIRECTORY_NAMES["home"]).resolve(),
            ))
            self.assertEqual(module.legacy_app_data_dirs(self.root / "offline-fixture"), ())
        with patch.dict(os.environ, {"LOCALAPPDATA": ""}), patch.object(module.Path, "home", return_value=home):
            target = home / ".gpttranslator"
            self.assertEqual(module.default_app_data_dir(), target)
            self.assertEqual(module.legacy_app_data_dirs(target), ((home / LEGACY_DATA_DIRECTORY_NAMES["home"]).resolve(),))

    def test_home_fallback_profile_is_migrated_without_a_local_app_data_directory(self):
        self.source = self.root / LEGACY_DATA_DIRECTORY_NAMES["home"]
        self.target = self.root / ".gpttranslator"
        self.fixture()
        with patch.dict(os.environ, {"LOCALAPPDATA": ""}), patch.object(module.Path, "home", return_value=self.root):
            guard = main.ProfileMigrationGuard(module.default_app_data_dir())
            self.addCleanup(guard.release)
            guard.prepare()
        self.assertTrue((self.target / "browser/storage/Cookies").exists())
        self.assertTrue((self.source / "browser/storage/Cookies").exists())

    def test_normal_startup_prepares_migration_before_diagnostics_and_releases_locks(self):
        calls = []
        guard = Mock()
        guard.prepare.side_effect = lambda: calls.append("prepare")
        guard.release.side_effect = lambda: calls.append("release")
        with patch.object(main.sys, "argv", ["main.py"]), \
                patch.object(main, "default_app_data_dir", return_value=self.target), \
                patch.object(main, "ProfileMigrationGuard", return_value=guard), \
                patch.object(main, "_run_with_diagnostics", side_effect=lambda *args: calls.append("diagnostics") or 0):
            self.assertEqual(main.main(), 0)
        self.assertEqual(calls, ["prepare", "diagnostics", "release"])

    def test_blocked_migration_never_starts_diagnostics_settings_or_browser(self):
        guard = Mock()
        guard.prepare.side_effect = ProfileMigrationError("Zárd be a korábbi példányt.")
        with patch.object(main.sys, "argv", ["main.py"]), \
                patch.object(main, "ProfileMigrationGuard", return_value=guard), \
                patch.object(main, "QMessageBox") as message, \
                patch.object(main, "SettingsStore") as settings, \
                patch.object(main, "_run_with_diagnostics") as diagnostics:
            self.assertEqual(main.main(), 1)
        settings.assert_not_called()
        diagnostics.assert_not_called()
        message.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
