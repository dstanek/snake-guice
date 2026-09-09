from unittest.mock import Mock

import pytest

from snakeguice import create_injector, inject
from snakeguice.binder import Binder
from snakeguice.errors import BindingError, CircularDependencyError, CreationError
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


def test_circular_dependency_error_is_a_binding_error_but_not_a_creation_error() -> (
    None
):
    """CircularDependencyError is raised lazily from get_instance(), for a
    single key, potentially long after create_injector() has already
    succeeded -- unlike CreationError, which is only ever raised eagerly and
    in a batch, at create_injector() time. It stays inside the documented
    `except BindingError` catch-all as a sibling of CreationError, not a
    subclass of it.
    """
    assert issubclass(CircularDependencyError, BindingError)
    assert not issubclass(CircularDependencyError, CreationError)


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
    binder.bind(ch.Person, to=ch.EvilPerson())  # type: ignore[call-overload]

    assert len(binder.errors) == 1
    assert "'to' requires a new-style class" in binder.errors[0].message


def test_to_provider_without_get_method_class_is_recorded() -> None:
    binder = Binder()
    binder.bind(ch.Person, to_provider=ch.EvilPerson)  # type: ignore[arg-type]

    assert len(binder.errors) == 1
    assert "a 'get' method" in binder.errors[0].message


def test_to_provider_without_get_method_instance_is_recorded() -> None:
    binder = Binder()
    binder.bind(ch.Person, to_provider=ch.EvilPerson())  # type: ignore[call-overload]

    assert len(binder.errors) == 1
    assert "a 'get' method" in binder.errors[0].message


def test_to_instance_accepts_a_duck_typed_stand_in() -> None:
    """to_instance= no longer requires isinstance(to_instance, _class); a
    duck-typed test double is enough, matching the other two binding forms."""

    class FakePerson:
        pass

    binder = Binder()
    binder.bind(ch.Person, to_instance=FakePerson())

    assert binder.errors == []


def test_to_instance_accepts_a_mock() -> None:
    binder = Binder()
    binder.bind(ch.Person, to_instance=Mock())

    assert binder.errors == []


def test_to_instance_with_annotation_still_resolves_the_bound_instance() -> None:
    """Annotation-keyed to_instance= bindings still work with the isinstance
    check removed."""

    mock_person = Mock()

    class MyModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(ch.Person, annotated_with="fake", to_instance=mock_person)

    inj = create_injector([MyModule()])
    assert inj.get_instance(ch.Person, "fake") is mock_person


def test_to_instance_duck_typed_instance_bound_in_one_module_consumed_in_another() -> (
    None
):
    """A duck-typed to_instance= binding must resolve across module
    boundaries too, not only when bound and consumed by the same module."""

    class FakePerson:
        """Duck-typed stand-in; not a ch.Person subclass."""

    class Consumer:
        @inject
        def __init__(self, person: ch.Person) -> None:
            self.person = person

    fake_person = FakePerson()

    class BindingModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(ch.Person, to_instance=fake_person)

    class ConsumerModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(Consumer, to=Consumer)

    inj = create_injector([BindingModule(), ConsumerModule()])
    consumer = inj.get_instance(Consumer)
    assert consumer.person is fake_person  # type: ignore[comparison-overlap]


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
    binder.bind(ch.Person)  # type: ignore[call-overload]  # no to / to_provider / to_instance

    assert len(binder.errors) == 1
    assert "no binding target" in binder.errors[0].message


def test_to_and_to_instance_together_is_recorded_as_error() -> None:
    binder = Binder()
    binder.bind(ch.Person, to=ch.EvilPerson, to_instance=ch.EvilPerson())  # type: ignore[call-overload]

    assert len(binder.errors) == 1
    assert "multiple binding targets" in binder.errors[0].message


def test_to_and_to_provider_together_is_recorded_as_error() -> None:
    binder = Binder()
    binder.bind(ch.Person, to=ch.EvilPerson, to_provider=ch.EvilPerson)  # type: ignore[call-overload]

    assert len(binder.errors) == 1
    assert "multiple binding targets" in binder.errors[0].message


def test_to_provider_and_to_instance_together_is_recorded_as_error() -> None:
    binder = Binder()
    binder.bind(ch.Person, to_provider=ch.EvilPerson, to_instance=ch.EvilPerson())  # type: ignore[call-overload]

    assert len(binder.errors) == 1
    assert "multiple binding targets" in binder.errors[0].message


def test_create_injector_raises_creation_error_on_duplicate_binding() -> None:
    class PrimaryModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(ch.Person, to=ch.EvilPerson)

    class ReplicaModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(ch.Person, to=ch.GoodPerson)

    with pytest.raises(CreationError):
        create_injector([PrimaryModule(), ReplicaModule()])
