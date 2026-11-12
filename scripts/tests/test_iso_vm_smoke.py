"""FR-010: a VM screenshot must show the installer, not only its GRUB menu."""

import importlib.util
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
