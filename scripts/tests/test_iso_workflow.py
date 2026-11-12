"""Guard the ISO CI authority boundary and installation guide."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/iso.yml"


class IsoWorkflowTests(unittest.TestCase):
    def test_real_builds_are_gated_for_both_variants(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("variant: [forjaos, forjaos-nvidia-open]", source)
        self.assertIn(".github/scripts/build-iso.sh", source)
        self.assertIn("scripts/verify-iso.py create", source)
        self.assertIn("scripts/verify-iso.py check", source)
        self.assertIn("cosign verify-blob", source)
        self.assertIn("--bundle", source)
        self.assertIn("actions/upload-artifact@", source)
        self.assertIn("'image/build_files/installer/**'", source)
        self.assertIn("'brand/palette.json'", source)
        self.assertIn("'brand/logo/**'", source)
        self.assertIn("'brand/fonts/**'", source)
        self.assertIn("THIRD_PARTY_LICENSES.md", source)
        self.assertIn("-grub.cfg", source)

    def test_pr_job_has_no_release_authority(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        build_section = source.split("\n  release:\n", 1)[0]
        self.assertIn("pull_request:", source)
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", build_section)
        self.assertIn("contents: read", build_section)
        self.assertNotIn("contents: write", build_section)
        self.assertNotIn("gh release create", build_section)
        self.assertNotIn("gh release upload", build_section)
        self.assertNotIn("delete:packages", build_section)

    def test_release_requires_main_and_creates_verified_draft(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("release_tag:", source)
        self.assertIn('IMAGE_CHANNEL', source)
        release_section = source.split("\n  release:\n", 1)[1]
        for required in (
            "github.ref == 'refs/heads/main'", "contents: write",
            "actions/download-artifact@", "gh release create", "--draft",
            "gh release download", "scripts/verify-iso.py check",
            "cosign verify-blob", "v[0-9]+", "SHA256SUMS",
        ):
            with self.subTest(required=required):
                self.assertIn(required, release_section)

    def test_candidate_is_draft_from_f1_branch_and_uses_testing_payload(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("candidate_tag:", source)
        self.assertIn("Validate release request", source)
        self.assertIn("release and candidate tags are mutually exclusive", source)
        self.assertIn("candidate requires the F1-002 branch", source)
        self.assertIn("final release requires main", source)
        self.assertIn("inputs.release_tag != '' && 'stable' || 'testing'", source)
        release_section = source.split("\n  release:\n", 1)[1]
        self.assertIn("github.ref == 'refs/heads/feat/F1-002-iso-anaconda'", release_section)
        self.assertIn("inputs.candidate_tag != ''", release_section)
        self.assertIn("v[0-9]+\\.[0-9]+\\.[0-9]+-rc\\.[0-9]+", release_section)
        self.assertIn("--prerelease", release_section)
        self.assertIn("--draft", release_section)
        self.assertIn("gh release download", release_section)
        self.assertIn("cosign verify-blob", release_section)

    def test_vm_boot_proves_installer_before_release(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("'scripts/tests/test_iso_vm_smoke.py'", source)
        self.assertIn("'.github/scripts/smoke-iso-vm.py'", source)
        self.assertIn("\n  boot:\n", source)
        boot_section = source.split("\n  boot:\n", 1)[1].split("\n  release:\n", 1)[0]
        self.assertIn("needs: build", boot_section)
        self.assertIn("variant: [forjaos, forjaos-nvidia-open]", boot_section)
        self.assertIn("smoke-iso-vm.py", boot_section)
        self.assertIn("qemu-system-x86", boot_section)
        self.assertIn("tesseract-ocr", boot_section)
        self.assertIn("upload-artifact@", boot_section)
        release_section = source.split("\n  release:\n", 1)[1]
        self.assertIn("needs: [build, boot]", release_section)

if __name__ == "__main__":
    unittest.main()
