# This code was first implemented as a standard nelder mead (Adapted from Scholorpedia http://dx.doi.org/10.4249/scholarpedia.2928) which was then checked against the amoeba algorithm in "Numerical Recipes in C" by Press et al. The resulting Nelder Mead algorithm was verified against scipy nelder mead, then adjusted to reproduce the simulated annealing of "Numerical Recipes in C" by perturbing the costs.

import numpy as np
import ionbench


def run(bm, x0=[], tempInitial=None, N=5, maxIter=1000, debug=False):
    """
    Simulated Annealing by Vanier 1999 uses the algorithm presented in "Numerical Recipes in C" by Press et al. This features a nelder mead optimiser, in which each point in the simplex, in addition to the cost also stored a realisation of a logarithmically distributed random variable. When points are compared, if the point is already in the simplex, this random variable is added to the cost, and if the point is not yet in the simplex (or was added during this step), then it is subtracted from the cost. This ensures that 1) the point which is moved (the worst point in nelder mead) is now random, and 2) there is a non-zero probability to accept a move that increases the cost. As the temperature decreases, the magnitude of this noise also decreases, ensuring the algorithm approaches a standard nelder mead simplex as the number of iterations approaches the maximum number.
    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    x0 : list, optional
        Initial parameter guess. Population is generated by randomly perturbing this initial guess +-50%, then applying the appropriate bounds. If x0=[] (the default), then the population will be sampled uniformly between the bounds.
    tempInitial : float, optional
        Set to 1 in Vanier 1999, but changes with the scale of the cost function/problem. If no value is set, the default, then the cost of x0 is used.
    N : float, optional
        Number of moves per temperature update. Vanier 1999 varies this problem specifically, between 5 and 300. The default is 5.
    maxIter : int, optional
        Maximum number of iterations. Sets the budget which controls how fast the temperature decreases, smaller maxIter means faster decrease in temperature to ensure temperature approaches 0 (although it will terminate before reaching 0). The default is 1000.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters in the final simplex.

    """
    def wrap_around_boundaries(xOld):
        x = np.copy(xOld)
        if not bm.in_bounds(x):
            for i in range(bm.n_parameters()):
                ub = bm.input_parameter_space(bm.ub)
                lb = bm.input_parameter_space(bm.lb)
                step = ub[i] - lb[i]
                while x[i] > ub[i]:
                    x[i] -= step
                while x[i] < lb[i]:
                    x[i] += step
        return x
    # class for points on the simplex

    class Point:
        def __init__(self, x):
            self.x = wrap_around_boundaries(x)
            self.cost = bm.cost(x)
            self.regen_noise()

        def regen_noise(self):
            self.noise = temp * np.log(np.random.rand())

        def tot_cost(self):
            return self.cost + self.noise

    # class for the simplex
    class Simplex:
        def __init__(self, points):
            self.points = points

        def regen_noise(self):
            # Regenerate the random noise for each point in the simplex
            for p in self.points:
                p.regen_noise()

        def get_best(self):
            # returns the best point in the simplex
            x_best = self.points[0]
            for p in self.points:
                if p.tot_cost() < x_best.tot_cost():
                    x_best = p
            return x_best

        def get_worst(self):
            # returns the worst point in the simplex
            x_worst = self.points[0]
            for p in self.points:
                if p.tot_cost() > x_worst.tot_cost():
                    x_worst = p
            return x_worst

        def get_second_worst(self):
            # returns second worst point in the simplex
            x_worst = self.get_worst()
            x_secondWorst = self.points[0]
            for p in self.points:
                if p.tot_cost() > x_secondWorst.tot_cost() and p != x_worst:
                    x_secondWorst = p
            return x_secondWorst

        def centroid(self, x_worst):
            # find the centroid of the simplex by averaging the x positions, not including x_worst. Dont generate a point, cost not needed
            cen = [0] * bm.n_parameters()
            for p in self.points:
                if p != x_worst:
                    cen += p.x
            cen /= len(self.points) - 1
            return wrap_around_boundaries(cen)

        def accept(self, x):
            x_worst = self.get_worst()
            for i in range(len(self.points)):
                if self.points[i] == x_worst:
                    self.points[i] = x
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
            xr = Point(2 * c - x_worst.x)
            xr.noise = -xr.noise
            if xr.tot_cost() < x_secondWorst.tot_cost() and xr.tot_cost() >= x_best.tot_cost():
                if debug:
                    print("Accept reflection")
                self.accept(xr)
                return
            if xr.tot_cost() < x_best.tot_cost():
                # Attempt expand
                xe = Point(2 * xr.x - c)
                xe.noise = -xe.noise
                if xe.tot_cost() < xr.tot_cost():
                    if debug:
                        print("Accept expansion")
                    self.accept(xe)
                else:
                    if debug:
                        print("Ignore expansion. Accept reflection")
                    self.accept(xr)
                return
            if xr.tot_cost() >= x_secondWorst.tot_cost():
                # contract
                if debug:
                    print("Attempt contraction")
                if xr.tot_cost() < x_worst.tot_cost() and xr.tot_cost() >= x_secondWorst.tot_cost():
                    # outside contract
                    xc = Point((xr.x + c) / 2)
                    xc.noise = -xc.noise
                    if xc.tot_cost() <= xr.tot_cost():
                        if debug:
                            print("Accept inside contraction")
                        self.accept(xc)
                        return
                else:
                    # inside contract
                    xc = Point((x_worst.x + c) / 2)
                    xc.noise = -xc.noise
                    if xc.tot_cost() < x_worst.tot_cost():
                        if debug:
                            print("Accept inside contraction")
                        self.accept(xc)
                        return
            # shrink
            if debug:
                print("Shrink")
            for i in range(len(self.points)):
                if self.points[i] != x_best:
                    self.points[i] = Point((x_best.x + self.points[i].x) / 2)
            return

    if len(x0) == 0:
        # sample initial point
        x0 = bm.sample()

    # Initialise the temperature
    if tempInitial is None:
        tempInitial = bm.cost(x0)
    temp = tempInitial

    # Same initialization procedure as scipy or fminseach
    points = [Point(x0)]
    perturbVector = 0.05 * x0
    perturbVector[perturbVector == 0] = 0.00025
    for i in range(bm.n_parameters()):
        perturb = np.zeros(bm.n_parameters())
        perturb[i] = perturbVector[i]
        points.append(Point(x0 + perturb))

    # Build the simplex
    simplex = Simplex(points)
    for i in range(maxIter):
        # Take a modified nelder mead step
        simplex.step()
        # Regenerate the logarithmically distributed noise used in SA modification
        simplex.regen_noise()
        # Annealing schedule
        if i % N == 0:
            temp = tempInitial * (1 - i / maxIter)  # Proportional decrease in temperature

    # Return the best point in the final simplex
    x_best = simplex.get_best().x
    bm.evaluate(x_best)
    return x_best


if __name__ == '__main__':
    bm = ionbench.problems.staircase.HH_Benchmarker()
    x0 = bm.sample()
    x = run(bm, x0=x0, maxIter=1000, debug=False)


def get_modification():
    """

    Returns
    -------
    mod : modification
        The modification used in Vanier1999.

    """
    mod = ionbench.modification.Vanier1999()
    return mod
