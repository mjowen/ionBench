import numpy as np
import ionbench
import ionbench.utils.population_optimisers as pop_opt
import copy
import warnings


def run(bm, x0=None, nGens=1000, popSize=0, debug=False):
    """
    Runs the genetic algorithm from Gurkiewicz et al. 2007. This uses tournament selection (tournament size of 2) and single point crossover. This version of the algorithm, labelled version b, uses gaussian perturbations as the mutation method.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, clamped to bounds if necessary. If x0=None (the default), then the population will be sampled using bm.sample().
    nGens : int, optional
        The number of generations to run the optimisation algorithm for. The default is 1000.
    popSize : int, optional
        The size of the population in each generation. If the popSize is less than twenty times the number of parameters, it will be increased to twenty times the number of parameters. The default is 0.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified.

    """
    cost_func = ionbench.utils.cache.get_cached_cost(bm)

    if popSize < 20 * bm.n_parameters():
        warnings.warn('Too small a value specified for popSize. Gurkiewicz recommends using at least 20 times the number of parameters. popSize will be increased to this value.')
        popSize = 20 * bm.n_parameters()

    pop = pop_opt.get_pop(bm, x0, popSize, cost_func)
    for gen in range(nGens):
        elites = pop_opt.get_elites(pop, 1)
        if debug:
            print("------------")
            print(f'Gen {gen}, Best cost: {elites[0].cost}')

        # Tournament selection
        pop = pop_opt.tournament_selection(pop)

        # One Point Crossover
        pop = pop_opt.one_point_crossover(pop, bm, cost_func)

        # Mutation
        for i in range(popSize):
            for j in range(bm.n_parameters()):
                if np.random.rand() < 0.01:
                    # Normal with variance of 5% of
                    pop[i].x[j] += np.random.normal(scale=0.05 * np.sqrt(np.abs(pop[i].x[j])))

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
    modNum = 1 -> Gurkiewicz2007

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Gurkiewicz2007.

    """
    mod = ionbench.modification.Gurkiewicz2007()
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    run(bm, nGens=10, debug=True, **mod.kwargs)
