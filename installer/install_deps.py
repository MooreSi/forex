"""
Dependency installer — called by Inno Setup during installation.

Usage (from Inno Setup [Run] section):
    {app}\python_embed\python.exe {app}\installer\install_deps.py {app}

Creates a virtual environment under {app}\.venv and installs all requirements.
Writes {app}\.venv\req_hash.txt so the launcher skips re-installing on each start.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: install_deps.py <app_dir>")
        sys.exit(1)

    app_dir = Path(sys.argv[1]).resolve()
    req_file = app_dir / "requirements.txt"
    venv_dir = app_dir / ".venv"
    python   = sys.executable

    if not req_file.exists():
        print(f"ERROR: requirements.txt not found at {req_file}")
        sys.exit(1)

    print(f"App directory  : {app_dir}")
    print(f"Python         : {python}")
    print(f"Venv directory : {venv_dir}")
    print()

    # Create venv
    if not (venv_dir / "Scripts" / "python.exe").exists():
        print("Creating virtual environment...")
        result = subprocess.run(
            [python, "-m", "venv", str(venv_dir)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"ERROR creating venv:\n{result.stderr}")
            sys.exit(1)
        print("Virtual environment created.")
    else:
        print("Virtual environment already exists — skipping creation.")

    venv_python = venv_dir / "Scripts" / "python.exe"
    venv_pip    = venv_dir / "Scripts" / "pip.exe"

    # Upgrade pip
    print("\nUpgrading pip...")
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        check=False,
    )

    # Install requirements (--upgrade ensures all packages are at their required minimum)
    print("Installing packages (this may take several minutes)...")
    result = subprocess.run(
        [str(venv_pip), "install", "--quiet", "--upgrade", "-r", str(req_file)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ERROR installing requirements:\n{result.stderr}")
        sys.exit(1)
    print("Packages installed successfully.")

    # Store hash so launcher can detect when requirements change
    req_hash = hashlib.md5(req_file.read_bytes()).hexdigest()
    (venv_dir / "req_hash.txt").write_text(req_hash, encoding="utf-8")
    print(f"\nHash recorded: {req_hash}")
    print("\nSetup complete.")


if __name__ == "__main__":
    main()
