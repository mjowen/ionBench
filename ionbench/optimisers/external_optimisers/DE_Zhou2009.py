import numpy as np
import ionbench
import copy
from functools import lru_cache
import scipy.optimize


def run(bm, x0=[], nGens=4000, popSize=None, F=0.5, CR=0.3, debug=False):
    """
    Run differential evolution, as defined by Zhou et al. 2009. This algorithm is based on scheme DE/rand/1 of Storn 1999.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, clamped to bounds if necessary. If x0=[] (the default), then the population will be sampled using bm.sample().
    nGens : int, optional
        The number of generations to run the optimisation algorithm for. The default is 4000.
    popSize : int, optional
        The size of the population in each generation. The default is None, in which case 10 times the number of parameters will be used.
    F : float, optional
        The weight applied to the difference vector. No recommended value is reported by Zhou et al. 2009. The range is [0.5,1.0] is recommended by Storn 1996 (the citation within Zhou et al. 2009). We have arbitrarily chosen 0.5 to be the default value.
    CR : float, optional
        The crossover probability. No recommended value is reported by Zhou et al. 2009. The value of 0.3 is recommended by Storn 1996 (the citation within Zhou et al. 2009), so we use this as the default value.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified.

    """
    class Individual:
        def __init__(self):
            if len(x0) == 0:
                self.x = bm.sample()
            else:
                self.x = bm.input_parameter_space(bm.original_parameter_space(x0) * np.random.uniform(low=0.5, high=1.5, size=bm.n_parameters()))
            self.x = bm.clamp_parameters(self.x)
            self.cost = None

        def find_cost(self):
            self.cost = cost_func(tuple(self.x))

    def get_L():
        # Get the number of parameters to perturb in crossover
        L = 1
        while np.random.rand() < CR and L < bm.n_parameters():
            L += 1
        return L

    @lru_cache(maxsize=None)
    def cost_func(x):
        return bm.cost(x)

    # Ensure popSize is defined
    if popSize is None:
        popSize = 10 * bm.n_parameters()

    # Generate initial population
    pop = [None] * popSize
    for i in range(popSize):
        pop[i] = Individual()
        pop[i].find_cost()

    for gen in range(nGens):
        print('----------------')
        print(f'Generation {gen} of {nGens}')
        if debug:
            costMean = 0
            for p in pop:
                costMean += p.cost / popSize
            print(f'Average cost is {costMean}')
        if gen > 0 and gen % 1000 == 0:
            # Run lm on each point
            if debug:
                print('Running lm on each point')
            for i in range(popSize):
                out = scipy.optimize.least_squares(bm.signed_error, pop[i].x, method='lm', diff_step=1e-3, max_nfev=1000)
                pop[i].x = out.x
                pop[i].cost = out.cost

        for i in range(popSize):
            # Find trial point
            if debug:
                print(f'Working on individual {i}')
                print(pop[i].x)
            possible = list(range(popSize))
            possible.remove(i)
            r1, r2, r3 = np.random.choice(possible, size=3, replace=False)
            if debug:
                print(f'r1: {r1}, r2: {r2}, r3: {r3}')
            trial = Individual()
            nu = pop[r1].x + F * (pop[r2].x - pop[r3].x)
            if debug:
                print('Perturbed point (nu)')
                print(nu)
            # Do crossover
            trial.x = copy.copy(pop[i].x)
            L = get_L()
            n = np.random.choice(range(bm.n_parameters()))
            for j in range(bm.n_parameters()):
                if j == n:
                    for k in range(L):
                        trial.x[(j + k) % bm.n_parameters()] = nu[(j + k) % bm.n_parameters()]
            if debug:
                print(f'Perturbed point after crossover with L {L} and n {n}')
                print(trial.x)
            # Save best out of trial or pop[i]
            trial.find_cost()
            if trial.cost < pop[i].cost:
                if debug:
                    print(f'Point accepted since trail cost is {trial.cost} and ith cost is {pop[i].cost}')
                pop[i] = trial

    # Find best point in final pop
    bestInd = Individual()
    bestInd.cost = np.inf
    for i in range(popSize):
        if pop[i].cost <= bestInd.cost:
            bestInd = pop[i]
    bm.evaluate(bestInd.x)
    return bestInd.x


def get_modification(modNum=1):
    """
    modNum = 1 -> Zhou2009

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Zhou2009.

    """
    mod = ionbench.modification.Zhou2009()
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    run(bm, nGens=5, debug=True, **mod.kwargs)
