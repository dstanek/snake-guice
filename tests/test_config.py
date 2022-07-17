#!python

from snakeguice import config


# class __TestConfig(DingusTestCase(config.Config)):
class __TestConfig:
    def setup(self):
        super(__TestConfig, self).setup()

        self.s = "some string value"
        self.c = config.Config(self.s)

    def test(self):
        assert self.c.entry == self.s
