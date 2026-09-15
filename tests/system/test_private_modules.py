import inspect

import pytest

from snakeguice import (
    PrivateModule,
    annotate,
    create_injector,
    inject,
    provides,
    scopes,
)
from snakeguice.binder import Binder as ConcreteBinder
from snakeguice.errors import (
    BindingError,
    CircularDependencyError,
    CreationError,
    MissingBindingError,
)
from snakeguice.interfaces import Binder
from snakeguice.modules import Module


class IConnectionConfig:
    """Interface for a database connection configuration."""


class PrimaryConfig(IConnectionConfig):
    host = "db-primary.internal"


class ReplicaConfig(IConnectionConfig):
    host = "db-replica.internal"


class IDatabase:
    """Interface for a database connection."""


class Database(IDatabase):
    @inject
    def __init__(self, config: IConnectionConfig) -> None:
        self.config = config


def test_binding_the_same_interface_twice_on_one_binder_raises() -> None:
    class PrimaryModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(IConnectionConfig, to=PrimaryConfig)

    class ReplicaModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(IConnectionConfig, to=ReplicaConfig)

    with pytest.raises(BindingError):
        create_injector([PrimaryModule(), ReplicaModule()])


class PrimaryDatabaseModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        binder.bind(IDatabase, annotated_with="primary", to=Database)
        self.expose(binder, IDatabase, "primary")


class ReplicaDatabaseModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=ReplicaConfig)
        binder.bind(IDatabase, annotated_with="replica", to=Database)
        self.expose(binder, IDatabase, "replica")


class UserRepository:
    @inject
    @annotate(primary="primary", replica="replica")
    def __init__(self, primary: IDatabase, replica: IDatabase) -> None:
        self.primary = primary
        self.replica = replica


class AppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, PrimaryDatabaseModule())
        self.install(binder, ReplicaDatabaseModule())


def test_private_modules_isolate_bindings_and_expose_the_rest() -> None:
    injector = create_injector([AppModule()])
    repo = injector.get_instance(UserRepository)

    assert isinstance(repo.primary, Database)
    assert isinstance(repo.replica, Database)
    assert isinstance(repo.primary.config, PrimaryConfig)
    assert isinstance(repo.replica.config, ReplicaConfig)


class BrokenReplicaDatabaseModule(PrivateModule):
    """Exposes IDatabase under an annotation it never binds privately."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=ReplicaConfig)
        binder.bind(IDatabase, to=Database)
        self.expose(binder, IDatabase, "replica")


class BrokenAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, PrimaryDatabaseModule())
        self.install(binder, BrokenReplicaDatabaseModule())


def test_expose_without_a_matching_private_binding_raises_at_creation() -> None:
    msg = r"replica.*has no matching private binding"
    with pytest.raises(CreationError, match=msg):
        create_injector([BrokenAppModule()])


class UnannotatedConfigModule(PrivateModule):
    """Binds and exposes IConnectionConfig without an annotation."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        self.expose(binder, IConnectionConfig)


def test_expose_without_an_annotation_resolves_the_private_binding() -> None:
    injector = create_injector([UnannotatedConfigModule()])

    config = injector.get_instance(IConnectionConfig)

    assert isinstance(config, PrimaryConfig)


class HiddenDatabaseModule(PrivateModule):
    """Binds IDatabase privately, under an annotation, but never exposes it."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        binder.bind(IDatabase, annotated_with="hidden", to=Database)


class HiddenAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, HiddenDatabaseModule())


def test_private_binding_never_exposed_is_invisible_to_the_parent() -> None:
    """A key bound inside a private module but never passed to expose() must
    stay invisible to the parent injector -- under the old fall-through
    behavior an unexposed annotated key would silently implicitly-construct
    a plausible but wrong instance; now it must raise MissingBindingError."""

    injector = create_injector([HiddenAppModule()])

    with pytest.raises(MissingBindingError, match=r"hidden"):
        injector.get_instance(IDatabase, "hidden")


class IInner:
    """Interface for a cycle that lives entirely inside a private module."""


class IInnerOther:
    """The other half of the internal cycle."""


class InnerImpl(IInner):
    @inject
    def __init__(self, other: IInnerOther) -> None:
        self.other = other


class InnerOtherImpl(IInnerOther):
    @inject
    def __init__(self, inner: IInner) -> None:
        self.inner = inner


class CyclicPrivateModule(PrivateModule):
    """Both bindings, and the cycle between them, are entirely private.

    Exposing IInner doesn't matter here -- the cycle never crosses the
    private/parent boundary, it's confined to the private injector.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(IInner, to=InnerImpl)
        binder.bind(IInnerOther, to=InnerOtherImpl)
        self.expose(binder, IInner)


class CyclicPrivateAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, CyclicPrivateModule())


def test_cycle_entirely_inside_a_private_module_is_detected() -> None:
    """A genuine cycle confined to one private module's own bindings must
    still raise CircularDependencyError, not RecursionError -- the
    per-injector resolving stack has to work for the private injector too.
    """

    injector = create_injector([CyclicPrivateAppModule()])

    with pytest.raises(CircularDependencyError):
        injector.get_instance(IInner)


class IK:
    """Exposed by PrivA; its implementation depends on IL, exposed by PrivB."""


class IL:
    """Exposed by PrivB; its implementation depends on IK, exposed by PrivA."""


class KImpl(IK):
    @inject
    def __init__(self, ell: IL) -> None:
        self.ell = ell


class LImpl(IL):
    @inject
    def __init__(self, k: IK) -> None:
        self.k = k


class PrivA(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IK, to=KImpl)
        self.expose(binder, IK)


class PrivB(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IL, to=LImpl)
        self.expose(binder, IL)


class CrossPrivateAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, PrivA())
        self.install(binder, PrivB())


def test_cycle_spanning_two_private_modules_expose_boundaries_is_detected() -> None:
    """IK (exposed by PrivA) depends on IL (exposed by PrivB) depends back on
    IK: a cycle that crosses two separate expose() boundaries must still be
    detected, since every hop through an expose() provider always re-enters
    that private module's own (consistent) injector instance.
    """

    injector = create_injector([CrossPrivateAppModule()])

    with pytest.raises(CircularDependencyError):
        injector.get_instance(IK)


def test_cycle_spanning_two_private_modules_message_marks_the_expose_hops() -> None:
    """This cycle crosses two expose() boundaries (PrivA -> PrivB -> PrivA),
    so _format_chain() must mark each hop rather than render an unmarked
    "->" that would read like the false positive it isn't. The label is the
    neutral "[different injector]": a frame only records the injector it was
    resolved on, so an expose() hop and a plain create_child() hop are
    indistinguishable at format time (see
    test_injector.test_cross_injector_cycle_via_create_child_is_not_mislabeled_private_module
    for the create_child() side of that)."""

    injector = create_injector([CrossPrivateAppModule()])

    with pytest.raises(CircularDependencyError) as exc_info:
        injector.get_instance(IK)

    message = str(exc_info.value)
    # the cycle crosses PrivA -> PrivB -> PrivA, i.e. two injector hops
    assert message.count("[different injector]") >= 2


class Marker:
    pass


# One process-wide Singleton() instance, shared across every run of
# ReusedPrivateModule.configure() below -- deliberately, to show that
# scopes.Singleton's cache is keyed by the per-run Binding object (B3), not
# by this shared scope instance, so reusing it doesn't merge the two
# private injectors' caches.
_MARKER_SCOPE = scopes.Singleton()


class ReusedPrivateModule(PrivateModule):
    """A single instance of this is deliberately passed to two separate
    create_injector() calls below -- see B5."""

    def configure(self, binder: Binder) -> None:
        binder.bind(Marker, to=Marker, in_scope=_MARKER_SCOPE)
        self.expose(binder, Marker)


def test_reusing_a_private_module_across_two_injectors_keeps_them_independent() -> None:
    """Regression test for B5: run_configure() used to store
    original_binder/private_injector on the *module instance*, and the
    expose() provider closure read private_injector back off the module at
    resolution time -- so building a second injector from the same
    PrivateModule instance would silently repoint the first injector's
    exposed bindings into the second injector's private scope. Both
    injectors must resolve correctly and independently, even after the
    second one is built.

    Today each run_configure() call instead creates its own PrivateBinder
    (binder.create_private()), and the exposure provider resolves through
    that specific PrivateBinder's `.injector`, set once - and only once, per
    run - by Injector._build_private_injectors(), so the two runs can never
    cross-contaminate each other's private scope.
    """

    module = ReusedPrivateModule()

    i1 = create_injector([module])
    i2 = create_injector([module])

    # Resolved *after* i2 exists -- under the old bug, i1's exposed
    # provider would by now read module.private_injector == i2's private
    # injector, so m1 would incorrectly come out equal to m2.
    m1 = i1.get_instance(Marker)
    m2 = i2.get_instance(Marker)
    m1_again = i1.get_instance(Marker)

    assert type(m1) is Marker
    assert type(m2) is Marker
    assert m1 is not m2  # each injector's private scope is its own
    assert m1 is m1_again  # i1 keeps resolving through its OWN private injector


class Secret:
    pass


class ProvidedSecret(Secret):
    """Marker subclass returned by SecretProvidingPrivateModule's @provides."""


class SecretProvidingPrivateModule(PrivateModule):
    """Provides Secret privately via @provides, but binds and exposes
    nothing -- regression test for the @provides methods leaking onto the
    parent binder.
    """

    def configure(self, binder: Binder) -> None:
        pass

    @provides(Secret)
    def provide_secret(self) -> Secret:
        return ProvidedSecret()


def test_unexposed_provides_method_does_not_leak_onto_the_parent_binder() -> None:
    """Regression test: @provides(Secret) on a PrivateModule must bind Secret
    on the *private* binder, same as configure() would. Under the old bug it
    was instead bound on the parent's binder, so the parent would resolve
    the provided ProvidedSecret instance directly. Since Secret is never
    exposed, the parent has no binding for it at all, and Secret is
    unannotated, so the parent falls through to implicit construction: the
    result must be a plain Secret, not the private module's ProvidedSecret.
    """
    injector = create_injector([SecretProvidingPrivateModule()])

    secret = injector.get_instance(Secret)

    assert type(secret) is Secret


class Hidden:
    pass


class ProvidedHidden(Hidden):
    """Marker subclass returned by HiddenProvidingPrivateModule's @provides."""


class HiddenProvidingPrivateModule(PrivateModule):
    """Provides Hidden privately via @provides and exposes it -- the
    exposed binding must be satisfied by the @provides method landing on
    the private binder, not raise "no matching private binding".
    """

    def configure(self, binder: Binder) -> None:
        self.expose(binder, Hidden)

    @provides(Hidden)
    def provide_hidden(self) -> Hidden:
        return ProvidedHidden()


def test_exposed_provides_method_satisfies_the_expose() -> None:
    """Regression test: exposing a key that's only ever bound via a
    @provides method (never binder.bind()) must succeed -- the private
    binding it's checked against has to include @provides bindings, not
    just explicit binder.bind() calls."""
    injector = create_injector([HiddenProvidingPrivateModule()])

    hidden = injector.get_instance(Hidden)

    assert type(hidden) is ProvidedHidden


class Dep:
    pass


class ProvidedDep(Dep):
    """Marker subclass returned by DepProvidingPrivateModule's @provides."""


class Consumer:
    @inject
    def __init__(self, dep: Dep) -> None:
        self.dep = dep


class DepProvidingPrivateModule(PrivateModule):
    """Provides Dep privately via @provides (never exposed) and exposes
    Consumer, which depends on Dep -- proves the private @provides binding
    is visible to other bindings resolved *inside* the same private
    injector, even though it never crosses the expose() boundary itself.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(Consumer, to=Consumer)
        self.expose(binder, Consumer)

    @provides(Dep)
    def provide_dep(self) -> Dep:
        return ProvidedDep()


def test_private_provides_method_is_visible_inside_its_own_private_injector() -> None:
    injector = create_injector([DepProvidingPrivateModule()])

    consumer = injector.get_instance(Consumer)

    assert type(consumer.dep) is ProvidedDep


class NestedSecret:
    pass


class RealNestedSecret(NestedSecret):
    """Bound privately by OuterNestedModule; must be visible to a
    PrivateModule installed from *inside* OuterNestedModule's own
    configure(), not just to OuterNestedModule itself.
    """


class UsesNestedSecret:
    @inject
    def __init__(self, secret: NestedSecret) -> None:
        self.secret = secret


class InnerOnly:
    """Bound and exposed only inside InnerNestedModule; OuterNestedModule
    never re-exposes it, so it must stay invisible past Outer's boundary.
    """


class InnerNestedModule(PrivateModule):
    """Installed from inside OuterNestedModule.configure() -- its private
    binder must chain to Outer's private binder, not to the root, so it can
    see NestedSecret without Outer exposing it.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(UsesNestedSecret, to=UsesNestedSecret)
        binder.bind(InnerOnly, annotated_with="inner-only", to=InnerOnly)
        self.expose(binder, UsesNestedSecret)
        self.expose(binder, InnerOnly, "inner-only")


class OuterNestedModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(NestedSecret, to=RealNestedSecret)
        self.install(binder, InnerNestedModule())
        self.expose(binder, UsesNestedSecret)


def test_nested_private_modules_see_the_enclosing_private_bindings() -> None:
    """A PrivateModule installed from inside another PrivateModule's
    configure() must resolve dependencies against the enclosing module's
    private bindings, not fall through to implicit construction. Before the
    PrivateBinder redesign, a nested PrivateModule's child injector chained
    to the *root* binder instead of the enclosing private binder, so this
    used to silently construct a plain NestedSecret instead of the private
    RealNestedSecret.
    """
    injector = create_injector([OuterNestedModule()])

    uses = injector.get_instance(UsesNestedSecret)

    assert isinstance(uses.secret, RealNestedSecret)


def test_nested_private_bindings_do_not_leak_the_enclosing_binding_to_the_root() -> (
    None
):
    """NestedSecret is bound privately inside OuterNestedModule and never
    exposed, so resolving it unannotated at the root must fall through to
    implicit construction of a plain NestedSecret, not the private
    RealNestedSecret."""
    injector = create_injector([OuterNestedModule()])

    secret = injector.get_instance(NestedSecret)

    assert type(secret) is NestedSecret


def test_type_bound_only_inside_a_nested_private_module_is_invisible_at_the_root() -> (
    None
):
    """InnerOnly is bound and exposed by InnerNestedModule, but Outer never
    re-exposes it past its own boundary -- the root injector must have no
    binding for it at all."""
    injector = create_injector([OuterNestedModule()])

    with pytest.raises(MissingBindingError, match=r"inner-only"):
        injector.get_instance(InnerOnly, "inner-only")


class BrokenExposeOnlyModule(PrivateModule):
    """Exposes IDatabase without ever binding it privately -- a second,
    independent source of a configuration error, for the aggregation test
    below."""

    def configure(self, binder: Binder) -> None:
        self.expose(binder, IDatabase, "never-bound")


class DoublyBrokenAppModule(Module):
    """Combines a plain bind() error on the parent binder with a
    PrivateModule's expose() error, to prove both land in the same
    CreationError."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to="not a class")  # type: ignore[call-overload]
        self.install(binder, BrokenExposeOnlyModule())


def test_parent_bind_error_and_private_expose_error_aggregate_into_one() -> None:
    """A bind() error recorded directly on the parent's binder and an
    expose() error recorded on a private binder nested underneath it must
    both surface in the single CreationError raised at create_injector()
    time, not just whichever one is discovered first."""
    with pytest.raises(CreationError, match=r"2 errors") as exc_info:
        create_injector([DoublyBrokenAppModule()])

    message = str(exc_info.value)
    assert "'to' requires a new-style class" in message
    assert "no matching private binding" in message


class Bogus:
    pass


class WrongBinderExposeModule(PrivateModule):
    """Calls expose() with a fresh, unrelated Binder instead of the private
    binder configure() was actually given."""

    def configure(self, binder: Binder) -> None:
        binder.bind(Bogus, to=Bogus)
        self.expose(ConcreteBinder(), Bogus)


def test_expose_with_a_binder_other_than_the_one_configure_was_given_raises() -> None:
    """expose() must be called with the same (private) binder configure()
    received; passing an unrelated Binder is a programming error, not a
    configuration error to defer to CreationError time."""
    with pytest.raises(BindingError, match=r"expose\(\) must be called"):
        create_injector([WrongBinderExposeModule()])


class MissingBindingExposeModule(PrivateModule):
    """Exposes IDatabase without ever binding it privately, solely to check
    where the resulting CreationError says the problem is: the call site of
    self.expose() below, not a library frame inside PrivateModule.run_configure
    or Injector, which is where validate_exposures() actually runs and
    records the error."""

    def configure(self, binder: Binder) -> None:
        self.expose(binder, IDatabase, "location-check")


def test_expose_without_matching_binding_reports_the_expose_call_site() -> None:
    source, start_line = inspect.getsourcelines(MissingBindingExposeModule.configure)
    expose_line = next(
        start_line + offset
        for offset, line in enumerate(source)
        if "self.expose(" in line
    )

    with pytest.raises(CreationError) as exc_info:
        create_injector([MissingBindingExposeModule()])

    message = str(exc_info.value)
    assert f"File {__file__}, line {expose_line}, in configure" in message
