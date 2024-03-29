from snakeguice.scopes import _NoScope, _Singleton


class FakeProvider:
    def get(self) -> object:
        return object()


class Test_the_NoScope_scope:
    def setup(self) -> None:
        self.provider = FakeProvider()
        self.scope = _NoScope()

    def test_that_the_provider_is_passed_through(self) -> None:
        assert self.scope.scope("key", self.provider) is self.provider


class Test_the_Singleton_scope:
    def setup(self) -> None:
        self.key = "key"
        self.provider = FakeProvider()
        self.scope = _Singleton()
        self.scope.scope(self.key, self.provider)

    def test_using_the_same_key_results_in_getting_a_cached_provider(self) -> None:
        instance_provider_0 = self.scope.scope(self.key, self.provider)
        instance_provider_1 = self.scope.scope(self.key, self.provider)
        assert instance_provider_0 == instance_provider_1
