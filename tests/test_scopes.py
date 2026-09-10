import threading

from snakeguice.scopes import Singleton, ThreadLocalScope, _NoScope


class FakeProvider:
    def get(self) -> object:
        return object()


class Test_the_NoScope_scope:
    def setup_method(self) -> None:
        self.provider = FakeProvider()
        self.scope = _NoScope()

    def test_that_the_provider_is_passed_through(self) -> None:
        assert self.scope.scope("key", self.provider) is self.provider


class Test_the_Singleton_scope:
    def setup_method(self) -> None:
        self.key = "key"
        self.provider = FakeProvider()
        self.scope = Singleton()
        self.scope.scope(self.key, self.provider)

    def test_using_the_same_key_results_in_getting_a_cached_provider(self) -> None:
        instance_provider_0 = self.scope.scope(self.key, self.provider)
        instance_provider_1 = self.scope.scope(self.key, self.provider)
        assert instance_provider_0 == instance_provider_1


class Test_the_Singleton_scope_with_a_falsey_cached_instance:
    """The cache-hit check tests the cached *provider* for None, not the
    underlying instance -- so a falsey instance (0, "", [], False) must
    still be cached and reused, not mistaken for "nothing cached yet" and
    recomputed on every call."""

    def setup_method(self) -> None:
        self.key = "key"
        self.scope = Singleton()

    def test_falsey_instance_is_cached_and_reused(self) -> None:
        calls: list[int] = []

        class CountingFalseyProvider:
            def get(self) -> object:
                calls.append(1)
                return 0

        provider = CountingFalseyProvider()
        instance_provider_0 = self.scope.scope(self.key, provider)
        instance_provider_1 = self.scope.scope(self.key, provider)

        assert instance_provider_0 is instance_provider_1
        assert instance_provider_0.get() == 0
        assert len(calls) == 1


class Test_the_ThreadLocalScope:
    """Like Test_the_Singleton_scope above, but exercising the per-thread
    cache directly (no Injector involved) -- see BUGS.md section 6."""

    def setup_method(self) -> None:
        self.key = "key"
        self.provider = FakeProvider()
        self.scope = ThreadLocalScope()
        self.scope.scope(self.key, self.provider)

    def test_using_the_same_key_on_the_same_thread_returns_a_cached_provider(
        self,
    ) -> None:
        instance_provider_0 = self.scope.scope(self.key, self.provider)
        instance_provider_1 = self.scope.scope(self.key, self.provider)
        assert instance_provider_0 == instance_provider_1

    def test_different_threads_get_independent_providers_for_the_same_key(
        self,
    ) -> None:
        """The whole point of ThreadLocalScope over Singleton: the same key,
        resolved twice on each of two different threads, must be cached
        per-thread (stable across the two calls on one thread) rather than
        shared globally (equal across threads). Comparing the *resolved*
        instances, not the wrapper Provider objects create_instance_provider
        constructs fresh on every cache miss, is what actually
        distinguishes a per-thread cache from no cache at all.

        Results are collected by list index, not threading.get_ident() -- a
        short-lived thread's OS-level id can be reused by the next thread
        started after it exits, so keying by ident (without forcing both
        threads to be alive at once) can silently collide two "different"
        threads' results into one dict entry instead of catching a real
        cross-thread leak. The Barrier forces genuine overlap instead.
        """

        barrier = threading.Barrier(2)
        results: list[tuple[object, object] | None] = [None, None]

        def resolve(index: int) -> None:
            barrier.wait()  # both threads must be alive together
            first = self.scope.scope(self.key, FakeProvider()).get()
            second = self.scope.scope(self.key, FakeProvider()).get()
            results[index] = (first, second)

        threads = [threading.Thread(target=resolve, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        pair_a, pair_b = results
        assert pair_a is not None
        assert pair_b is not None
        first_a, second_a = pair_a
        first_b, second_b = pair_b
        assert first_a is second_a  # stable across repeated calls on one thread
        assert first_b is second_b
        assert first_a is not first_b  # but not shared between threads
