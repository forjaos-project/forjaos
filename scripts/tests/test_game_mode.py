"""Game Mode state and inherited gaming contract tests (run at final local build)."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image/game/game_mode.py"
SPEC = importlib.util.spec_from_file_location("game_mode", SCRIPT)
GAME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GAME)


class GameModeTests(unittest.TestCase):
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
