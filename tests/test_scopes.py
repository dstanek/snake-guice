from snakeguice.scopes import Singleton, _NoScope


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
