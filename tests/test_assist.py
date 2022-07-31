#!/usr/bin/env python

"""Tests for the assisted injection feature."""

import pytest

from snakeguice import annotate, create_injector, inject
from snakeguice.assist import AssistProvider, assisted_inject
from snakeguice.errors import AssistError


class IService:
    """An interface for services."""


class IWorkerFactory:
    """An interface to create Worker instances."""


class CustomerService:
    """A concrete service for dealing with customers."""


class OrderService:
    """A concrete service for dealing with orders."""


class Worker:
    """Uses services to do real work."""

    @assisted_inject(c_service=IService, o_service=IService)
    @annotate(c_service="customer", o_service="order")
    def __init__(self, c_service, o_service, name, date):
        self.c_service = c_service
        self.o_service = o_service
        self.name = name
        self.date = date


class Manager:
    """Makes sure that the worker does its work."""

    @inject(worker_factory=IWorkerFactory)
    def __init__(self, worker_factory):
        self.worker = worker_factory.create(name="awesome worker", date="07/09/2010")


class Module:
    def configure(self, binder):
        binder.bind(IWorkerFactory, to_provider=AssistProvider(Worker))
        binder.bind(IService, annotated_with="customer", to=CustomerService)
        binder.bind(IService, annotated_with="order", to=OrderService)


class test_partiall_injecting_an_object:
    def setup(self):
        inj = create_injector([Module()])
        self.manager = inj.get_instance(Manager)

    def test(self):
        assert isinstance(self.manager.worker, Worker)


class Base_AssistProvider_decorator_errors:
    def test_that_an_exception_is_raised(self):
        with pytest.raises(AssistError):
            AssistProvider(self.C)


class Test_creating_an_AssistProvider_from_an_inject(
    Base_AssistProvider_decorator_errors
):
    def setup(self):
        class C:
            @inject(x=object)
            def __init__(self, x):
                pass

        self.C = C


class Test_creating_an_AssistProvider_from_an_uninjected_object(
    Base_AssistProvider_decorator_errors
):
    def setup(self):
        class C:
            pass

        self.C = C


def test_using_assisted_inject_on_a_method():
    with pytest.raises(AssistError):

        class C:
            @assisted_inject(x=object)
            def m(self, x):
                pass
