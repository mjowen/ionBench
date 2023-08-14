import numpy as np
import myokit
import csv
import os
import ionBench
import matplotlib.pyplot as plt
import warnings

class Tracker():
    """
    This class records the various performance metrics used to evaluate the optimisation algorithms. 
    
    It records the number of times the model is solved (stored as self.solveCount), not including the times that parameters were out of bounds.
    
    It records the RMSE (Root Mean Squared Error) cost each time a parameter vector is evaluated, using np.inf if parameters are out of bounds.
    
    It records the RMSRE (Root Mean Squared Relative Error) of the estimated parameters each time a parameter vector is evaluated. This is relative to the true parameters, ie the RMS of the vector of error between the estimated and true parameters, expressed as a percentage of the true parameters.
    
    It records the number of parameters that were correctly identified (within 5% of the true values) each time a parameter vector is evaluated.
    
    This class contains two methods: update(), and plot(). 
    
    update is called everytime a parameter vector is evaluated in the benchmarker and updates the performance metric vectors.
    
    plot is called during the benchmarkers evaluate function. It plots the performance metrics as functions of time (in the order in which parameter vectors were evaluated).
    """
    def __init__(self):
        self.costs = []
        self.paramRMSRE = []
        self.paramIdentifiedCount = []
        self.solveCount = 0
    
    def update(self, trueParams, estimatedParams, cost = np.inf, incrementSolveCounter = True):
        """
        This method updates the performance metric tracking vectors with new values. It should only be called by a benchmarker class.
        
        Parameters
        ----------
        
        trueParams : arraylike
            The vector of true parameters that generated the data set that is being used for fitting.
        estimatedParams : arraylike
            The vector of parameters that are being evaluated, after any transformations to return them to the original parameter space have been applied.
        cost : float, optional
            The RMSE cost of the parameter vectors that are being evaluated. The default is np.inf, to be used if parameters are out of bounds.
        incrementSolveCounter : bool, optional
            Should the solveCount be incremented, ie did the model need to be solved. This should only be False during benchmarker.evaluate() or if the parameters were out of bounds. The default is True.

        Returns
        -------
        None.

        """
        #Cast to numpy arrays
        trueParams = np.array(trueParams)
        estimatedParams = np.array(estimatedParams)
        #Update performance metrics
        self.paramRMSRE.append(np.sqrt(np.mean(((estimatedParams-trueParams)/trueParams)**2)))
        self.paramIdentifiedCount.append(np.sum(np.abs((estimatedParams-trueParams)/trueParams)<0.05))
        self.costs.append(cost)
        if incrementSolveCounter:
            self.solveCount += 1
    
    def plot(self):
        """
        This method plots the performance metrics as functions of time (in the order in which parameter vectors were evaluated). It will produce three plots, the RMSE cost, parameter RMSRE, and the number of identified parameters over the optimisation. This method will be called when benchmarker.evaluate() is called, so long as benchmarker.plotter = True (the default).

        Returns
        -------
        None.

        """
        #Cost plot
        plt.figure()
        plt.scatter(range(len(self.costs)),self.costs, c="k", marker=".")
        plt.xlabel('Cost function calls')
        plt.ylabel('RMSE cost')
        
        #Parameter RMSRE plot
        plt.figure()
        plt.scatter(range(len(self.paramRMSRE)),self.paramRMSRE, c="k", marker=".")
        plt.xlabel('Cost function calls')
        plt.ylabel('Parameter RMSRE')
        
        #Number of identified parameters plot
        plt.figure()
        plt.scatter(range(len(self.paramIdentifiedCount)),self.paramIdentifiedCount, c="k", marker=".")
        plt.xlabel('Cost function calls')
        plt.ylabel('Number of parameters identified')
    
class Benchmarker():
    """
    The Benchmarker class contains all the features needed to evaluate an optimisation algorithm. Generally, this class does not need to be called directly and is instead used as a parent class for the benchmarker problems. 
    
    A custom benchmarker can be built by first creating an instance of this class. Then calling the addModel() method with a Myokit model object and a Myokit log. Then a .csv data file can be added using the loadData() method.
    
    The main methods to use from this class are n_parameters(), cost(), reset(), and evaluate().
    """
    def __init__(self):
        self._bounded = False #Should the parameters be bounded
        self._logTransformParams = [False]*self.n_parameters() #Are any of the parameter log-transformed
        self.plotter = True #Should the performance metrics be plotted when evaluate() is called
        self.tracker = Tracker() #Tracks the performance metrics
        try:
            self.addModel(self.model, self._log) #Compile the Myokit model into a Myokit Simulation
        except:
            warnings.warn("No model or protocol has been defined for this benchmark. Please use the addModel function on this benchmarker object along with a Myokit model object and log to add the desired voltage protocol.")
    
    def addModel(self, model, log):
        """
        Adds a model and protocol to the benchmarker and compiles them. It also assigns self.tmax (the last timepoint in the protocol) and prepaces the simulation for 500ms.

        Parameters
        ----------
        model : Myokit Model
            A Myokit Model to compile and use to evaluate the parameters.
        log : Myokit Log
            A Myokit Log containing the voltage protocol under the name 'voltage'.

        Returns
        -------
        None.

        """
        self.model = model
        self.sim = myokit.Simulation(self.model)
        self.sim.set_tolerance(1e-8,1e-8)
        protocol = myokit.TimeSeriesProtocol(self._log.time(), self._log['voltage'])
        self.sim.set_protocol(protocol)
        self.tmax = self._log.time()[-1]
        self.sim.pre(500) #Prepace for 500ms
        
    def loadData(self, dataPath = '', paramPath = ''):
        """
        Loads output data to use in fitting.

        Parameters
        ----------
        dataPath : TYPE, optional
            An absolute filepath to the .csv data file. The default is '', in which case no file will be loaded.
        paramPath : TYPE, optional
            An absolute filepath to the .csv file containing the true parameters. The default is '', in which case no file will be loaded.

        Returns
        -------
        None.

        """
        if not dataPath == '':
            tmp=[]
            with open(dataPath, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    tmp.append(float(row[0]))
            self.data = np.array(tmp)
        if not paramPath == '':
            tmp=[]
            with open(paramPath, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    tmp.append(float(row[0]))
            self._trueParams = np.array(tmp)
    
    def addBounds(self, bounds, parameterSpace = 'original'):
        """
        Add bounds to the parameters. The bounds will be checked whenever the model is about to be solved, if they are violated then the model will not be solved and an infinite cost will be reported. The model solve count will not be incremented if the bounds are violated but the parameter vector will still be tracked for the other metrics.
        
        The bounds are checked after reversing any log-transforms on parameters (ie on exp(inputted parameters)).

        Parameters
        ----------
        bounds : list
            A list of bounds. The list should contain two elements, the first is a list of lower bounds, the same length as a parameter vector and the second a similar list of upper bounds. Use -np.inf or np.inf to not include bounds on particular parameters.
        parameterSpace : string
            Specify the parameter space of the inputted bounds. The options are 'original', to specify the bounds in the original parameter space, using the parameters that will be evaluated in the model, or 'input' for the parameter space inputted by the cost function, meaning they will be scaled by the default parameters if self._useScaleFactors=True, and log transformed if any parameters are to be log transformed. This will only have a difference if parameters are log transformed or if  self._useScaleFactors=True. The default is 'original'.

        Returns
        -------
        None.

        """
        if parameterSpace.lower() == 'input':
            self.lb = self.originalParameterSpace(bounds[0])
            self.ub = self.originalParameterSpace(bounds[1])
        elif parameterSpace.lower() == 'original':
            self.lb = bounds[0]
            self.ub = bounds[1]
        self._bounded = True
    
    def logTransform(self, whichParams = []):
        """
        Fit some parameters in a log-transformed space. 
        
        Inputted log-transformed parameters will be set to exp(inputted parameters) before solving the model.

        Parameters
        ----------
        whichParams : list, optional
            Which parameters should be log-transformed. The default is [], in which case all parameters will be log-transformed.

        Returns
        -------
        None.

        """
        if whichParams == []: #Log-transform all parameters
            whichParams = [True]*self.n_parameters()
        self._logTransformParams = whichParams
    
    def inputParameterSpace(self, parameters):
        """
        Maps parameters from the original parameter space to the input space. Incorporating any log transforms or scaling factors.

        Parameters
        ----------
        parameters : list
            Parameter vector in the original parameter space.

        Returns
        -------
        parameters : list
            Parameter vector mapped to input space.

        """
        for i in range(self.n_parameters()):
            if self._useScaleFactors:
                parameters[i] = parameters[i]/self.defaultParams[i]
            if self._logTransformParams[i]:
                parameters[i] = np.log(parameters[i])
        
        return parameters
    
    def originalParameterSpace(self, parameters):
        """
        Maps parameters from input space to the original parameter space. Removing any log transforms or scaling factors.

        Parameters
        ----------
        parameters : list
            Parameter vector in input space.

        Returns
        -------
        parameters : list
            Parameter vector mapped to the original parameter space.

        """
        for i in range(self.n_parameters()):
            if self._logTransformParams[i]:
                parameters[i] = np.exp(parameters[i])
            if self._useScaleFactors:
                parameters[i] = parameters[i]*self.defaultParams[i]
        
        return parameters
    
    def inBounds(self, parameters):
        """
        Checks if parameters are inside any bounds. If self._bounded = False, then it always returns True.

        Parameters
        ----------
        parameters : list or numpy array
            Vector of parameters (in original parameter space) to check against the bounds.

        Returns
        -------
        bool
            True if parameters are inside the bounds or no bounds are specified, False if the parameters are outside of the bounds.

        """
        if self._bounded:
            if any(parameters[i]<self.lb[i] or parameters[i]>self.ub[i] for i in range(self.n_parameters())):
                return False
        return True
    
    def n_parameters(self):
        """
        Returns the number of parameters in the model.
        """
        return len(self.defaultParams)
    
    def reset(self):
        """
        Resets the benchmarker. This clears the simulation object and restarts the performance tracker.

        Returns
        -------
        None.

        """
        self.sim.reset()
        self.tracker = Tracker()
    
    def cost(self, parameters, incrementSolveCounter = True):
        """
        Find the RMSE cost between the model solved using the inputted parameters and the data.

        Parameters
        ----------
        parameters : list or numpy array
            Vector of parameters to solve the model.
        incrementSolveCounter : bool, optional
            If False, it disables the solve counter tracker. This never needs to be set to False by a user. This is only required by the evaluate() method. The default is True.

        Returns
        -------
        cost : float
            The RMSE cost of the parameters.
        
        """
        testOutput = np.array(self.simulate(parameters, np.arange(0, self.tmax), incrementSolveCounter = incrementSolveCounter))
        cost = np.sqrt(np.mean((testOutput-self.data)**2))
        return cost
    
    def signedError(self, parameters):
        """
        Similar to the cost method, but instead returns the vector of residuals/errors in the model output.

        Parameters
        ----------
        parameters : list or numpy array
            Vector of parameters to solve the model.

        Returns
        -------
        signedError : numpy array
            The vector of model errors/residuals.

        """
        #Calculate cost for a given set of parameters
        testOutput = np.array(self.simulate(parameters, np.arange(0, self.tmax)))
        return (testOutput-self.data)
    
    def squaredError(self, parameters):
        """
        Similar to the cost method, but instead returns the vector of squared residuals/errors in the model output.

        Parameters
        ----------
        parameters : list or numpy array
            Vector of parameters to solve the model.

        Returns
        -------
        signedError : numpy array
            The vector of model squared errors/residuals.
        
        """
        #Calculate cost for a given set of parameters
        testOutput = np.array(self.simulate(parameters, np.arange(0, self.tmax)))
        return (testOutput-self.data)**2
    
    def setParams(self, parameters):
        """
        Set the parameters in the simulation object. Inputted parameters should be in the original parameter space.

        Parameters
        ----------
        parameters : list or numpy array
            Vector of parameters to solve the model.

        Returns
        -------
        None.

        """
        # Update the parameters
        for i in range(self.n_parameters()):
            self.sim.set_constant(self._paramContainer+'.p'+str(i+1), parameters[i])
    
    def solveModel(self, times, continueOnError = True):
        """
        Solve the model at the inputted times and return the current trace.

        Parameters
        ----------
        times : list or numpy array
            Vector of timepoints to record model output. Typically in ms.
        continueOnError : bool, optional
            If continueOnError is True, any errors that occur during solving the model will be ignored and an infinite output will be given. The default is True.

        Returns
        -------
        modelOutput : list
            A vector of model outputs (current trace).
        
        """
        if continueOnError:
            try:
                log = self.sim.run(self.tmax+1, log_times = times, log = [self._outputName])
                return log[self._outputName]
            except:
                return [np.inf]*len(times)
        else:
            log = self.sim.run(self.tmax+1, log_times = times, log = [self._outputName])
            return log[self._outputName]
    
    def simulate(self, parameters, times, continueOnError = True, incrementSolveCounter = True):
        """
        Simulate the model for the inputted parameters and return the model output at the specified times.

        Parameters
        ----------
        parameters : list or numpy array
            Vector of parameters to solve the model.
        times : list or numpy array
            Vector of timepoints to record model output. Typically in ms.
        continueOnError : bool, optional
            If continueOnError is True, any errors that occur during solving the model will be ignored and an infinite output will be given. The default is True.
        incrementSolveCounter : bool, optional
            If False, it disables the solve counter tracker. This never needs to be set to False by a user. This is only required by the evaluate() method. The default is True.

        Returns
        -------
        modelOutput : list
            A vector of model outputs (current trace).

        """
        #Return the parameters to the original parameter space
        parameters = self.originalParameterSpace(parameters)
        
        # Reset the simulation
        self.sim.reset()
        
        # Abort solving if the parameters are out of bounds
        if not self.inBounds(parameters):
            self.tracker.update(self._trueParams, parameters, incrementSolveCounter = False)
            return [np.inf]*len(times)
        
        # Set the parameters in the simulation object
        self.setParams(parameters)
        
        # Run the simulation and track the performance
        out = self.solveModel(times, continueOnError = continueOnError)
        self.tracker.update(self._trueParams, parameters, cost = np.sqrt(np.mean((out-self.data)**2)), incrementSolveCounter = incrementSolveCounter)
        return out
    
    def evaluate(self, parameters):
        """
        Evaluates a final set of parameters. 
        
        This method reports the performance metrics for this parameter vector (calling evaluate() does NOT increase the number of cost function evaluations). If self.plotter = True, then it also plots the performance metrics over the course of the optimisation.

        Parameters
        ----------
        parameters : list or numpy array
            Vector of parameters to solve the model, evaluating the performance of the final parameter vector.

        Returns
        -------
        None.

        """
        print('')
        print('=========================================')
        print('===    Evaluating Final Parameters    ===')
        print('=========================================')
        print('')
        print('Number of cost evaluations:      '+str(self.tracker.solveCount))
        cost =  self.cost(parameters, incrementSolveCounter = False)
        print('Final cost:                      {0:.6f}'.format(cost))
        print('Parameter RMSRE:                  {0:.6f}'.format(self.tracker.paramRMSRE[-1]))
        print('Number of identified parameters: '+str(self.tracker.paramIdentifiedCount[-1]))
        print('Total number of parameters:      '+str(self.n_parameters()))
        print('')
        if self.plotter:
            self.tracker.plot()
        