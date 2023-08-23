from ionbench.problems import staircase
from functools import cache
import numpy as np

def run(bm, CrtStp = 2e-5, Stp = 1/100, RedFct = 1/4, maxfev = 100000, debug = False):
    """
    Runs the pattern search algorithm from Kohjitani et al 2022.

    Parameters
    ----------
    bm : Benchmarker
        A benchmarker to evaluate the performance of the optimisation algorithm.
    CrtStp : float, optional
        The minimum step size. If there are no improvements within CrtStp, the optimisation terminates. The default is 2e-5.
    Stp : float, optional
        Initial step size. The default is 1/100.
    RedFct : float, optional
        The reduction factor. If the center point is better than its neighbours, the step size is scaled by this reduction factor. The default is 1/4.
    maxfev : int, optional
        Maximum number of cost function evaluations. The default is 100000.
    debug : bool, optional
        If True, debug information will be printed, reporting that status of the optimisation each generation. The default is False.

    Returns
    -------
    xbest : list
        The best parameters identified.

    """
    @cache
    def cost_func(x):
        return bm.cost(x)
    
    funcCounter = 0
    def explore(BP, Stp):
        foundImprovement = False
        NP = np.copy(BP)
        MSE = cost_func(tuple(BP)) #No real computation cost from this thanks to the cache
        for i in range(bm.n_parameters()): 
            home = BP[i]
            NP[i] = home + Stp#Positive Step
            MSEp = cost_func(tuple(NP))#Positive MSE
            NP[i] = home - Stp#Negative Step
            MSEn = cost_func(tuple(NP))#Negative MSE
            minMSE = min(MSEp, MSEn)#MSE in best direction (postive or negative Stp)
            if minMSE < MSE: #If improvement found
                if MSEp < MSEn: #If positive step is better
                    NP[i] = home + Stp#Take positive step
                else:#If negative step is better
                    NP[i] = home - Stp#Take negative step
                MSE = minMSE#Either way, record new MSE
                foundImprovement = True
            else:#If no improvement
                NP[i] = home#Restore center point
        return foundImprovement, NP

    BP = bm.sample() #Set initial base point
    funcCounter += 1
    while Stp > CrtStp: #Stop when step size is sufficiently small
        #Explore neighbouring points
        if debug:
            print("------------")
            print("Current step size:"+str(Stp))
            print("Cost: "+str(cost_func(tuple(BP))))
        improvementFound, NP = explore(BP, Stp) #Explore neighbouring points
        funcCounter += 4
        while improvementFound:
            if debug:
                print("Improvement Found? "+str(improvementFound))
            BP = np.copy(NP) #Move to new improved point
            improvementFound, NP = explore(BP, Stp) #Explore neighbouring points
            funcCounter += 4
            if funcCounter > maxfev:
                print("Exceeded maximum number of function evaluations.")
                bm.evaluate(NP)
                return NP
        
        Stp = Stp * RedFct #Decrease step size if all neighbouring points are worse
    
    bm.evaluate(NP)
    return NP

if __name__ == '__main__':
    bm = staircase.HH_Benchmarker()
    run(bm, debug = True)