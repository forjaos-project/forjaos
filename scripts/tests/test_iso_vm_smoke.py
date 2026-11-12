"""FR-010: a VM screenshot must show the installer, not only its GRUB menu."""

import importlib.util
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / ".github/scripts/smoke-iso-vm.py"
SPEC = importlib.util.spec_from_file_location("smoke_iso_vm", SCRIPT)
if SPEC is not None and SPEC.loader is not None:
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
else:
    module = None


class IsoVmSmokeTests(unittest.TestCase):
    def test_screenshot_negotiates_qmp_before_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            monitor = root / "qmp.sock"
            destination = root / "screen.ppm"
            commands = []
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(str(monitor))
                server.listen(1)

                def serve():
                    connection, _ = server.accept()
                    with connection, connection.makefile("rwb") as stream:
                        stream.write(b'{"QMP":{"version":{},"capabilities":[]}}\r\n')
                        stream.flush()
                        for _ in range(2):
                            commands.append(json.loads(stream.readline()))
                            if commands[-1]["execute"] == "screendump":
                                destination.write_bytes(b"P6\n1 1\n255\n\x00\x00\x00")
                            stream.write(b'{"return":{}}\r\n')
                            stream.flush()

                worker = threading.Thread(target=serve, daemon=True)
                worker.start()
                module.screenshot(monitor, destination)
                worker.join(timeout=2)
            self.assertEqual(commands, [
                {"execute": "qmp_capabilities"},
                {"execute": "screendump", "arguments": {"filename": str(destination)}},
            ])

    def test_uses_pflash_with_separate_writable_variables(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code = root / "CODE.fd"
            variables = root / "VARS.fd"
            code.write_bytes(b"code")
            variables.write_bytes(b"vars")
            args = module.firmware_drives(code, variables, root)
            self.assertEqual(args, [
                "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={code}",
                "-drive", f"if=pflash,format=raw,unit=1,file={root / 'OVMF_VARS.fd'}",
            ])
            self.assertEqual((root / "OVMF_VARS.fd").read_bytes(), b"vars")

    def test_uses_software_emulation_without_kvm(self):
        self.assertEqual(module.accelerator(False), "tcg,thread=multi")
        self.assertEqual(module.accelerator(True), "kvm")

    def test_rejects_grub_menu_and_blank_screen(self):
        for text in ("", "Instalar ForjaOS", "GNU GRUB\nInstalar ForjaOS"):
            with self.subTest(text=text):
                self.assertFalse(module.installer_visible(text))

    def test_accepts_installer_screen_with_project_identity(self):
        for text in (
            "Welcome to ForjaOS\nSelect your language",
            "Anaconda\nForjaOS\nInstallation Summary",
            "ForjaOS\nBem-vindo à instalação",
        ):
            with self.subTest(text=text):
                self.assertTrue(module.installer_visible(text))

    def test_rejects_fedora_identity(self):
        self.assertFalse(module.installer_visible("Welcome to Fedora Linux\nInstallation Summary"))


if __name__ == "__main__":
    unittest.main()
