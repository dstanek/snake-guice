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


def test_singleton_scope_rlock_allows_nested_resolution_of_another_singleton() -> None:
    """Regression guard for scopes.Singleton using threading.RLock, not a
    plain threading.Lock: constructing one singleton-scoped binding can
    legitimately re-enter Singleton.scope() on the SAME thread for a
    DIFFERENT binding, when that dependency is *also* scoped through the
    same Singleton() instance. Here A depends on B, and both are bound
    in_scope=the same shared_scope: resolving A means A's own
    Singleton.scope() call is still holding self._lock (inside the
    "with self._lock:" block, constructing A) when A's __init__ triggers
    get_instance(B), which re-enters scope() on that identical scope
    object. An RLock lets the same thread re-acquire it; a plain Lock
    would block forever waiting for a lock it already holds, deadlocking
    on the very first resolution -- so if a future "simplification" swaps
    RLock for Lock, this must fail loudly instead of just hanging CI.

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
