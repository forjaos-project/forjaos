#!/usr/bin/env python3
"""Boot an installer ISO in KVM and retain proof that Anaconda opened."""

import argparse
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path


def installer_visible(text: str) -> bool:
    visible = " ".join(text.lower().split())
    if "forjaos" not in visible or any(name in visible for name in ("fedora linux", "bazzite", "bluefin")):
        return False
    return any(mark in visible for mark in (
        "welcome", "installation summary", "select your language", "anaconda",
        "instalação", "idioma",
    ))


def accelerator(kvm_available: bool) -> str:
    return "kvm" if kvm_available else "tcg,thread=multi"


def firmware_drives(code: Path, variables: Path, output: Path) -> list[str]:
    writable_variables = output / "OVMF_VARS.fd"
    shutil.copyfile(variables, writable_variables)
    return [
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={code}",
        "-drive", f"if=pflash,format=raw,unit=1,file={writable_variables}",
    ]


def screenshot(monitor: Path, destination: Path) -> None:
    destination.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(30)
        connection.connect(str(monitor))
        with connection.makefile("rwb") as stream:
            greeting = json.loads(stream.readline())
            if "QMP" not in greeting:
                raise RuntimeError("QEMU did not send a QMP greeting")
            for command in (
                {"execute": "qmp_capabilities"},
                {"execute": "screendump", "arguments": {"filename": str(destination)}},
            ):
                stream.write(json.dumps(command).encode() + b"\r\n")
                stream.flush()
                while True:
                    response = json.loads(stream.readline())
                    if "error" in response:
                        raise RuntimeError(f"QEMU command failed: {response['error']}")
                    if "return" in response:
                        break
    for _ in range(20):
        if destination.is_file() and destination.stat().st_size > 0:
            return
        time.sleep(0.5)
    raise RuntimeError("QEMU did not produce a screenshot")


def boot(iso: Path, output: Path, timeout_seconds: int) -> None:
    if not iso.is_file():
        raise FileNotFoundError(iso)
    firmware = next(((code, variables) for code, variables in (
        (Path("/usr/share/OVMF/OVMF_CODE_4M.fd"), Path("/usr/share/OVMF/OVMF_VARS_4M.fd")),
        (Path("/usr/share/OVMF/OVMF_CODE.fd"), Path("/usr/share/OVMF/OVMF_VARS.fd")),
    ) if code.is_file() and variables.is_file()), None)
    if firmware is None:
        raise FileNotFoundError("OVMF firmware")
    output.mkdir(parents=True, exist_ok=True)
    disk = output / "installer-test.qcow2"
    monitor = output / "qemu-monitor.sock"
    screen = output / "screen.ppm"
    transcript = output / "screen-ocr.txt"
    subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "32G"], check=True)
    command = [
        "qemu-system-x86_64", "-accel", accelerator(os.access("/dev/kvm", os.R_OK | os.W_OK)),
        "-machine", "q35",
        "-m", "4096", "-smp", "2", *firmware_drives(*firmware, output),
        "-boot", "order=d", "-cdrom", str(iso),
        "-drive", f"file={disk},format=qcow2,if=virtio",
        "-netdev", "user,id=net0", "-device", "virtio-net-pci,netdev=net0",
        "-vga", "std", "-display", "none", "-vnc", "127.0.0.1:1",
        "-qmp", f"unix:{monitor},server,nowait",
        "-serial", f"file:{output / 'serial.log'}", "-no-reboot",
    ]
    with (output / "qemu.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + timeout_seconds
            transcript.write_text("", encoding="utf-8")
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"QEMU exited before installer opened: {process.returncode}")
                if monitor.exists():
                    screenshot(monitor, screen)
                    result = subprocess.run(
                        ["tesseract", str(screen), "stdout", "--psm", "11"],
                        capture_output=True, text=True, check=True,
                    )
                    with transcript.open("a", encoding="utf-8") as proof:
                        proof.write(f"\n--- {int(time.time())} ---\n{result.stdout}\n")
                    if installer_visible(result.stdout):
                        print("iso-vm: Anaconda screen and ForjaOS identity visible")
                        return
                time.sleep(20)
            raise TimeoutError("Anaconda screen did not appear before timeout")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    args = parser.parse_args()
    boot(args.iso, args.output, args.timeout_seconds)


if __name__ == "__main__":
    main()
