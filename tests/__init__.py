import os
import tempfile

_default_vault = tempfile.mkdtemp(prefix="daily-note-test-default-")
os.environ.setdefault("DAILY_NOTE_VAULT_ROOT", _default_vault)
os.environ.setdefault("DAILY_NOTE_LOG_DIR", os.path.join(_default_vault, "logs"))
