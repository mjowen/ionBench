import numpy as np
import scipy
import benchmarker
from functools import cache

from pymoo.core.individual import Individual
from pymoo.core.problem import Problem
from pymoo.operators.crossover.sbx import SBX

#Todo:
#Seems to devolve into many individuals giving infinite cost (likely negative parameters)

class individual():
    def __init__(self):
        self.x = np.random.rand(bm.n_parameters())*2
        self.cost = None
    def findCost(self):
        self.cost = costFunc(tuple(self.x))

bm = benchmarker.HH_Benchmarker()

@cache
def costFunc(x):
    return bm.cost(x)

nGens = 50
debug = True
eta_cross = 10
elitePercentage = 0.066
eta_mut = 20
popSize = 50
eliteCount = int(np.round(popSize*elitePercentage))
pop = [None]*popSize
for i in range(popSize):
    pop[i] = individual()
    pop[i].findCost()

for gen in range(nGens):
    costVec = [0]*popSize
    for i in range(popSize):
        costVec[i] = pop[i].cost
    eliteIndices = np.argsort(costVec)[:eliteCount]
    elites = [None]*eliteCount
    for i in range(eliteCount):
        elites[i] = pop[eliteIndices[i]]
    if debug:
        print("------------")
        print("Gen "+str(gen))
        print("Best cost: "+str(min(costVec)))
        print("Average cost: "+str(np.mean(costVec)))
    #Tournement selection
    newPop = []
    for j in range(2):
        perm = np.random.permutation(popSize)
        for i in range(popSize//2):
            if pop[perm[2*i]].cost > pop[perm[2*i+1]].cost:
                newPop.append(pop[perm[2*i]])
            else:
                newPop.append(pop[perm[2*i+1]])
    pop = newPop #Population of parents
    #Crossover SBX
    newPop = []
    problem = Problem(n_var=bm.n_parameters(), xl=0.0, xu=2.0)
    for i in range(popSize//2):
        a, b = Individual(X=np.array(pop[2*i].x)), Individual(X=np.array(pop[2*i+1].x))

        parents = [[a, b]]
        off = SBX(prob=0.9, eta=eta_cross).do(problem, parents) #What is prob vs prob_var
        Xp = off.get("X")
        newPop.append(individual())
        newPop[-1].x = Xp[0]
        newPop.append(individual())
        newPop[-1].x = Xp[1] #Can this be done in one line
    pop = newPop
    #Mutation
    for i in range(popSize):
        if np.random.rand()<0.9:
            direc = np.random.rand(bm.n_parameters())
            direc = direc/np.linalg.norm(direc)
            mag = scipy.stats.cauchy.rvs(loc=0, scale=0.18)
            pop[i].x += mag*direc
    if debug:
        print("Finishing gen "+str(gen))
    #Find costs
    for i in range(popSize):
        pop[i].findCost()
    #Elitism
    costVec = [0]*popSize
    for i in range(popSize):
        costVec[i] = pop[i].cost
    eliteIndices = np.argsort(costVec)[-eliteCount:]
    for i in range(eliteCount):
        pop[eliteIndices[i]] = elites[i]

minCost = np.inf
for i in range(popSize):
    if pop[i].cost < minCost:
        minCost = pop[i].cost
        elite = pop[i]
bm.evaluate(elite.x)