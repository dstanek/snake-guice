#!/usr/bin/env python

"""Specification for how snake-guice handles inherited classes."""


from snakeguice import Injector, inject, annotate


class Data: pass
class OldData: pass
class NewData: pass


class Module:
    def configure(self, binder):
        binder.bind(Data, annotated_with='old', to=OldData)
        binder.bind(Data, annotated_with='new', to=NewData)


def describe_a_child_inheriting_an_injected_init():
    class Parent:
        @inject(value=OldData)
        def __init__(self, value):
            self.value = value

    class Child(Parent):
        pass

    instance = Injector(Module()).get_instance(Child)

    def child_should_have_value_set():
        assert isinstance(instance.value, OldData)


def describe_a_child_inheriting_an_injected_method():
    class Parent:
        @inject(value=Data)
        @annotate(value='old')
        def set_parent_value(self, value):
            self.parent_value = value

    class Child(Parent):
        @inject(value=Data)
        @annotate(value='new')
        def set_child_value(self, value):
            self.child_value = value

    instance = Injector(Module()).get_instance(Child)

    def parent_value_should_be_set():
        assert isinstance(instance.parent_value, OldData)

    def child_value_should_be_set():
        assert isinstance(instance.child_value, NewData)


def describe_a_child_overriding_an_inherited_method():
    class Parent:
        @inject(value=Data)
        @annotate(value='old')
        def set_value(self, value):
            self.parent_value = value

    class Child(Parent):
        @inject(value=Data)
        @annotate(value='new')
        def set_value(self, value):
            self.child_value = value

    instance = Injector(Module()).get_instance(Child)

    def value_should_be_set_by_child():
        assert isinstance(instance.child_value, NewData)

    def value_should_not_be_set_by_parent():
        assert hasattr(instance, 'parent_value') == False
