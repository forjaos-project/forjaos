"""F0-005: verify image RPM license inventory output and failure behavior."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / ".github" / "scripts" / "generate_third_party_licenses.py"
IMAGE_ID = "sha256:" + "a" * 64


class ThirdPartyLicensesTest(unittest.TestCase):
    def run_generator(self, data, output, image_id=IMAGE_ID):
        return subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--variant",
                "forjaos",
                "--image-id",
                image_id,
                "--output",
                str(output),
            ],
            input=data,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_sorted_packages_and_declared_license_files(self):
        data = (
            "P\tzebra\t2-1.fc45\tx86_64\tMIT | BSD-3-Clause\tzebra-2-1.src.rpm\n"
            "F\t/usr/bin/zebra\t\n"
            "F\t/usr/share/licenses/zebra/LICENSE\tl\n"
            "P\talpha\t1-2.fc45\tnoarch\tApache-2.0\talpha-1-2.src.rpm\n"
            "F\t/usr/share/licenses/alpha/COPYING\tdl\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "THIRD_PARTY_LICENSES.md"
            result = self.run_generator(data, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = output.read_text(encoding="utf-8")
            self.assertIn("# Third-party licenses — forjaos", report)
            self.assertIn(IMAGE_ID, report)
            self.assertIn("2 installed RPM packages", report)
            self.assertLess(report.index("| alpha |"), report.index("| zebra |"))
            self.assertIn("MIT \\| BSD-3-Clause", report)
            self.assertIn("/usr/share/licenses/zebra/LICENSE", report)
            self.assertIn("/usr/share/licenses/alpha/COPYING", report)
            self.assertNotIn("/usr/bin/zebra", report)
            self.assertEqual(self.run_generator(data, output).returncode, 0)
            self.assertEqual(report, output.read_text(encoding="utf-8"))

    def test_empty_or_malformed_input_leaves_no_report(self):
        cases = [
            "",
            "F\t/usr/share/licenses/orphan/LICENSE\tl\n",
            "P\tbad\t1-1\tx86_64\t\tbad.src.rpm\n",
            "P\tbad\t1-1\tx86_64\tMIT\n",
            "P\tbad\t1-1\tx86_64\tMIT\tbad.src.rpm\nF\trelative/LICENSE\tl\n",
            "P\tbad\t1-1\tx86_64\tMIT\tbad.src.rpm\n"
            "P\tbad\t1-1\tx86_64\tBSD\tbad.src.rpm\n",
        ]
        for data in cases:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "THIRD_PARTY_LICENSES.md"
                result = self.run_generator(data, output)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_bare_podman_image_id_is_normalized_but_invalid_id_fails(self):
        data = "P\tfixture\t1-1\tx86_64\tMIT\tfixture.src.rpm\n"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "THIRD_PARTY_LICENSES.md"
            result = self.run_generator(data, output, image_id="a" * 64)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(IMAGE_ID, output.read_text(encoding="utf-8"))
            output.unlink()
            result = self.run_generator(data, output, image_id="a" * 63)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
