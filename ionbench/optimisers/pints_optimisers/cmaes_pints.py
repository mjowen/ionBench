import pints
import ionbench
import numpy as np
from ionbench.optimisers.pints_optimisers import classes_pints


def run(bm, x0=None, popSize=12, maxIter=1000, debug=False):
    """
    Runs CMA-ES from Pints using a benchmarker.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter vector from which to start optimisation. Default is None, in which case a randomly sampled parameter vector is retrieved from bm.sample().
    popSize : int, optional
        The population size to use in CMA-ES.
    maxIter : int, optional
        Number of iterations of CMA-ES to run. The default is 1000.
    debug : bool, optional
        If True, logging messages are printed every iteration. Otherwise, the default of every iteration for the first 3 and then every 20 iterations. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified by CMA-ES.

    """
    if x0 is None:
        x0 = bm.sample()
    model = classes_pints.Model(bm)
    problem = pints.SingleOutputProblem(model, np.arange(0, model.bm.T_MAX, model.bm.TIMESTEP), model.bm.DATA)
    error = pints.RootMeanSquaredError(problem)

    if bm._parameters_bounded:
        if bm._rates_bounded:
            boundaries = classes_pints.AdvancedBoundaries(bm)
        else:
            boundaries = pints.RectangularBoundaries(bm.input_parameter_space(bm.lb), bm.input_parameter_space(bm.ub))
        counter = 1
        while not boundaries.check(x0):
            x0 = bm.sample()
            counter += 1
        if counter > 10:
            print(f'Struggled to find parameters in bounds. Required {counter} iterations.')
        opt = pints.OptimisationController(error, x0, method=pints.CMAES, boundaries=boundaries)
    else:
        opt = pints.OptimisationController(error, x0, method=pints.CMAES)
    opt.optimiser().set_population_size(popSize)
    if debug:
        opt.set_log_interval(iters=1)
    opt.set_max_iterations(maxIter)
    # Run the optimisation
    x, f = opt.run()

    model.bm.evaluate()
    return x


def get_modification(modNum=1):
    """
    modNum = 1 -> Clerx2019
    modNum = 2 -> JedrzejewskiSzmek2018

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Clerx2019.

    """

    if modNum == 1:
        mod = ionbench.modification.Clerx2019()
    elif modNum == 2:
        mod = ionbench.modification.JedrzejewskiSzmek2018()
    else:
        mod = ionbench.modification.Empty(name='cmaes_pints')
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    run(bm, **mod.kwargs)
