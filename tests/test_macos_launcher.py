"""Native developer launcher identity and CPython startup checks, without a GUI.

The witnessed Launch Services/Qt interaction is recorded separately. These tests
require the current macOS developer toolchain; they do not certify an installer.
"""

import json
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.make_macos_launcher import build_launcher

ROOT = Path(__file__).parents[1]


def _configured_python_has_dynamic_runtime() -> bool:
    """Return whether the launcher-selected environment supports dlopen."""
    executable = ROOT / ".venv/bin/python"
    if not executable.is_file():
        return False
    probe = subprocess.run(
        [
            str(executable),
            "-c",
            "import json,sysconfig; "
            "print(json.dumps([sysconfig.get_config_var('LIBDIR'), "
            "sysconfig.get_config_var('LDLIBRARY')]))",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if probe.returncode != 0:
        return False
    library_directory, library_name = json.loads(probe.stdout)
    if not library_directory or not library_name:
        return False
    return (Path(library_directory) / library_name).is_file()


pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("xcrun") is None,
    reason="local macOS launcher verification requires Apple's developer tools",
)


@pytest.mark.skipif(
    sys.platform == "darwin"
    and shutil.which("xcrun") is not None
    and not _configured_python_has_dynamic_runtime(),
    reason="launcher startup verification requires a dynamic CPython runtime",
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
