#!/usr/bin/env python

"""
_extractor module unit tests
"""

import inspect

import pytest

from snakeguice import _extractor
from snakeguice._extractor import Param, extract_params
from snakeguice.annotation import UNANNOTATED
from snakeguice.decorators import annotate, inject


class _Widget:
    @inject
    @annotate(b="named")
    def build(self, a: int, b: str = "default") -> bool:
        return True


class _NoInit:
    pass


def test_extract_params_reports_dtype_annotation_and_default() -> None:
    """Params without `@annotate` stay UNANNOTATED and carry their dtype and
    default; `@annotate(b="named")` carries the plain string through as-is,
    and the return annotation is skipped entirely."""
    params = extract_params(_Widget.build)

    assert params == (
        Param("a", int, UNANNOTATED, inspect.Parameter.empty),
        Param("b", str, "named", "default"),
    )


def test_bound_method_and_function_agree() -> None:
    """A bound method and its underlying function extract to the same
    params, and neither includes `self`."""
    widget = _Widget()

    bound_params = extract_params(widget.build)
    func_params = extract_params(_Widget.build)

    assert bound_params == func_params
    assert all(param.name != "self" for param in bound_params)


def test_class_with_no_init_has_no_params() -> None:
    """A class that doesn't define `__init__` inherits `object.__init__`,
    which has no annotated params to extract."""
    assert extract_params(_NoInit.__init__) == ()


def test_extract_params_is_memoised_per_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling extract_params twice on the same function only inspects the
    signature once; a callable with no annotations never needs it at all."""
    calls: list[object] = []
    real_signature = inspect.signature

    def counting_signature(obj: object) -> inspect.Signature:
        calls.append(obj)
        return real_signature(obj)  # type: ignore[arg-type]

    monkeypatch.setattr(getattr(_extractor, "inspect"), "signature", counting_signature)

    def annotated(a: int) -> None:
        pass

    def unannotated():  # type: ignore[no-untyped-def]
        pass

    extract_params(annotated)
    extract_params(annotated)
    assert len(calls) == 1

    extract_params(unannotated)
    assert len(calls) == 1
