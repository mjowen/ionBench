import numpy as np
import myokit
import csv
#TODO:
#Prepacing - Still undecided if it is worth it in the benchmark
#Benchmarker requires data file, but data file is generated using benchmarker
#Set tolerances
#Noise adds in bias, need to make sure it doesn't move optimal parameters [currently doesn't seem to be a big issue]
#Parallel processes won't give the correct solveCount. Will need to build a test case and see how I can resolve this. shared_memory from the multiprocessing class seems to be a good option
#Improve style of evaluate output

class HH_Benchmarker():
    def __init__(self):
        print('Initialising Hodgkin-Huxley IKr benchmark')
        self.model = myokit.load_model('beattie-2017-ikr-hh.mmt')
        self.sim = myokit.Simulation(self.model)
        log = myokit.DataLog.load_csv('staircase-ramp.csv')
        self.sim.set_fixed_form_protocol(log.time(), log['voltage'])
        self.defaultParams = [2.26e-4, 0.0699, 3.45e-5, 0.05462, 0.0873, 8.91e-3, 5.15e-3, 0.03158, 0.1524]
        self.tmax = log.time()[-1]
        tmp=[]
        with open('dataHH.csv', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                tmp.append(float(row[0]))
        self.data = np.array(tmp)
        tmp=[]
        with open('trueParamsHH.csv', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                tmp.append(float(row[0]))
        self.__trueParams = np.array(tmp)
        self.__solveCount = 0
        print('Benchmarker initialised')
        
    def n_parameters(self):
        return len(self.defaultParams)
    
    def reset(self):
        self.__solveCount = 0
        self.sim.reset()
    
    def cost(self, parameters):
        #Calculate cost for a given set of parameters
        testOutput = np.array(self.simulate(parameters, np.arange(0, self.tmax)))
        return np.sqrt(np.mean((testOutput-self.data)**2))
    
    def simulate(self, parameters, times):
        #Simulate the model and find the current
        # Reset the simulation
        self.sim.reset()
        
        # Update the parameters
        for i in range(len(self.defaultParams)):
            self.sim.set_constant('ikr.p'+str(i+1), self.defaultParams[i]*parameters[i])
        
        # Run a simulation
        self.__solveCount += 1
        try:
            log = self.sim.run(self.tmax, log_times = times, log = ['ikr.IKr'])
            return log['ikr.IKr']
        except:
            return [np.inf]*len(times)
    
    def evaluate(self, parameters):
        print('Evaluating final parameters')
        print('Number of evaluations: '+str(self.__solveCount))
        cost =  self.cost(parameters)
        self.__solveCount -= 1
        print('Final cost: '+str(cost))
        parameters = np.array(parameters)
        rmse = np.sqrt(np.mean((parameters-self.__trueParams)**2))
        identifiedCount = np.sum(np.abs(parameters-self.__trueParams)<0.05)
        print('Parameter RMSE: '+str(rmse))
        print('Number of parameters correctly identified: '+str(identifiedCount))
        print('Total number of parameters in model: '+str(self.n_parameters()))
        print('Benchmark complete')

def generateData():
    bm = HH_Benchmarker()
    trueParams = np.random.uniform(0.5,1.5,bm.n_parameters())
    out = bm.simulate(trueParams, np.arange(bm.tmax))
    out = out + np.random.normal(0, np.mean(np.abs(out))*0.05, len(out))
    with open('dataHH.csv', 'w', newline = '') as csvfile:
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerows(map(lambda x: [x], out))
    with open('trueParamsHH.csv', 'w', newline = '') as csvfile:
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerows(map(lambda x: [x], trueParams))
