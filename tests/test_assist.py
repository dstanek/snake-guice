#!/usr/bin/env python

"""Tests for the assisted injection feature."""

from typing import Any, Type, cast

import pytest

from snakeguice import annotate, create_injector, inject
from snakeguice.assist import AssistProvider, assisted_inject
from snakeguice.errors import AssistError
from snakeguice.interfaces import Binder, Factory


class IService:
    """An interface for services."""


class CustomerService:
    """A concrete service for dealing with customers."""


class OrderService:
    """A concrete service for dealing with orders."""


class Worker:
    """Uses services to do real work."""

    @assisted_inject("name", "date")
    @annotate(c_service="customer", o_service="order")
    def __init__(
        self, c_service: IService, o_service: IService, name: str, date: str
    ) -> None:
        self.c_service = c_service
        self.o_service = o_service
        self.name = name
        self.date = date


class IWorkerFactory:
    """An interface to create Worker instances."""

    def create(self, name: str, date: str) -> Worker:
        raise NotImplementedError


class Manager:
    """Makes sure that the worker does its work."""

    @inject
    def __init__(self, worker_factory: IWorkerFactory) -> None:
        self.worker = worker_factory.create(name="awesome worker", date="07/09/2010")


class Module:
    def configure(self, binder: Binder) -> None:
        binder.bind(IWorkerFactory, to_provider=AssistProvider(Worker))
        binder.bind(IService, annotated_with="customer", to=CustomerService)
        binder.bind(IService, annotated_with="order", to=OrderService)


class Test_partially_injecting_an_object:
    def setup_method(self) -> None:
        inj = create_injector([Module()])
        self.manager = inj.get_instance(Manager)

    def test(self) -> None:
        assert isinstance(self.manager.worker, Worker)
        assert self.manager.worker.name == "awesome worker"
        assert self.manager.worker.date == "07/09/2010"


class Base_AssistProvider_decorator_errors:
    C: Type[Any]

    def test_that_an_exception_is_raised(self) -> None:
        with pytest.raises(AssistError):
            AssistProvider(self.C)


class Test_creating_an_AssistProvider_from_an_inject(
    Base_AssistProvider_decorator_errors
):
    def setup_method(self) -> None:
        class C:
            @inject
            def __init__(self, x: object) -> None:
                pass

        self.C = C


class Test_creating_an_AssistProvider_from_an_uninjected_object(
    Base_AssistProvider_decorator_errors
):
    def setup_method(self) -> None:
        class C:
            pass

        self.C = C


def test_using_assisted_inject_on_a_method() -> None:
    with pytest.raises(AssistError):

        class C:
            @assisted_inject("x")
            def m(self, x: object) -> None:
                pass


def test_create_with_unexpected_kwarg_raises_useful_type_error() -> None:
    inj = create_injector([Module()])
    # the runtime binding is a dynamically generated Factory[Worker], whose
    # create() accepts arbitrary kwargs and validates them itself
    factory = cast(Factory[Worker], inj.get_instance(IWorkerFactory))

    with pytest.raises(TypeError) as exc_info:
        factory.create(name="awesome worker", date="07/09/2010", oops="surprise")

    message = str(exc_info.value)
    assert "oops" in message
    assert "%r" not in message
