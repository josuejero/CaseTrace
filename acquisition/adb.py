\"\"\"Adb helpers shared by the acquisition CLI.\"\"\"
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Sequence


def ensure_adb_available() -> Path:
    adb = shutil.which(\"adb\")
    if not adb:
        raise FileNotFoundError(\"'adb' executable not found on PATH; install Android platform tools\")
    return Path(adb)


def run_adb_command(serial: str, *args: str, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [\"adb\", \"-s\", serial]
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=capture_output, text=True)


def verify_device(serial: str) -> None:
    result = subprocess.run([\"adb\", \"devices\"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f\"adb devices failed: {result.stderr.strip()}\")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        raise RuntimeError(\"no devices attached to adb\")
    connected: list[str] = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        serial_id, status = parts[0], parts[1]
        if status == \"device\":
            connected.append(serial_id)
    if serial not in connected:
        raise RuntimeError(f\"target serial {serial} not connected; available: {connected}\")


def verify_package(serial: str, package: str) -> None:
    result = run_adb_command(serial, \"shell\", \"pm\", \"list\", \"packages\", package)
    if result.returncode != 0:
        raise RuntimeError(f\"pm list packages failed: {result.stderr.strip()}\")
    if f\"package:{package}\" not in result.stdout:
        raise RuntimeError(f\"package {package} not installed on device {serial}\")


def get_emulator_property(serial: str, prop: str) -> str:
    result = run_adb_command(serial, \"shell\", \"getprop\", prop)
    if result.returncode != 0:
        raise RuntimeError(f\"getprop {prop} failed: {result.stderr.strip()}\")
    return result.stdout.strip()


def get_app_version(serial: str, package: str) -> str:
    result = run_adb_command(serial, \"shell\", \"dumpsys\", \"package\", package)
    if result.returncode != 0:
        raise RuntimeError(f\"dumpsys package failed: {result.stderr.strip()}\")
    for line in result.stdout.splitlines():
        if \"versionName=\" in line:
            return line.split(\"versionName=\", 1)[1].strip()
    return \"unknown\"
