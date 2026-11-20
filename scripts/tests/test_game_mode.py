"""Game Mode state and inherited gaming contract tests (run at final local build)."""

import importlib.util
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image/game/game_mode.py"
SPEC = importlib.util.spec_from_file_location("game_mode", SCRIPT)
GAME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GAME)


class GameModeTests(unittest.TestCase):
    def test_performance_profile_is_restored_only_if_game_mode_still_owns_it(self):
        class ProfileValue(str):
            def __new__(cls, value, variant_level=0):
                del variant_level
                return super().__new__(cls, value)

        class Properties:
            active = "balanced"
            profiles = [{"Profile": "balanced"}, {"Profile": "performance"}]

            def Get(self, _interface, name):
                return self.active if name == "ActiveProfile" else self.profiles

            def Set(self, _interface, name, value):
                if name == "ActiveProfile":
                    self.active = str(value)

        properties = Properties()
        dbus = types.SimpleNamespace(
            SystemBus=lambda: types.SimpleNamespace(get_object=lambda *_args: object()),
            Interface=lambda _proxy, _interface: properties,
            String=ProfileValue,
        )
        with patch.dict("sys.modules", {"dbus": dbus}):
            previous = GAME.set_performance_profile()
            self.assertEqual(previous, "balanced")
            self.assertEqual(properties.active, "performance")
            GAME.restore_power_profile(previous)
            self.assertEqual(properties.active, "balanced")

            previous = GAME.set_performance_profile()
            self.assertEqual(previous, "balanced")
            properties.active = "balanced"  # Respect a user's change during the session.
            GAME.restore_power_profile(previous)
            self.assertEqual(properties.active, "balanced")

    def test_only_owned_steam_or_gamescope_processes_activate_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            for pid, name in (("101", "steam"), ("102", "other"), ("103", "gamescope")):
                path = proc / pid
                path.mkdir()
                (path / "comm").write_text(name + "\n", encoding="utf-8")
            uid = os.stat(proc / "101").st_uid
            self.assertTrue(GAME.gaming_process_running(proc, uid))
            (proc / "101/comm").write_text("steamwebhelper\n", encoding="utf-8")
            self.assertTrue(GAME.gaming_process_running(proc, uid))
            (proc / "103/comm").write_text("unrelated\n", encoding="utf-8")
            self.assertFalse(GAME.gaming_process_running(proc, uid))
            self.assertFalse(GAME.gaming_process_running(proc, uid + 1))

    def test_automatic_start_and_stop_respect_manual_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            with patch.object(GAME, "systemctl") as systemctl:
                GAME.watch_once(runtime, True, False)
                systemctl.assert_called_once_with("start", GAME.TARGET)
                systemctl.reset_mock()
                GAME.watch_once(runtime, False, True)
                systemctl.assert_called_once_with("stop", GAME.TARGET)
                systemctl.reset_mock()
                (runtime / "game-mode-manual").touch()
                GAME.watch_once(runtime, False, True)
                systemctl.assert_not_called()
                (runtime / "game-mode-suppressed").touch()
                GAME.watch_once(runtime, True, False)
                systemctl.assert_not_called()
                GAME.watch_once(runtime, False, False)
                self.assertFalse((runtime / "game-mode-suppressed").exists())

    def test_explicit_off_suppresses_reactivation_until_game_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            (runtime / "game-mode-manual").touch()
            with patch.object(GAME, "gaming_process_running", return_value=True), \
                    patch.object(GAME, "systemctl") as systemctl:
                systemctl.return_value.returncode = 0
                self.assertEqual(GAME.change_mode("off", runtime), 0)
            self.assertFalse((runtime / "game-mode-manual").exists())
            self.assertTrue((runtime / "game-mode-suppressed").exists())

    def test_game_session_pauses_only_a_running_memory_service_and_restores_it(self):
        with patch.object(GAME, "user_service_active", return_value=True), \
                patch.object(GAME, "systemctl") as systemctl:
            systemctl.return_value.returncode = 0
            self.assertTrue(GAME.stop_memory_for_game())
            systemctl.assert_called_once_with("stop", "memd.service")
        with patch.object(GAME, "user_service_active", side_effect=[False]), \
                patch.object(GAME, "systemctl") as systemctl:
            systemctl.return_value.returncode = 0
            GAME.restore_memory_after_game(True)
            systemctl.assert_called_once_with("start", "memd.service")
        with patch.object(GAME, "user_service_active", return_value=False), \
                patch.object(GAME, "systemctl") as systemctl:
            self.assertFalse(GAME.stop_memory_for_game())
            systemctl.assert_not_called()

    def test_game_session_unloads_only_models_reported_as_running(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            ollama = home / ".brew" / "bin" / "ollama"
            ollama.parent.mkdir(parents=True)
            ollama.touch()
            calls = []

            def run(command, **_kwargs):
                calls.append(command)
                if command[-1] == "ps":
                    return GAME.subprocess.CompletedProcess(
                        command, 0,
                        stdout="NAME ID SIZE PROCESSOR UNTIL\nqwen3:8b abc 5 GB 100% GPU 4m\n"
                        "llama3.1:latest def 2 GB 100% GPU 4m\n",
                    )
                return GAME.subprocess.CompletedProcess(command, 0, stdout="stopped\n")

            with patch.object(GAME.Path, "home", return_value=home), \
                    patch.object(GAME.subprocess, "run", side_effect=run):
                GAME.unload_ollama_models()

            self.assertEqual(calls, [
                [str(ollama), "ps"],
                [str(ollama), "stop", "qwen3:8b"],
                [str(ollama), "stop", "llama3.1:latest"],
            ])

    def test_image_installs_target_and_scoped_services(self):
        containerfile = (ROOT / "image/Containerfile").read_text(encoding="utf-8")
        for unit in ("hero-game.target", "forjaos-game-session.service", "forjaos-game-watch.service"):
            self.assertIn(f"COPY image/game/{unit}", containerfile)
        target = (ROOT / "image/game/hero-game.target").read_text(encoding="utf-8")
        session = (ROOT / "image/game/forjaos-game-session.service").read_text(encoding="utf-8")
        watcher = (ROOT / "image/game/forjaos-game-watch.service").read_text(encoding="utf-8")
        self.assertIn("Wants=forjaos-game-session.service", target)
        self.assertIn("PartOf=hero-game.target", session)
        self.assertIn("PartOf=graphical-session.target", watcher)
        self.assertIn("MemoryMax=", session)
        self.assertIn("MemoryMax=", watcher)


if __name__ == "__main__":
    unittest.main()
