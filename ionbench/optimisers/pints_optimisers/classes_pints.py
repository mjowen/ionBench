import pints
import numpy as np
from functools import lru_cache


def pints_setup(bm, x0, method, forceUnbounded=False):
    """
    Set up a Pints model and optimisation controller for a benchmarker.
    Parameters
    ----------
    bm : benchmarker
        A test problem benchmarker.
    x0 : list
        Initial parameter vector from which to start optimisation. If x0=None, a randomly sampled parameter vector is retrieved from bm.sample().
    method : pints.Optimiser
        A Pints optimiser to use. For example, pints.CMAES, pints.PSO, or pints.NelderMead.
    forceUnbounded : bool, optional
        If True, the optimisation will be forced to be unbounded. Default is False.

    Returns
    -------
    model : Model
        A Pints model containing the benchmarker.
    opt : pints.OptimisationController
        An optimisation controller to run the pints optimisation on.
    """
    if x0 is None:
        x0 = bm.sample()
    model = classes_pints.Model(bm)
    problem = pints.SingleOutputProblem(model, np.arange(0, model.bm.T_MAX, model.bm.TIMESTEP), model.bm.DATA)
    error = pints.RootMeanSquaredError(problem)
    if bm.parametersBounded and not forceUnbounded:
        if bm.ratesBounded:
            boundaries = classes_pints.AdvancedBoundaries(bm)
        else:
            boundaries = pints.RectangularBoundaries(bm.input_parameter_space(bm.lb), bm.input_parameter_space(bm.ub))
        counter = 1
        while not boundaries.check(x0):
            x0 = bm.sample()
            counter += 1
        if counter > 10:
            print(f'Struggled to find parameters in bounds. Required {counter} iterations.')
        opt = pints.OptimisationController(error, x0, method=method, boundaries=boundaries)
    else:
        opt = pints.OptimisationController(error, x0, method=method)
    return model, opt


class Model(pints.ForwardModel):
    """
    A Pints forwards model containing a benchmarker class.
    """

    def __init__(self, bm):
        """
        Initialise a Pints forward model with a benchmarker, linking up the n_parameters() and simulate() methods.

        Parameters
        ----------
        bm : benchmarker
            A test problem benchmarker.

        Returns
        -------
        None.

        """
        self.bm = bm
        super().__init__()

    def n_parameters(self):
        """
        Returns the number of parameters in the model

        Returns
        -------
        n_parameters : int
            Number of parameters in the model.

        """
        return self.bm.n_parameters()

    def simulate(self, parameters, times):
        """
        Simulates the model and returns the model output.

        Parameters
        ----------
        parameters : list
            A list of parameter values, length n_parameters().
        times : list
            A list of times at which to return model output.

        Returns
        -------
        out : list
            Model output, typically a current trace.

        """
        # Reset the simulation
        return self.sim(tuple(parameters))

    @lru_cache(maxsize=None)
    def sim(self, p):
        """
        Simulate the model and return the model output. Cached to avoid double counting repeated calls.
        Parameters
        ----------
        p : tuple
            A tuple of parameter values, length n_parameters().
        """
        return self.bm.simulate(p, np.arange(0, self.bm.T_MAX, self.bm.TIMESTEP))


class AdvancedBoundaries(pints.Boundaries):
    """
    Pints boundaries to apply to the parameters and the rates.
    """

    def __init__(self, bm):
        """
        Build a Pints boundary object to apply parameter and rate bounds.

        Parameters
        ----------
        bm : benchmarker
            A test problem benchmarker.

        Returns
        -------
        None.

        """
        self.bm = bm

    def n_parameters(self):
        """
        Returns the number of parameters in the model.
        """
        return self.bm.n_parameters()

    def check(self, parameters):
        """
        Check inputted parameters against the parameter and rate bounds.

        Parameters
        ----------
        parameters : list
            Inputted parameter to check, in the input parameter space.

        Returns
        -------
        paramsInsideBounds : bool
            True if the parameters are inside the bound. False if the parameters are outside the bounds.

        """
        parameters = self.bm.original_parameter_space(parameters)
        return self.bm.in_rate_bounds(parameters) and self.bm.in_parameter_bounds(parameters)
