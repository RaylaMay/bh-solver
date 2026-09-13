"""Create a local developer .app wrapper, not a distributable BH installer.

The native entry point hosts this checkout's existing Python in the app process;
it bundles no Qt, Python or scientific libraries. Re-run after moving the checkout.
DW9 owns standalone packaging, signing, notices, library replacement and release minimums.
"""

from __future__ import annotations

import argparse
import json
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path


def build_launcher(destination: Path, repository: Path) -> Path:
    """Build an app tied to an absolute checkout path and its existing venv.

    Return the generated app path. Only a new destination or one marked by this
    helper may be written; drafts are untouched. Missing runtime/ownership raises
    ValueError. Tool or filesystem failures propagate; compilation precedes app
    writes, but a later write/sign failure can require a rebuild. See the DW2
    native macOS verification record for scope, consent and release limitations.
    """
    executable = repository / ".venv/bin/python"
    if not executable.is_file():
        raise ValueError("Repository environment is missing")
    marker = destination / "Contents/Resources/bh-developer-launcher"
    legacy_marker = destination / "Contents/bh-developer-launcher"
    if destination.exists() and not (marker.is_file() or legacy_marker.is_file()):
        raise ValueError("Refusing to replace an application not created by this helper")
    # Read the selected environment's metadata, not the helper's interpreter.
    probe = subprocess.run(
        [
            str(executable),
            "-c",
            "import json,sysconfig; "
            "print(json.dumps([sysconfig.get_config_var('LIBDIR'), "
            "sysconfig.get_config_var('LDLIBRARY')]))",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    library_directory, library_name = json.loads(probe.stdout)
    library = Path(library_directory) / library_name
    if not library.is_file():
        raise ValueError("The selected environment has no dynamic Python runtime")
    # Compile before touching a previous wrapper. Compiler failure leaves it intact.
    source = Path(__file__).with_name("macos_developer_main.m")
    with tempfile.TemporaryDirectory(prefix="bh-launcher-build-") as scratch:
        built = Path(scratch) / "bh-workstation"
        subprocess.run(
            [
                "xcrun",
                "clang",
                "-fobjc-arc",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-framework",
                "AppKit",
                str(source),
                "-o",
                str(built),
            ],
            check=True,
        )
        executable_bytes = built.read_bytes()
    macos = destination / "Contents/MacOS"
    macos.mkdir(parents=True, exist_ok=True)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("DW2 native developer entry point; no bundled runtime\n")
    if legacy_marker.is_file():
        # The old generated marker sat in a code location and blocks bundle signing.
        legacy_marker.unlink()
    info = {
        "CFBundleName": "BH solver",
        "CFBundleDisplayName": "BH solver",
        "CFBundleIdentifier": "org.boundhorizons.solver.preview",
        "CFBundleExecutable": "bh-workstation",
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
        "NSDocumentsFolderUsageDescription": (
            "BH solver loads its development project and local drafts from Documents."
        ),
        "BHDevelopmentPythonExecutable": str(executable),
        "BHDevelopmentPythonLibrary": str(library),
        "BHDevelopmentDataRoot": str(repository / ".bh/native-preview"),
    }
    (destination / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    launcher = macos / "bh-workstation"
    launcher.write_bytes(executable_bytes)
    launcher.chmod(0o755)
    # Local ad-hoc identity only. No Developer ID, notarization or permission grant.
    subprocess.run(["codesign", "--force", "--sign", "-", str(destination)], check=True)
    return destination


def main() -> None:
    """Build the wrapper in the ignored local runtime directory by default."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("This developer launcher is for macOS only")
    repository = Path(__file__).resolve().parents[1]
    destination = args.destination or repository / ".bh/BH solver.app"
    print(build_launcher(destination, repository))


if __name__ == "__main__":
    main()
