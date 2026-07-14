from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register asyncio_mode so local pytest runs do not require pytest-asyncio just to parse config."""
    parser.addini(
        'asyncio_mode',
        'Asyncio execution mode compatibility option used when pytest-asyncio is not installed.',
        default='auto',
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line('markers', 'asyncio: run async test functions on the default asyncio event loop')


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Small fallback runner for async tests when pytest-asyncio is missing.

    The project declares pytest-asyncio as a dev dependency, but local/global Python
    installs may run tests without it. This shim keeps the test contract stable.
    """
    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    fixture_names = getattr(pyfuncitem, '_fixtureinfo').argnames
    test_args: dict[str, Any] = {
        name: pyfuncitem.funcargs[name]
        for name in fixture_names
        if name in pyfuncitem.funcargs
    }
    asyncio.run(test_func(**test_args))
    return True
