"""F1-011: the build must wire approved logo assets into the image helper."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "image/Containerfile").read_text(encoding="utf-8")


class ImageContainerfileTests(unittest.TestCase):
    def test_approved_logo_assets_reach_the_helper(self):
        self.assertIn("COPY brand/logo/png/ /tmp/forjaos-icons/", SOURCE)
        self.assertIn("--icons-dir /tmp/forjaos-icons", SOURCE)
        self.assertIn("--image-name \"${IMAGE_NAME}\"", SOURCE)

    def test_branding_rpm_transaction_precedes_identity_rewrite(self):
        self.assertIn("COPY --from=branding-builder", SOURCE)
        self.assertLess(SOURCE.index("dnf install"), SOURCE.index("configure_image.py \\"))

    def test_firstboot_installs_homebrew_helper_for_user_setup(self):
        self.assertIn(
            "COPY image/firstboot/install_homebrew.py /usr/libexec/forjaos/install_homebrew.py",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
