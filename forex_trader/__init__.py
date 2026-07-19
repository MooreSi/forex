from pathlib import Path as _Path


def _derive_version() -> str:
    """Read the current version from the top of RELEASES and sync VERSION file."""
    from forex_trader.version_history import RELEASES
    ver_str = RELEASES[0][0].lstrip("v") if RELEASES else "unknown"
    # Keep VERSION file in sync so remote/client.py (file-based reader) agrees.
    ver_file = _Path(__file__).parent / "VERSION"
    try:
        if ver_file.read_text(encoding="utf-8").strip() != ver_str:
            ver_file.write_text(ver_str + "\n", encoding="utf-8")
    except Exception:
        pass
    return ver_str


__version__ = _derive_version()
