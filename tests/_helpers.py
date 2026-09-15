import importlib
import os
import tempfile
from pathlib import Path


class VaultSandbox:
    def __init__(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.vault_root = Path(self.tmpdir.name)
        self.notes_root = self.vault_root / "Notes"
        self.notes_root.mkdir(parents=True)
        self._old_env = {}

    def __enter__(self):
        self._old_env = {
            "DAILY_NOTE_VAULT_ROOT": os.environ.get("DAILY_NOTE_VAULT_ROOT"),
            "DAILY_NOTE_LOG_DIR": os.environ.get("DAILY_NOTE_LOG_DIR"),
        }
        os.environ["DAILY_NOTE_VAULT_ROOT"] = str(self.vault_root)
        os.environ["DAILY_NOTE_LOG_DIR"] = str(self.vault_root / "logs")
        self._reload_modules()
        return self

    def __exit__(self, exc_type, exc, tb):
        for key, val in self._old_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        self._reload_modules_safely()
        self.tmpdir.cleanup()

    def _reload_modules(self):
        import lib.config
        importlib.reload(lib.config)
        for name in [
            "lib.calendar_utils",
            "lib.parser",
            "lib.events",
            "lib.daily_writer",
            "lib.monthly_summary",
            "lib.monthly_drop",
            "lib.archive",
            "lib.orchestrator",
        ]:
            try:
                mod = importlib.import_module(name)
                importlib.reload(mod)
            except Exception:
                pass

    def _reload_modules_safely(self):
        try:
            self._reload_modules()
        except Exception:
            pass
