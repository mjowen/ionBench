"""
This module contains the PSO optimiser from Cabo 2022.
Little information on the algorithm is given in the paper but the code that was used is provided at https://github.com/kkentzo/pso
The code provides many options for the algorithm, which are not described in the paper. We use the defaults, also stated here.
There is a choice of topologies for determining the global acceleration term, in which case we use the ring topology (PSO_NHOOD_RING)
There is a choice of inertia weights, either linearly decreasing (user specified limits) or constant (0.7298). We use linearly decreasing from 0.7298 to 0.3 over maxIter iterations.
We use the internally calculated population size formula.
We assume the coefficients c1 and c2 are maintained at their defaults (1.496).
We assume the particle positions are clamped to the bounds.
The initial position sampling described would ignore the point x0 so cannot be used in ionBench. We use the ionBench default instead.
The initial velocity sampling can be used.
"""
import numpy as np
import ionbench
import copy


# noinspection PyShadowingNames
def run(bm, x0=None, maxIter=1000, debug=False):
    """
    Runs the PSO algorithm defined by Cabo 2022.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, then applying the appropriate bounds. If x0=None (the default), then the population will be sampled uniformly between the bounds.
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

    cost_func = ionbench.utils.cache.get_cached_cost(bm)

    # noinspection PyShadowingNames
    class Particle(ionbench.utils.particle_optimisers.Particle):
        def __init__(self):
            self.x0 = x0
            super().__init__(bm, cost_func, x0)

        def set_velocity(self):
            """
            The velocity algorithm used by Cabo 2022 takes two sampled positions. Sets the particle position to one of them, set the velocity to point away from the other.
            """
            copied_position = np.copy(self.position)
            self.set_position(self.x0)
            self.velocity = (self.position - copied_position) / 2
            # Reset position
            self.position = copied_position

        def clamp(self):
            """
            Clamp parameters to the input parameter space. Also sets the velocity to 0 in any clamped parameters.
            """
            for i in range(len(self.position)):
                if self.position[i] < 0:
                    self.position[i] = 0
                    self.velocity[i] = 0
                elif self.position[i] > 1:
                    self.position[i] = 1
                    self.velocity[i] = 0

    # noinspection PyShadowingNames
    def best_in_ring(particleList):
        """
        Finds the best cost and position in the ring topology for each particle. Returns the positions of the best neighbouring particle that each particle can see.

        Parameters
        ----------
        particleList : list
            List of particles.

        Returns
        -------
        ringPos : list
            List of positions of the best neighbouring particle that each particle can see.
        """
        costs = [p.bestCost for p in particleList]
        ringPos = [p.bestPosition for p in particleList]
        ringCosts = copy.copy(costs)
        for i in range(len(particleList)):
            costLow = costs[(i - 1) % len(particleList)]
            costHigh = costs[(i + 1) % len(particleList)]
            if costLow < ringCosts[i]:
                ringCosts[i] = costLow
                ringPos[i] = particleList[(i - 1) % len(particleList)].bestPosition
            if costHigh < ringCosts[i]:
                ringCosts[i] = costHigh
                ringPos[i] = particleList[(i + 1) % len(particleList)].bestPosition
        return ringPos

    # Set population size n
    n = int(10 + 2 * np.sqrt(bm.n_parameters()))
    # Initial population
    particleList = [Particle() for _ in range(n)]

    Gcost = [np.inf] * maxIter  # Best cost ever
    Gpos = [None] * maxIter  # Position of best cost ever
    L = None
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
            p.set_cost()
            if p.currentCost < Gcost[L]:
                Gcost[L] = p.currentCost
                Gpos[L] = np.copy(p.position)

        # Renew velocities
        c1 = 1.496
        c2 = 1.496
        if L < 1000:  # Dependence of w on maxIter has been removed
            w = 0.7298 - (0.7298-0.3)*L/1000
        else:
            w = 0.3
        ringPos = best_in_ring(particleList)
        for i, p in enumerate(particleList):
            localAcc = c1 * np.random.rand() * (p.bestPosition - p.position)
            globalAcc = c2 * np.random.rand() * (ringPos[i] - p.position)
            p.velocity = w * p.velocity + localAcc + globalAcc
        if debug:
            print("Velocities renewed")
        # Move positions
        for p in particleList:
            p.position += p.velocity
            p.clamp()

        if debug:
            print("Positions renewed")
            print(f'Finished population {L}')
            print(f'Best cost so far: {Gcost[L]}')
            print(f'Found at position: {Gpos[L]}')

        if bm.is_converged():
            break

    bm.evaluate()
    return Particle().untransform(Gpos[L])


# noinspection PyUnusedLocal,PyShadowingNames
def get_modification(modNum=1):
    """
    modNum = 1 -> Cabo2022

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Cabo2022.

    """
    mod = ionbench.modification.Cabo2022()
    return mod
