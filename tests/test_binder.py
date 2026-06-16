import pytest

from snakeguice import create_injector
from snakeguice.binder import Binder
from snakeguice.errors import BindingError, CreationError
from snakeguice.interfaces import Binder as BinderI

from . import cls_heirarchy as ch


def test_clean_binder_raises_nothing() -> None:
    binder = Binder()
    binder.raise_if_errors()


def test_duplicate_binding_is_recorded_not_raised() -> None:
    binder = Binder()
    binder.bind(ch.Person, to=ch.EvilPerson)
    binder.bind(ch.Person, to=ch.GoodPerson)

    assert len(binder.errors) == 1
    assert "already bound" in binder.errors[0].message


def test_raise_if_errors_raises_creation_error_with_details() -> None:
    binder = Binder()
    binder.bind(ch.Person, to=ch.EvilPerson)
    binder.bind(ch.Person, to=ch.GoodPerson)

    with pytest.raises(CreationError) as exc_info:
        binder.raise_if_errors()

    message = str(exc_info.value)
    err = binder.errors[0]
    assert err.message in message
    assert err.location in message
    assert err.source in message


def test_creation_error_is_a_binding_error() -> None:
    assert issubclass(CreationError, BindingError)


def test_multiple_errors_are_numbered() -> None:
    binder = Binder()
    binder.bind(ch.Person, to=ch.EvilPerson)
    binder.bind(ch.Person, to=ch.GoodPerson)
    binder.bind(ch.Place, to=ch.Beach)
    binder.bind(ch.Place, to=ch.Glacier)

    with pytest.raises(CreationError) as exc_info:
        binder.raise_if_errors()

    message = str(exc_info.value)
    assert message.startswith("2 errors while creating an injector:")
    assert "1) " in message
    assert "2) " in message


def test_invalid_to_argument_is_recorded() -> None:
    binder = Binder()
    binder.bind(ch.Person, to=ch.EvilPerson())

    assert len(binder.errors) == 1
    assert "'to' requires a new-style class" in binder.errors[0].message


def test_add_error_handles_missing_source_context() -> None:
    binder = Binder()

    src = (
        "binder.bind(ch.Person, to=ch.EvilPerson)\n"
        "binder.bind(ch.Person, to=ch.GoodPerson)\n"
    )
    exec(compile(src, "<test>", "exec"), {"binder": binder, "ch": ch})

    assert len(binder.errors) == 1
    assert binder.errors[0].source == "<source unavailable>"


def test_create_child_has_its_own_errors() -> None:
    parent = Binder()
    parent.bind(ch.Person, to=ch.EvilPerson)
    parent.bind(ch.Person, to=ch.GoodPerson)

    child = parent.create_child()

    assert parent.errors
    assert child.errors == []


def test_bind_without_target_is_recorded_as_error() -> None:
    binder = Binder()
    binder.bind(ch.Person)  # no to / to_provider / to_instance

    assert len(binder.errors) == 1
    assert "no binding target" in binder.errors[0].message


def test_create_injector_raises_creation_error_on_duplicate_binding() -> None:
    class PrimaryModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(ch.Person, to=ch.EvilPerson)

    class ReplicaModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(ch.Person, to=ch.GoodPerson)

    with pytest.raises(CreationError):
        create_injector([PrimaryModule(), ReplicaModule()])
