import shutil
import tempfile
from pathlib import Path


class Sandbox:
    """Owns one throwaway directory. Context manager. No git knowledge."""

    def __init__(self) -> None:
        self.path: Path = Path(tempfile.mkdtemp(prefix="gog-"))
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        shutil.rmtree(self.path, ignore_errors=False)
        self._closed = True

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
