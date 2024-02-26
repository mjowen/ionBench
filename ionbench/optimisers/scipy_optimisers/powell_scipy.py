import ionbench.problems.staircase
import scipy.optimize
import numpy as np
from functools import lru_cache


def run(bm, x0=None, xtol=1e-4, ftol=1e-4, maxIter=1000, maxfev=20000, debug=False):
    """
    Runs Powell's Simplex optimiser from Scipy. Bounds are automatically loaded from the benchmarker if present.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter vector from which to start optimisation. Default is None, in which case a randomly sampled parameter vector is retrieved from bm.sample().
    xtol : float, optional
        Tolerance in parameters. Used as a termination criterion. The default is 1e-4.
    ftol : float, optional
        Tolerance in cost. Used as a termination criterion. The default is 1e-4.
    maxIter : int, optional
        Maximum number of iterations of Powell's Simplex to use. The default is 1000.
    maxfev : int, optional
        Maximum number of cost function evaluations. The default is 20000.
    debug : bool, optional
        If True, prints out the cost and parameters found by the algorithm. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified by Powell's Simplex.
    """
    @lru_cache(maxsize=None)
    def cost(p):
        """
        Return the cost of the parameters. Cached so that the cost function is only evaluated once for each set of parameters. Requires inputs to be hashable (for example tuple).
        """
        return bm.cost(p)

    def cost_scipy(p):
        """
        Wrapper for the cached cost function. This is required as the scipy optimiser requires a function that won't supply a hashable type as input.
        """
        return cost(tuple(p))

    if x0 is None:
        x0 = bm.sample()
        if debug:
            print('Sampling x0')
            print(x0)

    if bm._parameters_bounded:
        lb = bm.input_parameter_space(bm.lb)
        ub = bm.input_parameter_space(bm.ub)
        bounds = []
        for i in range(bm.n_parameters()):
            if lb[i] == np.inf:
                lb[i] = None
            if ub[i] == np.inf:
                ub[i] = None
            bounds.append((lb[i], ub[i]))
        if debug:
            print('Bounds transformed')
            print('Old Bounds:')
            print(bm.lb)
            print(bm.ub)
            print('New bounds')
            print(bounds)
        out = scipy.optimize.minimize(cost_scipy, x0, method='powell', options={'disp': debug, 'xtol': xtol, 'ftol': ftol, 'maxiter': maxIter, 'maxfev': maxfev}, bounds=bounds)
    else:
        out = scipy.optimize.minimize(cost_scipy, x0, method='powell', options={'disp': debug, 'xtol': xtol, 'ftol': ftol, 'maxiter': maxIter, 'maxfev': maxfev})

    if debug:
        print(f'Cost of {out.fun} found at:')
        print(out.x)

    bm.evaluate()
    return out.x


def get_modification(modNum=1):
    """
    modNum = 1 -> Sachse2003
    modNum = 2 -> Seemann2009
    modNum = 3 -> Wilhelms2012a

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Sachse2003.

    """

    if modNum == 1:
        mod = ionbench.modification.Sachse2003()
    elif modNum == 2:
        mod = ionbench.modification.Seemann2009()
    elif modNum == 3:
        mod = ionbench.modification.Wilhelms2012a()
    else:
        mod = ionbench.modification.Empty(name='powell_scipy')
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    run(bm, debug=True, **mod.kwargs)
