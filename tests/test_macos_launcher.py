"""Native developer launcher identity and CPython startup checks, without a GUI.

The witnessed Launch Services/Qt interaction is recorded separately. These tests
require the current macOS developer toolchain; they do not certify an installer.
"""

import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.make_macos_launcher import build_launcher

ROOT = Path(__file__).parents[1]
pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("xcrun") is None,
    reason="local macOS launcher verification requires Apple's developer tools",
)


def test_native_launcher_hosts_the_configured_python(tmp_path: Path) -> None:
    destination = tmp_path / "BH developer test.app"
    build_launcher(destination, ROOT)
    info = plistlib.loads((destination / "Contents/Info.plist").read_bytes())
    binary = destination / "Contents/MacOS" / info["CFBundleExecutable"]
    # Mach-O identity must survive startup; a shell exec wrapper caused the defect.
    assert "Mach-O" in subprocess.check_output(["file", str(binary)], text=True)
    assert info["CFBundleIdentifier"] == "org.boundhorizons.solver.preview"
    assert info["BHDevelopmentPythonExecutable"] == str(ROOT / ".venv/bin/python")
    assert Path(info["BHDevelopmentPythonLibrary"]).is_file()
    subprocess.run(["codesign", "--verify", "--strict", str(destination)], check=True)
    result = subprocess.run(
        [str(binary), "--help"], capture_output=True, text=True, check=False, timeout=20
    )
    assert result.returncode == 0, result.stderr
    assert "BH solver native workstation preview" in result.stdout
    assert "--data-root" in result.stdout


def test_launcher_refuses_an_unowned_application(tmp_path: Path) -> None:
    destination = tmp_path / "Existing app.app"
    destination.mkdir()
    owner_file = destination / "owner-work.txt"
    owner_file.write_text("Preserve this existing application")
    with pytest.raises(ValueError, match="Refusing to replace"):
        build_launcher(destination, ROOT)
    assert owner_file.read_text() == "Preserve this existing application"
    assert not (destination / "Contents").exists()
