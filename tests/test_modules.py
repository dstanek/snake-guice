#!/usr/bin/env python

"""
Unit tests for snakeguice.modules -- Module._injector's ambient, per-run
tracking (see modules._configuring for the design rationale, part of the
B5 fix in BUGS.md section 6).
"""

from snakeguice import create_injector
from snakeguice.interfaces import Binder
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.modules import Module


class RecordingModule(Module):
    """Records the injector visible via self._injector while configure()
    runs, so a test can assert what the module saw without depending on any
    private state."""

    def __init__(self) -> None:
        self.seen_injector: InjectorI | None = None

    def configure(self, binder: Binder) -> None:
        self.seen_injector = self._injector


def test_module_injector_is_isolated_across_two_sequential_create_injector_calls() -> (
    None
):
    """A single plain Module instance, reused across two sequential
    create_injector() calls, must see its own injector on each build --
    Module._injector is looked up from an ambient per-run ContextVar stack
    (modules._configuring), not stored on the module instance, so nothing
    from the first build leaks into (or is overwritten by) the second.
    """

    module = RecordingModule()

    first_injector = create_injector([module])
    first_seen = module.seen_injector

    second_injector = create_injector([module])
    second_seen = module.seen_injector

    assert first_seen is first_injector
    assert second_seen is second_injector
    assert first_seen is not second_injector
