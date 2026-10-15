"""NVIDIA-indulás és egyszeri újraindítás: driver és grafikus ablak nélkül."""
from __future__ import annotations

import builtins
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import main
from gpttranslator import nvidia_compat
from gpttranslator.settings_store import AppSettings


class NvidiaStartupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.executable = self.root / "GPTTranslator.exe"
        self.executable.write_bytes(b"MZ isolated startup fixture")
        self.settings = AppSettings()
        self.events = []
        self.compatibility = {"status": "already_applied", "changed": False, "verified": True}
        self.store = Mock()
        self.store.load_settings.return_value = self.settings
        self.application = Mock()
        self.application.exec.return_value = 17
        self.instance = Mock()
        self.instance.ensure_primary_instance.return_value = True
        self.window = Mock()

        def create_application(*_arguments):
            self.events.append("qt")
            return self.application

        def create_window():
            self.events.append("window")
            return self.window

        def configure_driver(*_arguments, **_options):
            self.events.append("driver")
            return dict(self.compatibility)

        def restart(*_arguments, **_options):
            self.events.append("restart")
            return Mock()

        window_module = types.ModuleType("gpttranslator.main_window")
        window_module.MainWindow = Mock(side_effect=create_window)
        self.patches = [
            patch.object(main.sys, "frozen", True, create=True),
            patch.object(main.sys, "executable", str(self.executable)),
            patch.object(main.sys, "argv", [str(self.executable)]),
            patch.dict(os.environ, {}, clear=False),
            patch.object(main, "default_app_data_dir", return_value=self.root),
            patch.object(main, "SettingsStore", return_value=self.store),
            patch.object(main, "configure_webengine_environment",
                         side_effect=lambda *_args, **_kwargs: self.events.append("environment")),
            patch.object(main, "log_event"),
            patch.object(main, "log_exception"),
            patch.object(main, "QApplication", side_effect=create_application),
            patch.object(main, "SingleInstanceController", return_value=self.instance),
            patch.object(main.subprocess, "Popen", side_effect=restart),
            patch.object(nvidia_compat, "configure_nvidia_compatibility", side_effect=configure_driver),
            patch.dict(sys.modules, {"gpttranslator.main_window": window_module}),
        ]
        self.mocks = [patcher.start() for patcher in self.patches]
        for patcher in self.patches:
            self.addCleanup(patcher.stop)
        self.qt_constructor = self.mocks[9]
        self.restart = self.mocks[11]
        self.driver = self.mocks[12]

    def assert_normal_window_started(self):
        self.qt_constructor.assert_called_once_with(main.sys.argv)
        self.instance.ensure_primary_instance.assert_called_once()
        self.instance.activation_requested.connect.assert_called_once_with(self.window.show_from_external_request)
        self.window.show.assert_called_once()
        self.application.exec.assert_called_once()
        self.assertLess(self.events.index("environment"), self.events.index("qt"))

    def test_source_helper_never_imports_or_calls_driver_module(self):
        original_import = builtins.__import__

        def no_driver_import(name, *_args, **_kwargs):
            if name == "gpttranslator.nvidia_compat":
                raise AssertionError("Forrásból nem kérhető driverbeállítás")
            return original_import(name, *_args, **_kwargs)

        with patch.object(main.sys, "frozen", False), patch("builtins.__import__", side_effect=no_driver_import):
            result = main._configure_nvidia_compatibility(self.settings)
        self.assertFalse(result["changed"])
        self.assertFalse(result["verified"])
        self.driver.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [self.executable])

    def test_frozen_helper_delegates_exact_executable_setting_and_state_directory(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                self.driver.reset_mock()
                self.settings.nvidia_mouse_lag_fix_enabled = enabled
                result = main._configure_nvidia_compatibility(self.settings)
                self.assertEqual(result, self.compatibility)
                self.driver.assert_called_once_with(
                    self.executable, enabled=enabled, state_dir=self.root / "nvidia-compat",
                )

    def test_helper_exception_is_nonfatal_and_does_not_return_private_error_text(self):
        self.driver.side_effect = RuntimeError("private username and C:/private/profile")
        result = main._configure_nvidia_compatibility(self.settings)
        self.assertFalse(result["changed"])
        self.assertFalse(result["verified"])
        self.assertNotIn("private", json.dumps(result))
        self.restart.assert_not_called()

    def test_verified_profile_change_restarts_before_qt_with_safe_pyinstaller_environment(self):
        self.compatibility = {"status": "applied", "changed": True, "verified": True}
        main.sys.argv = [str(self.executable), "--nvidia-compat-restarted", "--self-test-duration", "25"]
        os.environ["_PYI_PARENT_PROCESS_LEVEL"] = "1"
        os.environ["_PYI_APPLICATION_HOME_DIR"] = "existing-extraction-directory"
        os.environ["GPTTRANSLATOR_STARTUP_TEST"] = "inherited-value"
        os.environ["PYINSTALLER_RESET_ENVIRONMENT"] = "0"
        self.assertEqual(main._run_normal(), 0)
        self.assertEqual(self.events, ["environment", "driver", "restart"])
        self.qt_constructor.assert_not_called()
        self.window.show.assert_not_called()
        self.restart.assert_called_once()
        arguments, options = self.restart.call_args
        command = arguments[0]
        self.assertEqual(command[0], str(self.executable))
        self.assertEqual(command.count("--nvidia-compat-restarted"), 1)
        self.assertEqual(command[1:-1], ["--self-test-duration", "25"])
        self.assertEqual(options["cwd"], str(self.executable.parent))
        self.assertTrue(options["close_fds"])
        self.assertEqual(options["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        self.assertEqual(options["env"]["_PYI_PARENT_PROCESS_LEVEL"], "1")
        self.assertEqual(options["env"]["_PYI_APPLICATION_HOME_DIR"], "existing-extraction-directory")
        self.assertEqual(options["env"]["GPTTRANSLATOR_STARTUP_TEST"], "inherited-value")
        self.assertNotIn("shell", options)

    def test_already_configured_profile_continues_to_qt_after_driver_check(self):
        self.assertEqual(main._run_normal(), 17)
        self.restart.assert_not_called()
        self.assertLess(self.events.index("driver"), self.events.index("qt"))
        self.assert_normal_window_started()

    def test_unverified_profile_change_never_restarts(self):
        self.compatibility = {"status": "failed", "changed": True, "verified": False}
        self.assertEqual(main._run_normal(), 17)
        self.restart.assert_not_called()
        self.assert_normal_window_started()

    def test_restart_marker_bounds_a_repeated_changed_response_to_one_restart(self):
        self.compatibility = {"status": "applied", "changed": True, "verified": True}
        self.assertEqual(main._run_normal(), 0)
        self.assertEqual(main._run_normal(nvidia_compat_restarted=True), 17)
        self.restart.assert_called_once()
        self.assertEqual(self.driver.call_count, 2)
        self.assert_normal_window_started()

    def test_restart_launch_failure_continues_to_normal_qt_window(self):
        self.compatibility = {"status": "restored", "changed": True, "verified": True}
        self.restart.side_effect = OSError("offline launch failure")
        self.assertEqual(main._run_normal(), 17)
        self.restart.assert_called_once()
        self.assertLess(self.events.index("driver"), self.events.index("qt"))
        self.assert_normal_window_started()

    def test_source_startup_continues_without_driver_call_or_restart(self):
        with patch.object(main.sys, "frozen", False):
            self.assertEqual(main._run_normal(), 17)
        self.driver.assert_not_called()
        self.restart.assert_not_called()
        self.assert_normal_window_started()

    def test_hidden_restart_parser_marker_reaches_normal_startup(self):
        def run_mode(_root, mode, runner):
            self.assertEqual(mode, "normal")
            return runner()

        with patch.object(main.sys, "argv", [str(self.executable), "--nvidia-compat-restarted"]), \
                patch.object(main, "_run_with_diagnostics", side_effect=run_mode), \
                patch.object(main, "_run_normal", return_value=0) as normal:
            self.assertEqual(main.main(), 0)
        normal.assert_called_once_with(nvidia_compat_restarted=True)
        self.driver.assert_not_called()
        self.qt_constructor.assert_not_called()

    def isolated_test_mode(self, arguments: list[str], mode: str):
        module = types.ModuleType("gpttranslator.self_test")
        module.run_self_test = Mock(return_value=0)
        module.run_staging = Mock(return_value=0)
        diagnostic_roots = []

        def run_mode(root, observed_mode, runner):
            self.assertEqual(observed_mode, mode)
            self.assertNotEqual(root, self.root)
            self.assertTrue(root.name.startswith("gpttranslator-test-diagnostics-"))
            diagnostic_roots.append(root)
            return runner()

        with patch.object(main.sys, "argv", [str(self.executable), *arguments, "--nvidia-compat-restarted"]), \
                patch.object(main, "_run_with_diagnostics", side_effect=run_mode), \
                patch.object(main, "_configure_nvidia_compatibility", side_effect=AssertionError("Driver tesztmódban")) as helper, \
                patch.object(main, "default_app_data_dir", side_effect=AssertionError("Normál profil tesztmódban")), \
                patch.object(main, "SettingsStore", side_effect=AssertionError("Normál beállítások tesztmódban")), \
                patch.dict(sys.modules, {"gpttranslator.self_test": module}):
            self.assertEqual(main.main(), 0)
        helper.assert_not_called()
        self.driver.assert_not_called()
        self.restart.assert_not_called()
        self.qt_constructor.assert_not_called()
        self.assertEqual(len(diagnostic_roots), 1)
        self.assertFalse(diagnostic_roots[0].exists())
        self.assertEqual(list(self.root.iterdir()), [self.executable])
        return module

    def test_frozen_self_test_bypasses_driver_normal_profile_and_restart(self):
        report = self.root / "self-test.json"
        module = self.isolated_test_mode(["--self-test-report", str(report), "--self-test-duration", "9"], "self_test")
        module.run_self_test.assert_called_once_with(report, 9, None)
        module.run_staging.assert_not_called()

    def test_frozen_staging_bypasses_driver_normal_profile_and_restart(self):
        module = self.isolated_test_mode(["--staging"], "staging")
        module.run_staging.assert_called_once_with()
        module.run_self_test.assert_not_called()


if __name__ == "__main__":
    unittest.main()
