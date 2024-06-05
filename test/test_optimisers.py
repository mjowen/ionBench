import pytest
import ionbench
import numpy as np
from importlib import import_module
from inspect import signature


class TestScipy:
    # Check all scipy optimisers run and improve cost compared to x0
    bmTest = ionbench.problems.test.Test()

    @pytest.mark.parametrize("opt", ionbench.OPT_SCIPY)
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    @pytest.mark.cheap
    def test_minimum_finding(self, opt):
        module = import_module(opt)
        mod = module.get_modification()
        mod.apply(self.bmTest)
        x0_opt = module.run(self.bmTest, debug=True)
        cost_opt = self.bmTest.cost(x0_opt)
        assert cost_opt < 5e-3


class TestPints:
    bmTest = ionbench.problems.test.Test()

    @pytest.mark.parametrize("opt", ionbench.OPT_PINTS)
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    @pytest.mark.cheap
    def test_minimum_finding(self, opt):
        module = import_module(opt)
        mod = module.get_modification()
        mod.apply(self.bmTest)
        if 'cmaes' in opt:
            # Turn off bounds since rate bounds don't make sense here
            self.bmTest._parameters_bounded = False
        x0_opt = module.run(self.bmTest, debug=True)
        cost_opt = self.bmTest.cost(x0_opt)
        assert cost_opt < 5e-3


class TestExternal:
    bmTest = ionbench.problems.test.Test()

    @pytest.mark.parametrize("opt", ionbench.OPT_EXT)
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    @pytest.mark.cheap
    def test_minimum_finding(self, opt):
        module = import_module(opt)
        mod = module.get_modification()
        mod.apply(self.bmTest)
        if 'maxIter' in signature(module.run).parameters:
            if 'loewe' in opt.lower():
                x0_opt = module.run(self.bmTest, n=5, maxIter=10000, debug=True)
            else:
                x0_opt = module.run(self.bmTest, maxIter=10000, debug=True)
        else:
            x0_opt = module.run(self.bmTest, debug=True)
        cost_opt = self.bmTest.cost(x0_opt)
        assert cost_opt < 5e-3
