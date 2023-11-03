import pytest
import ionbench
import ionbench.optimisers.scipy_optimisers as scipy_opts
import ionbench.optimisers.pints_optimisers as pints_opts
import ionbench.optimisers.external_optimisers as ext_opts


class Test_scipy:
    # Check all scipy optimisers run and improve cost compared to x0
    bm = ionbench.problems.staircase.HH_Benchmarker(sensitivities=True)
    bm._useScaleFactors = True  # Helps the stability of conjugate GD (avoiding big steps which lead to parameters that result in failed model solves)
    bm.plotter = False
    optimisers = [scipy_opts.lm_scipy.run, scipy_opts.nelderMead_scipy.run, scipy_opts.powell_scipy.run, scipy_opts.trustRegionReflective_scipy.run, scipy_opts.conjugateGD_scipy.run]

    @pytest.mark.parametrize("run", optimisers)
    def test_cost_reduction(self, run):
        x0 = self.bm.sample()
        cost = self.bm.cost(x0)
        # sample initial point, find its cost, optimise, find opt cost, assert reduction
        x0_opt = run(self.bm, x0=x0, maxIter=5)
        cost_opt = self.bm.cost(x0_opt)
        self.bm.reset()
        assert cost_opt <= cost


class Test_pints:
    # Check all pints optimisers run and improve cost compared to x0
    bm = ionbench.problems.staircase.HH_Benchmarker()
    bm.plotter = False
    optimisers = [pints_opts.cmaes_pints.run, pints_opts.nelderMead_pints.run, pints_opts.pso_pints.run, pints_opts.snes_pints.run, pints_opts.xnes_pints.run]

    @pytest.mark.parametrize("run", optimisers)
    def test_cost_reduction(self, run):
        x0 = self.bm.sample()
        cost = self.bm.cost(x0)
        # sample initial point, find its cost, optimise, find opt cost, assert reduction
        x0_opt = run(self.bm, x0=x0, maxIter=50)
        cost_opt = self.bm.cost(x0_opt)
        self.bm.reset()
        assert cost_opt <= cost


class Test_external:
    # Check all external optimisers run
    bm = ionbench.problems.staircase.HH_Benchmarker(sensitivities=True)
    bm._useScaleFactors = True
    bm.plotter = False
    optimisers = [(ext_opts.GA_Bot2012.run, {'nGens': 5}), (ext_opts.GA_Smirnov2020.run, {'nGens': 5}), (ext_opts.hybridPSOTRR_Loewe2016.run, {'n': 5, 'maxIter': 5}), (ext_opts.patternSearch_Kohjitani2022.run, {'maxfev': 50}), (ext_opts.ppso_Chen2012.run, {'n': 5, 'maxIter': 5}), (ext_opts.curvilinearGD_Dokos2004.run, {'maxIter': 20}), (ext_opts.SA_Vanier1999.run, {'maxIter': 10}), (ext_opts.SPSA_Spall1998.run, {'maxIter': 5})]

    @pytest.mark.parametrize("run", optimisers)
    def test_cost_reduction(self, run):
        x0 = self.bm.sample()
        # sample initial point, find its cost, optimise, find opt cost, can't assert reduction - population algorithms sample around x0 not at x0
        run[0](self.bm, x0=x0, **run[1])
