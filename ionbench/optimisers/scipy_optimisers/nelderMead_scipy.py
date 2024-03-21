import ionbench.problems.staircase
import scipy.optimize
import numpy as np


# noinspection PyShadowingNames
def run(bm, x0=None, xtol=1e-4, ftol=1e-4, maxIter=1000, maxfev=20000, debug=False):
    """
    Runs Nelder-Mead optimiser from Scipy. Bounds are automatically loaded from the benchmarker if present.

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
        Maximum number of iterations of Nelder-Mead to use. The default is 1000.
    maxfev : int, optional
        Maximum number of cost function evaluations. The default is 20000.
    debug : bool, optional
        If True, prints out the cost and parameters found by the algorithm. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified by Nelder-Mead.
    """
    cost = ionbench.utils.cache.get_cached_cost(bm)

    if x0 is None:
        x0 = bm.sample()
        if debug:
            print('Sampling x0')
            print(x0)

    if bm.parametersBounded:
        lb = list(bm.input_parameter_space(bm.lb))
        ub = list(bm.input_parameter_space(bm.ub))
        bounds = []
        for i in range(bm.n_parameters()):
            if lb[i] == np.inf or lb[i] == np.nan:
                lb[i] = None
            if ub[i] == np.inf or ub[i] == np.nan:
                ub[i] = None
            bounds.append((lb[i], ub[i]))
        if debug:
            print('Bounds transformed')
            print('Old Bounds:')
            print(bm.lb)
            print(bm.ub)
            print('New bounds')
            print(bounds)
        out = scipy.optimize.minimize(cost, x0, method='nelder-mead', options={'disp': debug, 'xatol': xtol, 'fatol': ftol, 'maxiter': maxIter, 'maxfev': maxfev}, bounds=bounds)
    else:
        out = scipy.optimize.minimize(cost, x0, method='nelder-mead', options={'disp': debug, 'xatol': xtol, 'fatol': ftol, 'maxiter': maxIter, 'maxfev': maxfev})

    if debug:
        print(f'Cost of {out.fun} found at:')
        print(out.x)

    bm.evaluate()
    return out.x


# noinspection PyShadowingNames
def get_modification(modNum=1):
    """
    modNum = 1 -> Balser1990
    modNum = 2 -> Davies2011
    modNum = 4 -> Moreno2016

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Balser1990.

    """

    if modNum == 1:
        mod = ionbench.modification.Balser1990()
    elif modNum == 2:
        mod = ionbench.modification.Davies2011()
    elif modNum == 3:
        mod = ionbench.modification.Moreno2016()
    else:
        mod = ionbench.modification.Empty(name='nelderMead_scipy')
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    run(bm, debug=True, **mod.kwargs)
