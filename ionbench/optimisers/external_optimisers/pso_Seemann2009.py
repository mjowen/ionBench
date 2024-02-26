import numpy as np
import ionbench


def run(bm, x0=None, n=20, maxIter=1000, gmin=0.05, debug=False):
    """
    Runs the PSO algorithm defined by Seemann et al. 2022.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, clamped to bounds if necessary. If x0=None (the default), then the population will be sampled uniformly between the bounds.
    n : int, optional
        Number of particles. The default is 20.
    maxIter : int, optional
        Maximum number of iterations. The default is 1000.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified.

    """
    if x0 is None:
        x0 = bm.sample()

    class Particle:
        def __init__(self):
            self.position = bm.input_parameter_space(bm.original_parameter_space(x0) * np.random.uniform(low=0.5, high=1.5, size=bm.n_parameters()))
            self.position = bm.clamp_parameters(self.position)
            self.velocity = 0.1 * np.random.rand(bm.n_parameters()) * self.position
            self.bestCost = np.inf  # Best cost of this particle
            self.bestPosition = np.copy(self.position)  # Position of best cost for this particle
            self.currentCost = None

        def set_cost(self, cost):
            self.currentCost = cost
            if cost < self.bestCost:
                self.bestCost = cost
                self.bestPosition = np.copy(self.position)

    def cost_func(x):
        return bm.cost(x)

    particleList = []
    for i in range(n):
        particleList.append(Particle())

    Gcost = [np.inf] * maxIter  # Best cost ever
    Gpos = [None] * maxIter  # Position of best cost ever
    for L in range(maxIter):
        if L > 0:
            Gcost[L] = Gcost[L - 1]
            Gpos[L] = Gpos[L - 1]

        if debug:
            print('-------------')
            print(f'Beginning population: {L}')
            print(f'Best cost so far: {Gcost[L]}')
            print(f'Found at position: {Gpos[L]}')

        for p in particleList:
            cost = cost_func(p.position)
            p.set_cost(cost)
            if cost < Gcost[L]:
                Gcost[L] = cost
                Gpos[L] = np.copy(p.position)

        if Gcost[L] < gmin:
            print("Cost successfully minimised")
            print(f'Final cost of {Gcost[L]} found at:')
            print(Gpos[L])
            break

        # Renew velocities
        c1 = 0.5 + L / maxIter * 2
        c2 = 2.5 - c1
        w = np.random.uniform(0.5, 1)
        for p in particleList:
            localAcc = c1 * np.random.rand() * (p.bestPosition - p.position)
            globalAcc = c2 * np.random.rand() * (Gpos[L] - p.position)
            p.velocity = w * p.velocity + localAcc + globalAcc
        if debug:
            print("Velocities renewed")
        # Move positions
        for p in particleList:
            p.position += p.velocity

        if debug:
            print("Positions renewed")
            print(f'Finished population {L}')
            print(f'Best cost so far: {Gcost[L]}')
            print(f'Found at position: {Gpos[L]}')

    bm.evaluate()
    return Gpos[L]


def get_modification(modNum=1):
    """
    modNum = 1 -> Seemann2009

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Seemann2009.

    """
    mod = ionbench.modification.Seemann2009()
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH()
    mod = get_modification()
    mod.apply(bm)
    bm._useScaleFactors = True
    run(bm, maxIter=5, debug=True, **mod.kwargs)
