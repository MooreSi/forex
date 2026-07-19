# Building the Windows Installer

## Prerequisites (on a Windows machine or VM)

1. Install **Inno Setup 6**: https://jrsoftware.org/isinfo.php

2. Download **Python 3.11 embeddable (64-bit)**:
   https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
   Extract the zip contents into: `installer/python_embed/`

3. Download **get-pip.py**:
   https://bootstrap.pypa.io/get-pip.py
   Save to: `installer/get-pip.py`

## Build Steps

1. Open `installer/FOREX_Trader_Setup.iss` in Inno Setup Compiler
2. Press **F9** (Build → Compile)
3. Wait for compilation (2-5 minutes on first run)
4. Installer appears at: `installer/Output/FOREX_Trader_Setup_1.0.0.exe`

## What the Installer Does

For the user (hands-off):
1. Checks if MetaTrader 5 is installed (warns if not)
2. Copies all app files to `%LOCALAPPDATA%\FOREX Trader\`
3. Bootstraps pip into the bundled Python
4. Creates a Python virtual environment at `%LOCALAPPDATA%\FOREX Trader\.venv\`
5. Installs all packages from requirements.txt (~5 minutes, requires internet)
6. Adds Windows Firewall rules for ports 8888 and 9000 (requires the one admin UAC prompt)
7. Creates Start Menu and optional desktop shortcuts
8. Optionally launches the app immediately after install

## User Setup After Installation (MT5 side)

The user still needs to:
1. Open MetaTrader 5 from their broker and log in
2. Enable "Algo Trading" in the MT5 toolbar (robot icon → green)
3. Enter their credentials in FOREX Trader → Settings → MT5/Bridge

These steps cannot be automated as they depend on the user's specific broker account.

## Updating the Version

Change `AppVersion` and `VersionInfoVersion` at the top of the .iss file.
The installer will create `FOREX_Trader_Setup_<version>.exe` in Output/.
