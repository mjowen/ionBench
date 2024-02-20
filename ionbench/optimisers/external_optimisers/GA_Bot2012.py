import numpy as np
import ionbench
import copy
from functools import lru_cache

from pymoo.core.individual import Individual as pymooInd
from pymoo.core.problem import Problem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PolynomialMutation
from pymoo.core.population import Population


def run(bm, x0=[], nGens=50, eta_cross=10, eta_mut=20, popSize=50, debug=False):
    """
    Runs the genetic algorithm from Bot et al. 2012.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, clamped to bounds if necessary. If x0=[] (the default), then the population will be sampled using bm.sample().
    nGens : int, optional
        The number of generations to run the optimisation algorithm for. The default is 50.
    eta_cross : float, optional
        Crossover parameter. The default is 10.
    eta_mut : float, optional
        Mutation parameter. The default is 20.
    popSize : int, optional
        The size of the population in each generation. The default is 50.
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

    @lru_cache(maxsize=None)
    def cost_func(x):
        return bm.cost(x)

    pop = [None] * popSize
    for i in range(popSize):
        pop[i] = Individual()
        pop[i].find_cost()

    for gen in range(nGens):
        minCost = np.inf
        for i in range(popSize):
            if pop[i].cost < minCost:
                minCost = pop[i].cost
                elite = copy.deepcopy(pop[i])
        if debug:
            print("------------")
            print(f'Gen {gen}, Best cost: {minCost}')
        # Tournament selection
        newPop = []
        for j in range(2):
            perm = np.random.permutation(popSize)
            for i in range(popSize // 2):
                if pop[perm[2 * i]].cost < pop[perm[2 * i + 1]].cost:
                    newPop.append(copy.deepcopy(pop[perm[2 * i]]))
                else:
                    newPop.append(copy.deepcopy(pop[perm[2 * i + 1]]))
        pop = newPop  # Population of parents
        # Crossover SBX
        newPop = []
        problem = Problem(n_var=bm.n_parameters(), xl=bm.input_parameter_space(bm.lb), xu=bm.input_parameter_space(bm.ub))
        for i in range(popSize // 2):
            a, b = pymooInd(X=np.array(pop[2 * i].x)), pymooInd(X=np.array(pop[2 * i + 1].x))

            parents = [[a, b]]
            off = SBX(prob=0.9, prob_var=0.5, eta=eta_cross).do(problem, parents)
            Xp = off.get("X")
            newPop.append(Individual())
            newPop[-1].x = Xp[0]
            newPop.append(Individual())
            newPop[-1].x = Xp[1]
        pop = newPop
        # Mutation
        mutation = PolynomialMutation(prob=1, prob_var=0.1, eta=eta_mut)
        for i in range(popSize):
            ind = Population.new(X=[pop[i].x])
            off = mutation(problem, ind)
            pop[i].x = off.get("X")[0]
        if debug:
            print(f'Finishing gen {gen}')
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
    modNum = 1 -> Bot2012
    modNum = 2 -> Groenendaal2015

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Bot2012.

    """

    if modNum == 1:
        mod = ionbench.modification.Bot2012()
    elif modNum == 2:
        mod = ionbench.modification.Groenendaal2015()
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    run(bm, debug=True, **mod.kwargs)
