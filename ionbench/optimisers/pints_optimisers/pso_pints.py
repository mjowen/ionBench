import pints
from ionbench.problems import staircase
import numpy as np
from ionbench.optimisers.pints_optimisers import classes_pints

def run(bm, x0 = [], maxIter=1000):
    """
    Runs PSO (Particle Swarm Optimisation) from Pints using a benchmarker. 

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter vector from which to start optimisation. Default is [], in which case a randomly sampled parameter vector is retrieved from bm.sample().
    maxIter : int, optional
        Number of iterations of PSO to run. The default is 1000.

    Returns
    -------
    xbest : list
        The best parameters identified by PSO.

    """
    if x0 == []:
        x0 = bm.sample()
    model = classes_pints.Model(bm)
    problem = pints.SingleOutputProblem(model, np.arange(model.bm.tmax), model.bm.data)
    error = pints.RootMeanSquaredError(problem)
    
    # Create an optimisation controller
    opt = pints.OptimisationController(error, x0, method=pints.PSO)
    opt.set_max_iterations(maxIter)
    # Run the optimisation
    x, f = opt.run()
    
    model.bm.evaluate(x)
    return x

if __name__ == '__main__':
    bm = staircase.HH_Benchmarker()
    bm.log_transform([True, False]*4+[False])
    run(bm)