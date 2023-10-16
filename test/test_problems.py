import pytest
import ionbench
import numpy as np
import copy
import matplotlib.pyplot as plt

class Problem():
    def test_cost(self):
        #Check cost of default params is sufficiently low (0 for loewe)
        assert self.bm.cost(self.bm.defaultParams) <= self.costBound
    
    def test_hasattr(self):
        #Check all neccessary variables in problems are defined
        assert hasattr(self.bm, "_name")
        assert hasattr(self.bm, "model")
        assert hasattr(self.bm, "_outputName")
        assert hasattr(self.bm, "_paramContainer")
        assert hasattr(self.bm, "defaultParams")
        assert hasattr(self.bm, "_rateFunctions")
        assert hasattr(self.bm, "standardLogTransform")
        assert hasattr(self.bm, "_trueParams")
        assert hasattr(self.bm, "data")
        assert hasattr(self.bm, "sim")
        assert hasattr(self.bm, "_useScaleFactors")
        assert hasattr(self.bm, "_bounded")
        assert hasattr(self.bm, "_logTransformParams")
        assert hasattr(self.bm, "plotter")
        assert hasattr(self.bm, "tracker")
    
    def test_plotter(self, monkeypatch):
        #Test plotting functionality runs for evaluate
        monkeypatch.setattr(plt, 'show', lambda: None) #Disables plots from being shown
        self.bm.plotter = True
        self.bm.evaluate(self.bm.defaultParams)
        self.bm.plotter = False
    
    def test_bounds(self):
        #Check bounds give infinite cost outside and solve inside bounds
        self.bm.add_bounds([0.99*self.bm.defaultParams,[np.inf]*self.bm.n_parameters()])
        #Check bounds give infinite cost outside of bounds
        p = copy.copy(self.bm.defaultParams)
        p[0] = 0.98*p[0]
        assert self.bm.cost(p) == np.inf
        #Check cost is finite inside bounds when bounded
        p[0] = self.bm.defaultParams[0]
        assert self.bm.cost(p) < np.inf
        #Check _bounded = False turns off bounds
        self.bm._bounded = False
        p[0] = 0.98*p[0]
        assert self.bm.cost(p) < np.inf
    
    def test_tracker(self):
        #Check solve count works with bounds and evaluate
        self.bm.reset()
        #Solve count is 0 after reset
        assert self.bm.tracker.solveCount == 0
        #Solve count increments after solving
        self.bm.cost(self.bm.defaultParams)
        assert self.bm.tracker.solveCount == 1
        #but not when out of bounds
        self.bm.add_bounds([0.99*self.bm.defaultParams,[np.inf]*self.bm.n_parameters()])
        p = copy.copy(self.bm.defaultParams)
        p[0] = 0.98*self.bm.defaultParams[0]
        self.bm.cost(p)
        assert self.bm.tracker.solveCount == 1
        #Solve count doesn't increment when evaluating
        self.bm.evaluate(p)
        assert self.bm.tracker.solveCount == 1
        #returns to 0 after resetting
        self.bm.reset()
        assert self.bm.tracker.solveCount == 0
        self.bm._bounded = False
    
    @pytest.mark.filterwarnings("ignore:Parameters:UserWarning", "ignore:Failed:UserWarning")
    def test_grad(self):
        threshold = 0.1
        assert not self.bm._bounded
        params = self.bm.sample()
        self.bm.reset()
        assert self.bm.tracker.solveCount == 0
        self.bm.grad(params)
        assert self.bm.tracker.solveCount == self.bm.n_parameters()+1
        centreCost = self.bm.cost(params)
        self.bm.reset()
        self.bm.grad(params, centreCost)
        assert self.bm.tracker.solveCount == self.bm.n_parameters()
        self.bm.reset()
        g = self.bm.grad(params, incrementSolveCounter = False)
        assert self.bm.tracker.solveCount == 0
        #Check bounds properties
        #Bounds force step in other direction using bounds
        self.bm.add_bounds([[-np.inf]*self.bm.n_parameters(),params])
        assert self.bm.in_bounds(params)
        g2 = self.bm.grad(params, centreCost)
        assert all(np.logical_or(g != g2, g == 0)) #Since direction and step size has changed
        assert all(np.abs(g-g2)<=threshold*np.abs(g)) #All should be close
        #Bounds will be ignored if it cant find good nearby points in bounds
        self.bm.add_bounds([params,params])
        g2 = self.bm.grad(params, centreCost)
        assert all(np.logical_or(g != g2, g == 0)) #Since step size will still be decreased
        assert all(np.abs(g-g2)<=threshold*np.abs(g)) #All should be close
        self.bm._bounded = False
        #If centre is out of bounds, the bounds will be completely ignored
        g = self.bm.grad(params*1.01, centreCost)
        self.bm._bounded = True
        g2 = self.bm.grad(params*1.01, centreCost)
        assert all(g == g2)

class Staircase(Problem):
    def test_sampler(self):
        #Check sampler is inside the right bounds and doesnt just return default rates, across all transforms
        # Sampler in bounds
        assert sampler_bounds(self.bm, 0.5*self.bm.defaultParams, 1.5*self.bm.defaultParams)
        # Sampled different to default
        assert sampler_different(self.bm, self.bm.defaultParams)
        # Same for scale factor parameter space
        self.bm._useScaleFactors = True
        assert sampler_bounds(self.bm, 0.5, 1.5)
        assert sampler_different(self.bm, np.ones(self.bm.n_parameters()))
        self.bm._useScaleFactors = False
        # Same for log transformed space
        self.bm.log_transform()
        assert sampler_bounds(self.bm, np.log(0.5)+np.log(self.bm.defaultParams), np.log(1.5)+np.log(self.bm.defaultParams))
        assert sampler_different(self.bm, np.log(self.bm.defaultParams))
        self.bm.log_transform([False]*self.bm.n_parameters())
        # Same for scale factor and log transformed space
        self.bm.log_transform()
        self.bm._useScaleFactors = True
        assert sampler_bounds(self.bm, np.log(0.5), np.log(1.5))
        assert sampler_different(self.bm, np.zeros(self.bm.n_parameters()))
        self.bm.log_transform([False]*self.bm.n_parameters())
        self.bm._useScaleFactors = False
    
    def test_transforms(self):
        #Check transforms map as expected
        # Log transform default rates
        self.bm.log_transform()
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), np.log(self.bm.defaultParams))
        # Original space
        assert param_equal(self.bm.original_parameter_space(np.log(self.bm.defaultParams)), self.bm.defaultParams)
        self.bm.log_transform([False]*self.bm.n_parameters())
        # Scale factor default rates
        self.bm._useScaleFactors = True
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), np.ones(self.bm.n_parameters()))
        assert param_equal(self.bm.original_parameter_space(np.ones(self.bm.n_parameters())), self.bm.defaultParams)
        # Scale factor and log transformed space
        self.bm.log_transform()
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), np.zeros(self.bm.n_parameters()))
        assert param_equal(self.bm.original_parameter_space(np.zeros(self.bm.n_parameters())), self.bm.defaultParams)
        self.bm._useScaleFactors = False
        self.bm.log_transform([False]*self.bm.n_parameters())

class Loewe(Problem):
    def test_sampler(self):
        #Check sampler is inside the right bounds and doesnt just return default rates, across all transforms
        #Get bounds from an approach
        app = ionbench.approach.Approach(bounds='Sampler')
        app.apply(self.bm)
        lb = self.bm.lb
        ub = self.bm.ub
        self.bm._bounded = False
        # Sampler in bounds
        assert sampler_bounds(self.bm, lb, ub)
        # Sampled different to default
        assert sampler_different(self.bm, self.bm.defaultParams)
        # Same for scale factor parameter space
        self.bm._useScaleFactors = True
        assert sampler_bounds(self.bm, self.bm.input_parameter_space(lb), self.bm.input_parameter_space(ub))
        assert sampler_different(self.bm, np.ones(self.bm.n_parameters()))
        self.bm._useScaleFactors = False
        # Same for log transformed space
        self.bm.log_transform([not i for i in self.bm.additiveParams])
        assert sampler_bounds(self.bm, self.bm.input_parameter_space(lb), self.bm.input_parameter_space(ub))
        assert sampler_different(self.bm, np.log(self.bm.defaultParams))
        self.bm.log_transform([False]*self.bm.n_parameters())
        # Same for scale factor and log transformed space
        self.bm.log_transform([not i for i in self.bm.additiveParams])
        self.bm._useScaleFactors = True
        assert sampler_bounds(self.bm, self.bm.input_parameter_space(lb), self.bm.input_parameter_space(ub))
        assert sampler_different(self.bm, np.zeros(self.bm.n_parameters()))
        self.bm.log_transform([False]*self.bm.n_parameters())
        self.bm._useScaleFactors = False
    
    def test_transforms(self):
        #Check transforms map as expected
        # Log transform default rates
        self.bm.log_transform([not i for i in self.bm.additiveParams])
        logDefault = [np.log(self.bm.defaultParams[i]) if self.bm.standardLogTransform[i] else self.bm.defaultParams[i] for i in range(self.bm.n_parameters())]
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), logDefault)
        # Original space
        assert param_equal(self.bm.original_parameter_space(logDefault), self.bm.defaultParams)
        self.bm.log_transform([False]*self.bm.n_parameters())
        # Scale factor default rates
        self.bm._useScaleFactors = True
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), np.ones(self.bm.n_parameters()))
        assert param_equal(self.bm.original_parameter_space(np.ones(self.bm.n_parameters())), self.bm.defaultParams)
        # Scale factor and log transformed space
        self.bm.log_transform([not i for i in self.bm.additiveParams])
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), [0.0 if self.bm.standardLogTransform[i] else 1.0 for i in range(self.bm.n_parameters())])
        assert param_equal(self.bm.original_parameter_space([0.0 if self.bm.standardLogTransform[i] else 1.0 for i in range(self.bm.n_parameters())]), self.bm.defaultParams)
        self.bm.log_transform([False]*self.bm.n_parameters())
        self.bm._useScaleFactors = False

class Test_Moreno(Problem):
    bm = ionbench.problems.moreno2016.ina()
    bm.plotter = False
    costBound = 1e-4
    
    def test_sampler(self):
        #Check sampler is inside the right bounds and doesnt just return default rates, across all transforms
        # Sampler in bounds
        assert sampler_bounds(self.bm, 0.95*self.bm.defaultParams, 1.05*self.bm.defaultParams)
        # Sampled different to default
        assert sampler_different(self.bm, self.bm.defaultParams)
        # Same for wider bounds
        self.bm.paramSpaceWidth = 90
        assert sampler_bounds(self.bm, 0.1*self.bm.defaultParams, 1.9*self.bm.defaultParams)
        self.bm.paramSpaceWidth = 5
        # Sampled different to default
        assert sampler_different(self.bm, self.bm.defaultParams)
        # Same for scale factor parameter space
        self.bm._useScaleFactors = True
        assert sampler_bounds(self.bm, 0.95, 1.05)
        assert sampler_different(self.bm, np.ones(self.bm.n_parameters()))
        self.bm._useScaleFactors = False
        # Same for log transformed space
        self.bm.log_transform()
        assert sampler_bounds(self.bm, np.log(0.95)+np.log(self.bm.defaultParams), np.log(1.05)+np.log(self.bm.defaultParams))
        assert sampler_different(self.bm, np.log(self.bm.defaultParams))
        self.bm.log_transform([False]*self.bm.n_parameters())
        # Same for scale factor and log transformed space
        self.bm.log_transform()
        self.bm._useScaleFactors = True
        assert sampler_bounds(self.bm, np.log(0.95), np.log(1.05))
        assert sampler_different(self.bm, np.zeros(self.bm.n_parameters()))
        self.bm.log_transform([False]*self.bm.n_parameters())
        self.bm._useScaleFactors = False
    
    def test_transforms(self):
        #Check transforms map as expected
        # Log transform default rates
        self.bm.log_transform()
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), np.log(self.bm.defaultParams))
        # Original space
        assert param_equal(self.bm.original_parameter_space(np.log(self.bm.defaultParams)), self.bm.defaultParams)
        self.bm.log_transform([False]*self.bm.n_parameters())
        # Scale factor default rates
        self.bm._useScaleFactors = True
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), np.ones(self.bm.n_parameters()))
        assert param_equal(self.bm.original_parameter_space(np.ones(self.bm.n_parameters())), self.bm.defaultParams)
        # Scale factor and log transformed space
        self.bm.log_transform()
        assert param_equal(self.bm.input_parameter_space(self.bm.defaultParams), np.zeros(self.bm.n_parameters()))
        assert param_equal(self.bm.original_parameter_space(np.zeros(self.bm.n_parameters())), self.bm.defaultParams)
        self.bm.log_transform([False]*self.bm.n_parameters())
        self.bm._useScaleFactors = False
    
    def test_grad(self):
        #Ignore grad test for Moreno. Model is too expensive to solve that many times.
        pass

class Test_HH(Staircase):
    bm = ionbench.problems.staircase.HH_Benchmarker()
    bm.plotter = False
    costBound = 0.04 #Accounts for noise

class Test_MM(Staircase):
    bm = ionbench.problems.staircase.MM_Benchmarker()
    bm.plotter = False
    costBound = 0.02 #Accounts for noise

class Test_Loewe_IKr(Loewe):
    bm = ionbench.problems.loewe2016.ikr()
    bm.plotter = False
    costBound = 0

class Test_Loewe_IKur(Loewe):
    bm = ionbench.problems.loewe2016.ikur()
    bm.plotter = False
    costBound = 0


def sampler_bounds(bm, lb, ub):
    """
    Test function for checking that sampled parameters lie within the expected bounds
    """
    p = bm.sample()
    return all(np.logical_and(p>=lb, p<=ub))

def sampler_different(bm, default):
    """
    Test function for checking that sampled parameters are different to the default parameters
    """
    p = bm.sample()
    return not param_equal(p, default)

def param_equal(p1, p2):
    """
    Test function to check if two parameters are equal
    """
    return all(np.abs(p1 - p2)<1e-10)
