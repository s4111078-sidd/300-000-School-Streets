"""I/O utility functions — stub for Phase 6."""


def ensure_dir(path: str) -> str:
    """Create directory if it doesn't exist. Returns path."""
    import os
    os.makedirs(path, exist_ok=True)
    return path
