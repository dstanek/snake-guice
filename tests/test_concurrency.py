#!/usr/bin/env python

"""
Integration-level concurrency tests for the injector, the singleton scope,
and the new ThreadLocalScope -- see BUGS.md section 6 (B1, B3, P7) for the
design rationale behind the fixes these guard. These exercise real threads
(and, for one test, real asyncio scheduling via an executor) rather than
mocking the contended state, since the whole point of the fix is behavior
under actual concurrent access -- a mock can't reproduce a race.

threading.Barrier is used wherever "force real overlap" matters, rather than
sleep-based timing, to keep these deterministic.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from snakeguice import create_injector, inject, scopes
from snakeguice.errors import CircularDependencyError
from snakeguice.interfaces import Binder as BinderI


class _Slow:
    """Any dependency slow enough that two threads constructing it are
    virtually guaranteed to overlap -- time.sleep() releases the GIL, so
    this reliably forces real interleaving instead of hoping for it."""

    def __init__(self) -> None:
        time.sleep(0.02)


class _NeedsSlowA:
    @inject
    def __init__(self, s: _Slow) -> None:
        self.s = s


class _NeedsSlowB:
    @inject
    def __init__(self, s: _Slow) -> None:
        self.s = s


class _NeedsSlowC:
    @inject
    def __init__(self, s: _Slow) -> None:
        self.s = s


def test_threads_resolving_unrelated_keys_with_a_shared_dep_has_no_false_positive() -> (
    None
):
    """Regression test for B1: Injector._resolving used to be a single list
    shared by every thread using one Injector. Two threads resolving
    unrelated keys (_NeedsSlowA, _NeedsSlowB) that share the slow _Slow
    dependency would interleave their pushes/pops and see each other's
    frames as their own resolution chain, raising a bogus
    CircularDependencyError. The ContextVar-backed stack in _context.py is
    isolated per thread by default, so this must not happen."""

    inj = create_injector([])
    barrier = threading.Barrier(2)
    outcomes: dict[str, object] = {}
    lock = threading.Lock()

    def resolve(name: str, cls: type) -> None:
        barrier.wait()  # force both threads to enter get_instance() together
        try:
            result: object = inj.get_instance(cls)
        except BaseException as exc:  # noqa: BLE001 - captured across threads
            result = exc
        with lock:
            outcomes[name] = result

    threads = [
        threading.Thread(target=resolve, args=("a", _NeedsSlowA)),
        threading.Thread(target=resolve, args=("b", _NeedsSlowB)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert isinstance(outcomes["a"], _NeedsSlowA)
    assert isinstance(outcomes["b"], _NeedsSlowB)


class _ThreadCycle:
    @inject
    def __init__(self, other: "_ThreadCycle") -> None:
        self.other = other


def test_genuine_cycle_raised_from_a_worker_thread_is_still_caught() -> None:
    """The per-thread isolation that fixes the false positive above must
    not also blind the detector to a REAL cycle just because it happens on
    a worker thread rather than the main one."""

    inj = create_injector([])
    caught: list[BaseException] = []

    def resolve() -> None:
        try:
            inj.get_instance(_ThreadCycle)
        except BaseException as exc:  # noqa: BLE001
            caught.append(exc)

    t = threading.Thread(target=resolve)
    t.start()
    t.join()

    assert len(caught) == 1
    assert isinstance(caught[0], CircularDependencyError)


def test_concurrent_resolution_via_asyncio_gather_has_no_false_positive() -> None:
    """Same false-positive scenario as the plain-threading test above, but
    driven through asyncio.gather(). get_instance() is fully synchronous --
    there is no async provider support (yet, see _context.py's docstring)
    -- so genuine interleaving *within* a resolution can only happen if the
    call actually runs on a different OS thread, which is exactly what a
    real async application calling into this sync DI framework would do via
    loop.run_in_executor(). contextvars.Context propagation across that
    boundary is what this guards: the per-thread isolation from the
    plain-threading test above must also hold when the threads are
    asyncio's executor workers."""

    inj = create_injector([])

    async def main() -> None:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, c = await asyncio.gather(
                loop.run_in_executor(pool, inj.get_instance, _NeedsSlowA),
                loop.run_in_executor(pool, inj.get_instance, _NeedsSlowC),
            )
        assert isinstance(a, _NeedsSlowA)
        assert isinstance(c, _NeedsSlowC)

    asyncio.run(main())


def test_singleton_scope_under_thread_contention_constructs_exactly_once() -> None:
    """Regression test for P7 (double-checked locking): N threads racing to
    resolve the same not-yet-cached singleton-scoped binding for the first
    time must construct it exactly once. Asserting identity alone is not
    enough -- an unlocked check-then-act can still hand every thread the
    same *final* instance purely by how the unlocked reads happened to
    interleave, while still constructing (and discarding) extras along the
    way. Counting constructions catches that; identity does not."""

    construction_count = 0
    count_lock = threading.Lock()

    class _Widget:
        def __init__(self) -> None:
            nonlocal construction_count
            with count_lock:
                construction_count += 1
            time.sleep(0.02)  # widen the window between check and cache-write

    scope = scopes.Singleton()

    class MyModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(_Widget, to=_Widget, in_scope=scope)

    inj = create_injector([MyModule()])
    n = 8
    barrier = threading.Barrier(n)
    results: list[object] = []
    results_lock = threading.Lock()

    def resolve() -> None:
        barrier.wait()
        widget = inj.get_instance(_Widget)
        with results_lock:
            results.append(widget)

    threads = [threading.Thread(target=resolve) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == n
    assert len({id(w) for w in results}) == 1  # every thread got the same instance
    assert construction_count == 1  # ...and it was built exactly once


def test_two_unrelated_singletons_construct_concurrently_across_injectors() -> None:
    """Regression test for moving Singleton's construction lock from the
    scope object onto the Binding: two independent injectors, each binding
    its own class in_scope=scopes.SINGLETON, must be able to construct
    those unrelated singletons at the same time. Both constructors
    barrier.wait() on a shared, timed Barrier -- with a per-binding lock
    both threads are inside the barrier together and it releases; with the
    old design, where the exported scopes.SINGLETON held a single
    process-wide lock, the second constructor could not even start until
    the first finished constructing (and released the lock), so the second
    thread would never reach the barrier in time and BrokenBarrierError
    would surface out of the first constructor's barrier.wait()."""

    barrier = threading.Barrier(2, timeout=2)

    class _WidgetA:
        def __init__(self) -> None:
            barrier.wait()

    class _WidgetB:
        def __init__(self) -> None:
            barrier.wait()

    class ModuleA:
        def configure(self, binder: BinderI) -> None:
            binder.bind(_WidgetA, to=_WidgetA, in_scope=scopes.SINGLETON)

    class ModuleB:
        def configure(self, binder: BinderI) -> None:
            binder.bind(_WidgetB, to=_WidgetB, in_scope=scopes.SINGLETON)

    inj_a = create_injector([ModuleA()])
    inj_b = create_injector([ModuleB()])
    results: dict[str, object] = {}
    lock = threading.Lock()

    def resolve(name: str, inj: object, cls: type) -> None:
        try:
            result: object = inj.get_instance(cls)  # type: ignore[attr-defined]
        except BaseException as exc:  # noqa: BLE001 - captured across threads
            result = exc
        with lock:
            results[name] = result

    threads = [
        threading.Thread(target=resolve, args=("a", inj_a, _WidgetA)),
        threading.Thread(target=resolve, args=("b", inj_b, _WidgetB)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert isinstance(results["a"], _WidgetA)
    assert isinstance(results["b"], _WidgetB)


def test_constructing_one_singleton_does_not_block_constructing_another() -> None:
    """Regression test for the deadlock shape a single process-wide
    Singleton lock invites: A and B are both in_scope=scopes.SINGLETON on
    ONE injector, and A's constructor -- still "under construction", still
    holding whatever lock guards it -- spins up a worker thread that
    resolves B and only then sets an Event. With a per-binding lock this is
    fine, since A and B's construction locks are distinct; with one lock
    shared by every singleton, A's constructor would hold that lock for as
    long as it runs, so the worker's attempt to resolve B would block until
    A returns, and the Event would never be set within A's own wait --
    which is exactly the deadlock shape this pins."""

    construction_counts = {"B": 0}
    counts_lock = threading.Lock()
    b_resolved = threading.Event()

    class B:
        def __init__(self) -> None:
            with counts_lock:
                construction_counts["B"] += 1

    class A:
        def __init__(self) -> None:
            def worker() -> None:
                inj.get_instance(B)
                b_resolved.set()

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            self.worker_set_in_time = b_resolved.wait(timeout=2)

    class MyModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(A, to=A, in_scope=scopes.SINGLETON)
            binder.bind(B, to=B, in_scope=scopes.SINGLETON)

    inj = create_injector([MyModule()])
    result: list[object] = []

    def resolve() -> None:
        result.append(inj.get_instance(A))

    thread = threading.Thread(target=resolve, daemon=True)
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive(), "resolving A did not complete within the timeout"
    assert len(result) == 1
    a = result[0]
    assert isinstance(a, A)
    assert a.worker_set_in_time, "B did not resolve while A was under construction"
    assert construction_counts == {"B": 1}


def test_provider_reenter_same_binding_via_child_constructs_twice() -> None:
    """Pins the pre-existing, intentional limitation that motivates keeping
    scopes.Singleton's construction lock an RLock rather than a plain Lock:
    a to_provider= provider whose first call re-enters
    injector.create_child([]).get_instance(A) for the SAME key it is itself
    supplying. The child inherits the parent's Binding (and so its
    scope_lock), but the child is a different Injector object, so the
    (injector, key) cycle frame differs from the parent's and no
    CircularDependencyError fires. The re-entrant call sees no cached value
    yet and reacquires the (already held, by this same thread) scope_lock
    via RLock, constructing A a second time -- this is documented, existing
    behavior being pinned here, not a bug under test. What IS under test is
    that per-binding locks stay RLocks: swapping to a plain Lock would make
    this hang instead of double-construct, so the daemon thread and bounded
    join turn that hang into a fast, ordinary failure."""

    construction_count = 0
    count_lock = threading.Lock()

    class A:
        def __init__(self) -> None:
            nonlocal construction_count
            with count_lock:
                construction_count += 1

    class ReentrantProvider:
        def __init__(self) -> None:
            self._first_call = True

        def get(self) -> A:
            if self._first_call:
                self._first_call = False
                inj.create_child([]).get_instance(A)  # side effect only, discarded
            return A()

    class MyModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(A, to_provider=ReentrantProvider(), in_scope=scopes.SINGLETON)

    inj = create_injector([MyModule()])
    result: list[object] = []

    def resolve() -> None:
        result.append(inj.get_instance(A))

    thread = threading.Thread(target=resolve, daemon=True)
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive(), (
        "resolution did not complete within the timeout -- Singleton.scope() "
        "likely deadlocked (this is what an RLock-to-Lock regression looks "
        "like)"
    )
    assert len(result) == 1
    assert isinstance(result[0], A)
    assert construction_count == 2  # documented double construction, not a bug


def test_singleton_scope_rlock_allows_nested_resolution_of_another_singleton() -> None:
    """Regression guard pinning nested resolution of a DIFFERENT singleton
    completing correctly on one thread: A depends on B, both bound
    in_scope=the same shared_scope. Resolving A means A's own
    Singleton.scope() call is holding A's Binding.scope_lock (constructing
    A) when A's __init__ triggers get_instance(B), re-entering scope() for
    B's own, distinct Binding.scope_lock -- so with per-binding locks this
    never contends with itself in the first place. (The RLock-vs-Lock
    rationale that used to live here -- re-entering the identical shared
    scope object's lock -- no longer applies now that each Binding gets its
    own lock; that reasoning is pinned instead by
    test_provider_reenter_same_binding_via_child_constructs_twice,
    where a provider re-enters resolution for the SAME binding.)

    Resolution runs in a daemon worker thread with a bounded join() for
    exactly that reason: a regression here is a hang, not an exception, so
    only a timeout can turn it into a normal (fast) test failure instead of
    stalling the whole suite.
    """

    construction_counts = {"A": 0, "B": 0}
    counts_lock = threading.Lock()

    class B:
        def __init__(self) -> None:
            with counts_lock:
                construction_counts["B"] += 1

    class A:
        @inject
        def __init__(self, b: B) -> None:
            with counts_lock:
                construction_counts["A"] += 1
            self.b = b

    shared_scope = scopes.Singleton()

    class MyModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(A, to=A, in_scope=shared_scope)
            binder.bind(B, to=B, in_scope=shared_scope)

    inj = create_injector([MyModule()])
    result: list[object] = []
    errors: list[BaseException] = []

    def resolve() -> None:
        try:
            result.append(inj.get_instance(A))
        except BaseException as exc:  # noqa: BLE001 - captured across threads
            errors.append(exc)

    # daemon=True: if this DOES deadlock, the process must still be able to
    # exit once the test suite finishes, rather than hanging forever on a
    # non-daemon thread that never returns.
    thread = threading.Thread(target=resolve, daemon=True)
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive(), (
        "resolution did not complete within the timeout -- Singleton.scope() "
        "likely deadlocked (this is what an RLock-to-Lock regression looks "
        "like)"
    )
    assert not errors, errors
    assert len(result) == 1
    a = result[0]
    assert isinstance(a, A)
    assert isinstance(a.b, B)
    assert construction_counts == {"A": 1, "B": 1}


def test_thread_local_scope_gives_one_instance_per_thread() -> None:
    """New scopes.ThreadLocalScope, resolved through a real Injector: N
    threads each resolving a THREAD_LOCAL-scoped binding get their own
    instance, stable across repeated resolutions on the same thread,
    distinct across threads. Counting constructions doubles as the
    cache-miss-race check for ThreadLocalScope (item 9) -- unlike Singleton,
    ThreadLocalScope needs no lock (each thread only ever touches its own
    threading.local() cache), so "exactly once per thread" is the invariant
    that would catch a broken cache, not a race between threads."""

    construction_count = 0
    count_lock = threading.Lock()

    class _Widget:
        def __init__(self) -> None:
            nonlocal construction_count
            with count_lock:
                construction_count += 1

    scope = scopes.ThreadLocalScope()

    class MyModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(_Widget, to=_Widget, in_scope=scope)

    inj = create_injector([MyModule()])
    n = 4
    barrier = threading.Barrier(n)
    per_thread: dict[int, tuple[object, object]] = {}
    lock = threading.Lock()

    def resolve() -> None:
        barrier.wait()
        first = inj.get_instance(_Widget)
        second = inj.get_instance(_Widget)  # same thread, again
        with lock:
            per_thread[threading.get_ident()] = (first, second)

    threads = [threading.Thread(target=resolve) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(per_thread) == n
    for first, second in per_thread.values():
        assert first is second  # stable across repeated resolutions on one thread

    instances = [pair[0] for pair in per_thread.values()]
    assert len({id(i) for i in instances}) == n  # distinct across threads
    assert construction_count == n  # exactly one construction per thread


def test_exported_thread_local_scope_does_not_leak_between_independent_injectors() -> (
    None
):
    """The exported scopes.THREAD_LOCAL wraps one process-wide
    threading.local(), but two independent injectors binding the same class
    in_scope=scopes.THREAD_LOCAL on the same thread must still get distinct
    instances -- caching keyed by the ambient Binding (not just the Key) is
    what makes that safe, the same mechanism scopes.SINGLETON uses for B3.
    """

    class Widget:
        pass

    class MyModule:
        def configure(self, binder: BinderI) -> None:
            binder.bind(Widget, to=Widget, in_scope=scopes.THREAD_LOCAL)

    i1 = create_injector([MyModule()])
    i2 = create_injector([MyModule()])

    assert i1.get_instance(Widget) is not i2.get_instance(Widget)
