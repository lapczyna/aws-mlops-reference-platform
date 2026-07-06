"""Fixtures for Lambda handler integration tests.

Handlers construct their AWS clients and use cases at import time (cold
start), reading configuration through shared.config.get_settings(), which
is lru_cache'd. Each test must therefore, in order: set the environment
variables it needs, clear that cache, and force a fresh import of the
handler module -- otherwise a previous test's cached settings or
already-imported module object would leak into the next test.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from types import ModuleType

import pytest

from batch_inference_platform.shared.config import get_settings


@pytest.fixture
def import_handler() -> Callable[[str], ModuleType]:
    def _import(module_name: str) -> ModuleType:
        get_settings.cache_clear()
        sys.modules.pop(module_name, None)
        return importlib.import_module(module_name)

    return _import
