import numpy as np
import ionbench
import copy
import warnings
from functools import lru_cache

from pymoo.core.individual import Individual
from pymoo.core.problem import Problem
from pymoo.operators.crossover.pntx import SinglePointCrossover


def run(bm, x0=[], nGens=1000, popSize=0, debug=False):
    """
    Runs the genetic algorithm from Gurkiewicz et al 2007. This uses tournement selection (tournement size of 2) and single point crossover. This version of the algorithm, labelled version b, uses gaussian perturbations as the mutation method.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%. If x0=[] (the default), then the population will be sampled using bm.sample().
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
    class individual():
        def __init__(self):
            if len(x0) == 0:
                self.x = bm.sample()
            else:
                self.x = x0 * np.random.uniform(low=0.5, high=1.5, size=bm.n_parameters())
            self.cost = None

        def find_cost(self):
            self.cost = cost_func(tuple(self.x))

    @lru_cache(maxsize=None)
    def cost_func(x):
        return bm.cost(x)

    if popSize < 20 * bm.n_parameters():
        warnings.warn('Too small a value specified for popSize. Gurkiewicz recommends using at least 20 times the number of parameters. popSize will be increased to this value.')
        popSize = 20 * bm.n_parameters()

    pop = [None] * popSize
    for i in range(popSize):
        pop[i] = individual()
        pop[i].find_cost()

    for gen in range(nGens):
        minCost = np.inf
        for i in range(popSize):
            if pop[i].cost < minCost:
                minCost = pop[i].cost
                elite = copy.deepcopy(pop[i])
        if debug:
            print("------------")
            print("Gen " + str(gen))
            print("Best cost: " + str(minCost))
        # Tournement selection
        newPop = []
        for j in range(2):
            perm = np.random.permutation(popSize)
            for i in range(popSize // 2):
                if pop[perm[2 * i]].cost > pop[perm[2 * i + 1]].cost:
                    newPop.append(copy.deepcopy(pop[perm[2 * i]]))
                else:
                    newPop.append(copy.deepcopy(pop[perm[2 * i + 1]]))
        pop = newPop  # Population of parents
        # One Point Crossover
        newPop = []
        problem = Problem(n_var=bm.n_parameters(), xl=0.0, xu=2.0)
        for i in range(popSize // 2):
            a, b = Individual(X=np.array(pop[2 * i].x)), Individual(X=np.array(pop[2 * i + 1].x))

            parents = [[a, b]]
            off = SinglePointCrossover(prob=0.5).do(problem, parents)
            Xp = off.get("X")
            newPop.append(individual())
            newPop[-1].x = Xp[0]
            newPop.append(individual())
            newPop[-1].x = Xp[1]
        pop = newPop

        # Mutation
        for i in range(popSize):
            for j in range(bm.n_parameters()):
                if np.random.rand() < 0.01:
                    # Normal with variance of 5% of
                    pop[i].x[j] += np.random.normal(scale=0.05 * np.sqrt(np.abs(pop[i].x[j])))

        if debug:
            print("Finishing gen " + str(gen))
        # Find costs
        for i in range(popSize):
            pop[i].find_cost()
        # Elitism
        maxCost = -np.inf
        for i in range(popSize):
            if pop[i].cost > maxCost:
                maxCost = pop[i].cost
                maxIndex = i
        pop[maxIndex] = copy.deepcopy(elite)

    minCost = np.inf
    for i in range(popSize):
        if pop[i].cost < minCost:
            minCost = pop[i].cost
            elite = pop[i]
    bm.evaluate(elite.x)
    return elite.x


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
    bm = ionbench.problems.staircase.HH_Benchmarker()
    mod = get_modification()
    mod.apply(bm)
    run(bm, nGens=10, debug=True)
