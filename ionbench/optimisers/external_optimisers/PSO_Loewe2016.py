"""
The module provides the PSO algorithm given by Loewe et al. 2016.
The particles are clamped differently to other PSO algorithms.
No initial position or velocity sampling given, so we assume ionBench defaults.
"""
import numpy as np
import ionbench
import warnings


# noinspection PyShadowingNames
def run(bm, x0=None, n=96, maxIter=1000, phi1=2.05, phi2=2.05, debug=False):
    """
    Runs the particle swarm optimisation from Loewe et al. 2016. If the benchmarker is bounded, the solver will search in the interval [lb,ub], otherwise the solver will search in the interval [0,2*default].

    Notes on using this optimiser:
        It is unclear the specifics of the optimisation used in Loewe et al. 2016. It does not describe the method for sampling the initial positions or velocities of the particles (we use uniform distribution between bounds for position and expect Loewe et al. 2016 did similarly, and zeros for the initial velocities, waiting for them to be set by TRR). The initial velocities may be different to those used in the Loewe et al. 2016.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, then applying the appropriate bounds. If x0=None (the default), then the population will be sampled uniformly between the bounds.
    n : int, optional
        Number of particles. The default is 96.
    maxIter : int, optional
        Maximum number of iterations. The default is 1000.
    phi1 : float, optional
        Scale of the acceleration towards a particle's best positions. The default is 2.05.
    phi2 : float, optional
        Scale of the acceleration towards the best point seen across all particles. The default is 2.05.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified.

    """
    if not bm.parametersBounded:
        raise RuntimeError('This optimiser requires bounds.')

    if x0 is None:
        x0 = bm.sample()

    signed_error = ionbench.utils.cache.get_cached_signed_error(bm)

    def cost_func(x):
        """
        Cost function needs to use the signed_error function so that they use the same cache.
        """
        return bm.rmse(signed_error(x) + bm.DATA, bm.DATA)

    # noinspection PyShadowingNames
    class Particle(ionbench.utils.particle_optimisers.Particle):
        def __init__(self):
            super().__init__(bm, cost_func, x0)

        def clamp(self):
            """
            Clamp parameters to the input parameter space.
            """
            for i in range(bm.n_parameters()):
                if self.position[i] < 0:  # pragma: no cover
                    self.position[i] = np.random.rand() / 4
                elif self.position[i] > 1:  # pragma: no cover
                    self.position[i] = np.random.rand() / 4

    L = None

    if (phi1 + phi2) ** 2 - 4 * (phi1 + phi2) < 0:
        warnings.warn(
            "Invalid constriction factor using specified values for phi1 and phi2. Using defaults of phi1=phi2=2.05 instead.")
        phi1 = 2.05
        phi2 = 2.05
    phi = phi1 + phi2
    constFactor = 2 / (phi - 2 + np.sqrt(phi ** 2 - 4 * phi))

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

        # Find best positions, both globally and locally
        for p in particleList:
            p.set_cost()
            if p.currentCost < Gcost[L]:
                Gcost[L] = p.currentCost
                Gpos[L] = np.copy(p.position)

        # Update velocities
        for p in particleList:
            # Update velocity
            localAcc = phi1 * np.random.rand() * (p.bestPosition - p.position)
            globalAcc = phi2 * np.random.rand() * (Gpos[L] - p.position)
            p.velocity = constFactor * (p.velocity + localAcc + globalAcc)

            # Move particle
            p.position += p.velocity

            # Clamp
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
    modNum = 1 -> Loewe2016

    Returns
    -------
    mod : modification
        Modification corresponding to inputted modNum. Default is modNum = 1, so Loewe2016.

    """
    mod = ionbench.modification.Loewe2016()
    return mod
