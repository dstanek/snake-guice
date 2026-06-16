from snakeguice.annotation import Annotation


class Test_Annotation_equality_against_non_Annotation:
    def test_hash_collision_does_not_produce_equality(self) -> None:
        a = Annotation("x")

        class HashThief:
            def __hash__(self) -> int:
                return hash(a)

        assert a != HashThief()

    def test_ne_against_unrelated_type(self) -> None:
        assert Annotation("x") != "x"
        assert Annotation("x") != 42
        assert Annotation("x") != None  # noqa: E711


class Test_Annotations_with_equal_values:
    annotation0: Annotation
    annotation1: Annotation

    @classmethod
    def setup_class(cls) -> None:
        cls.annotation0 = Annotation("value here")
        cls.annotation1 = Annotation("value here")

    def test_hash_the_same(self) -> None:
        assert hash(self.annotation0) == hash(self.annotation1)

    def test_should_be_equal(self) -> None:
        assert self.annotation0 == self.annotation1


class Test_Annotations_without_equal_values:
    annotation0: Annotation
    annotation1: Annotation

    @classmethod
    def setup_class(cls) -> None:
        cls.annotation0 = Annotation("value here0")
        cls.annotation1 = Annotation("value here1")

    def test_should_hash_differently(self) -> None:
        assert hash(self.annotation0) != hash(self.annotation1)

    def test_should_not_be_equal(self) -> None:
        assert self.annotation0 != self.annotation1


class Test_comparing_different_Annotation_subclasses(
    Test_Annotations_without_equal_values
):
    annotation0: Annotation
    annotation1: Annotation

    @classmethod
    def setup_class(cls) -> None:
        class Annotation0(Annotation):
            pass

        class Annotation1(Annotation):
            pass

        cls.annotation0 = Annotation0("value here")
        cls.annotation1 = Annotation1("value here")
