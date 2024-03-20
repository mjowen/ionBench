import numpy as np
import scipy
import ionbench
import ionbench.utils.population_optimisers as pop_opt
import copy
from functools import lru_cache


# TODO: eta_mut is unused - needs fixing
def run(bm, x0=None, nGens=50, eta_cross=10, eta_mut=20, elitePercentage=0.066, popSize=50, debug=False):
    """
    Runs the genetic algorithm from Smirnov et al. 2020.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, clamped to bounds if necessary. If x0=None (the default), then the population will be sampled using bm.sample().
    nGens : int, optional
        The number of generations to run the optimisation algorithm for. The default is 50.
    eta_cross : float, optional
        Crossover parameter. The default is 10.
    eta_mut : float, optional
        Mutation parameter. The default is 20.
    elitePercentage : float, optional
        The percentage of the population that are considered elites to move into the next generation. This will be multiplied by popSize and then rounded to the nearest integer. The default is 0.066.
    popSize : int, optional
        The size of the population in each generation. The default is 50.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified.

    """
    @lru_cache(maxsize=None)
    def cost_func(x):
        return bm.cost(x)

    eliteCount = int(np.round(popSize * elitePercentage))
    pop = pop_opt.get_pop(bm, x0, popSize, cost_func)

    for gen in range(nGens):
        elites = pop_opt.get_elites(pop, eliteCount)
        if debug:
            print("------------")
            print(f'Gen {gen}, Best cost: {elites[0].cost}')

        # Tournament selection
        pop = pop_opt.tournament_selection(pop)

        # Crossover SBX
        pop = pop_opt.sbx_crossover(pop, bm, cost_func, eta_cross)

        # Mutation
        for i in range(popSize):
            if np.random.rand() < 0.9:
                direc = np.random.rand(bm.n_parameters())
                direc = direc / np.linalg.norm(direc)
                mag = scipy.stats.cauchy.rvs(loc=0, scale=0.18)
                pop[i].x += mag * direc

        if debug:
            print(f'Finishing gen {gen}')

        # Find costs
        pop = pop_opt.find_pop_costs(pop)

        # Elitism
        pop = pop_opt.set_elites(pop, elites)

        if bm.is_converged():
            break

    elites = pop_opt.get_elites(pop, 1)
    bm.evaluate()
    return elites[0].x


# noinspection PyUnusedLocal
def get_modification(modNum=1):
    """
    modNum = 1 -> Smirnov2020

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Smirnov2020.

    """
    mod = ionbench.modification.Smirnov2020()
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    run(bm, debug=True, **mod.kwargs)
