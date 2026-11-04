"""Shared test setup: a throwaway data folder, set before Quota is imported."""
import os
import tempfile

os.environ.setdefault("QUOTA_DIR", tempfile.mkdtemp(prefix="quota-test-"))

from quota import store  # noqa: E402


def reset():
    """Empty data set with default settings."""
    store.reset()
    return store.DATA
