import numpy as np
import ionbench
from functools import lru_cache
# Velocity of new points from NM is undefined. New particles from NM (either accepting or shrinking) maintain their old locally best position and previous velocity. We dont update the velocity of particles which underwent a NM step


def run(bm, x0=[], maxIter=1000, gmin=0.05, debug=False):
    """
    Run the hybrid Nelder-Mead and PSO optimiser from Liu et al 2011.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, clamped to bounds if necessary. If x0=[] (the default), then the population will be sampled uniformly between the bounds.
    maxIter : int, optional
        Maximum number of iterations. The default is 1000.
    gmin : float, optional
        Cost termination criteria. Once a cost below gmin is found then optimisation will terminate. The default is 0.05.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified.

    """
    if len(x0) == 0:
        x0 = bm.sample()

    class Particle:
        def __init__(self, position=None):
            if position is None:
                self.position = bm.input_parameter_space(bm.original_parameter_space(x0) * np.random.uniform(low=0.5, high=1.5, size=bm.n_parameters()))
            else:
                self.position = position
            self.position = bm.clamp(self.position)
            self.velocity = 0.1 * np.random.rand(bm.n_parameters()) * self.position
            self.bestCost = np.inf  # Best cost of this particle
            self.bestPosition = np.copy(self.position)  # Position of best cost for this particle
            self.currentCost = None

        def set_cost(self, cost):
            self.currentCost = cost
            if cost < self.bestCost:
                self.bestCost = cost
                self.bestPosition = np.copy(self.position)

    # class for the simplex
    class Simplex:
        def __init__(self, particles):
            self.particles = particles

        def get_best(self):
            # returns the best point in the simplex
            x_best = self.particles[0]
            for p in self.particles:
                if p.currentCost < x_best.currentCost:
                    x_best = p
            return x_best

        def get_worst(self):
            # returns the worst point in the simplex
            x_worst = self.particles[0]
            for p in self.particles:
                if p.currentCost > x_worst.currentCost:
                    x_worst = p
            return x_worst

        def get_second_worst(self):
            # returns second worst point in the simplex
            x_worst = self.get_worst()
            x_secondWorst = self.particles[0]
            for p in self.particles:
                if p.currentCost > x_secondWorst.currentCost and p != x_worst:
                    x_secondWorst = p
            return x_secondWorst

        def centroid(self, x_worst):
            # find the centroid of the simplex by averaging the positions, not including x_worst. Dont generate a point, cost not needed
            cen = [0] * bm.n_parameters()
            for p in self.particles:
                if p != x_worst:
                    cen += p.position
            cen /= len(self.particles) - 1
            return cen

        def accept(self, x):
            x_worst = self.get_worst()
            for i in range(len(self.particles)):
                if self.particles[i] == x_worst:
                    self.particles[i].position = x.position
                    self.particles[i].set_cost(x.currentCost)
                    return

        def step(self):
            """
            Take a modified nelder mead step with acceptance probability related to the current temperature.
            """
            x_worst = self.get_worst()
            x_best = self.get_best()
            x_secondWorst = self.get_second_worst()
            c = self.centroid(x_worst)
            # attempt reflection
            xr = Particle(position=2 * c - x_worst.position)
            xr.set_cost(cost_func(tuple(xr.position)))
            if xr.currentCost < x_secondWorst.currentCost and xr.currentCost >= x_best.currentCost:
                if debug:
                    print("Accept reflection")
                self.accept(xr)
                return
            if xr.currentCost < x_best.currentCost:
                # Attempt expand
                xe = Particle(position=2 * xr.position - c)
                xe.set_cost(cost_func(tuple(xe.position)))
                if xe.currentCost < xr.currentCost:
                    if debug:
                        print("Accept expansion")
                    self.accept(xe)
                else:
                    if debug:
                        print("Ignore expansion. Accept reflection")
                    self.accept(xr)
                return
            if xr.currentCost >= x_secondWorst.currentCost:
                # contract
                if debug:
                    print("Attempt contraction")
                if xr.currentCost < x_worst.currentCost and xr.currentCost >= x_secondWorst.currentCost:
                    # outside contract
                    xc = Particle(position=(xr.position + c) / 2)
                    xc.set_cost(cost_func(tuple(xc.position)))
                    if xc.currentCost <= xr.currentCost:
                        if debug:
                            print("Accept inside contraction")
                        self.accept(xc)
                        return
                else:
                    # inside contract
                    xc = Particle(position=(x_worst.position + c) / 2)
                    xc.set_cost(cost_func(tuple(xc.position)))
                    if xc.currentCost < x_worst.currentCost:
                        if debug:
                            print("Accept inside contraction")
                        self.accept(xc)
                        return
            # shrink
            if debug:
                print("Shrink")
            for i in range(len(self.particles)):
                if self.particles[i] != x_best:
                    self.particles[i].position = (x_best.position + self.particles[i].position) / 2
                    self.particles[i].set_cost(cost_func(tuple(self.particles[i].position)))
            return

    @lru_cache(maxsize=None)
    def cost_func(x):
        return bm.cost(x)

    lb = bm.input_parameter_space(bm.lb)
    ub = bm.input_parameter_space(bm.ub)

    # Set population size n
    n = 3 * bm.n_parameters() + 1
    # Initial population
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
            print(f'Begginning population: {L}')
            print(f'Best cost so far: {Gcost[L]}')
            print(f'Found at position: {Gpos[L]}')

        for p in particleList:
            cost = cost_func(tuple(p.position))
            p.set_cost(cost)
            if cost < Gcost[L]:
                Gcost[L] = cost
                Gpos[L] = np.copy(p.position)

        if Gcost[L] < gmin:
            print("Cost successfully minimised")
            print(f'Final cost of {Gcost[L]} found at:')
            print(Gpos[L])
            break

        # Sort particle list by cost
        costs = [p.currentCost for p in particleList]
        particleList = [p for _, p in sorted(zip(costs, particleList), key=lambda pair: pair[0])]

        # Build simplex and take 1 step
        s = Simplex(particleList[:bm.n_parameters() + 1])
        s.step()
        particleList[:bm.n_parameters() + 1] = s.particles

        # Renew velocities
        c1 = 1.496  # Assume they used the fixed value
        c2 = 1.496  # Assume they used the fixed value
        for p in particleList[bm.n_parameters() + 1:]:
            localAcc = c1 * np.random.rand() * (p.bestPosition - p.position)
            globalAcc = c2 * np.random.rand() * (Gpos[L] - p.position)
            p.velocity = p.velocity + localAcc + globalAcc
        if debug:
            print("Velocities renewed")
        # Move positions
        for p in particleList[bm.n_parameters() + 1:]:
            p.position += p.velocity
            # Enfore bounds by clamping
            if not bm.in_bounds(bm.original_parameter_space(p.position)):
                for i in range(bm.n_parameters()):
                    if p.position[i] > ub[i]:
                        p.position[i] = ub[i]
                        p.velocity[i] = 0
                    elif p.position[i] < lb[i]:
                        p.position[i] = lb[i]
                        p.velocity[i] = 0

        if debug:
            print("Positions renewed")
            print(f'Finished population {L}')
            print(f'Best cost so far: {Gcost[L]}')
            print(f'Found at position: {Gpos[L]}')

    # If terminated by max iter, simplex or pso may have found a new best point
    for p in particleList:
        cost = cost_func(tuple(p.position))
        p.set_cost(cost)
        if cost < Gcost[L]:
            Gcost[L] = cost
            Gpos[L] = np.copy(p.position)

    bm.evaluate(Gpos[L])
    return Gpos[L]


def get_modification(modNum=1):
    """
    modNum = 1 -> Liu2011

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Liu2011.

    """
    mod = ionbench.modification.Liu2011()
    return mod


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH_Benchmarker()
    mod = get_modification()
    mod.apply(bm)
    run(bm, maxIter=50, gmin=0.01, debug=True, **mod.kwargs)
