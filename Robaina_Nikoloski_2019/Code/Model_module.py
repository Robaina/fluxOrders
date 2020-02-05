import cobra
import re
import numpy as np
import pandas as pd
from cobra.flux_analysis.sampling import OptGPSampler
from cobra.core.reaction import Reaction as cobraReaction
from cobra.util.solver import set_objective
import rpy2.robjects as ro
from rpy2.robjects import numpy2ri
import warnings
import copy
from six import iteritems

from Order_module import FluxOrder
from Data_module import DataParser
from Helper_methods import isCandidatePair
ro.r['source']('Rfunctions.R')
FVA = ro.r['FVA']
sampleFluxCone = ro.r['sampleFluxCone']
numpy2ri.activate()


class Model:
    """
    Methods to load the GEM, convert it to the required form and update the
    flux bounds to match the carbon source.
    """
    def __init__(self, fileName, workDir=None, v_eps=1e-9, verbose=True):
        self.workDir = workDir
        self.name = ''
        self.carbonSource = 'all'
        self.__loadModel(fileName, workDir)
        self.__enableUptakeOfCarbonSources()
        self.__removeBlockedReactions(v_eps)
        self.__splitReversibleReactions()
        self.__removeReactionsWithZeroUpperBound()
        self. __addMetabolicMacrosystems()
        self.geneIDs = [gene.id for gene in self.GEM.genes]
        self.numberOfReactions = len(self.GEM.reactions)
        self.numberOfMetabolites = len(self.GEM.metabolites)
        self.original_lb = self.getLowerBounds()
        self.original_ub = self.getUpperBounds()
        self.verbose = verbose
        print('Split GEM generated with ' + str(self.numberOfReactions)
              + ' non-blocked reactions and ' + str(self.numberOfMetabolites)
              + ' metabolites')

    def getLowerBounds(self):
        return np.array([rxn.lower_bound for rxn in self.GEM.reactions])

    def getUpperBounds(self):
        return np.array([rxn.upper_bound for rxn in self.GEM.reactions])

    def setLowerBounds(self, lb):
        for i, rxn in enumerate(self.GEM.reactions):
            rxn.lower_bound = lb[i]

    def setUpperBounds(self, ub):
        for i, rxn in enumerate(self.GEM.reactions):
            rxn.upper_bound = ub[i]

    def getStoichiometricMatrix(self):
        return np.array(
            cobra.util.array.create_stoichiometric_matrix(self.GEM, array_type='dense'))

    def getSubsystems(self):
        return np.array([rxn.subsystem for rxn in self.GEM.reactions])

    def getMacrosystems(self):
        return np.array([rxn.macrosystem for rxn in self.GEM.reactions])

    def getReactionNames(self):
        return [rxn.name for rxn in self.GEM.reactions]

    def getReactionIDs(self):
        return [rxn.id for rxn in self.GEM.reactions]

    def setCarbonSource(self, carbonSource, uptakeRate=20, fractionOfBiomassOptimum=0.95):
        """
        Sets current carbon source: opens importer for carbon source, closes all order
        organic imports and maximizes biomass. Wrapper to the two methods that follow.
        """
        self.setLowerBounds(self.original_lb)
        self.setUpperBounds(self.original_ub)
        if carbonSource.lower() not in 'all':
            self.updateExchangeReactionBounds(carbonSource, carbonUptakeRate=uptakeRate)
        self.setMinimumBiomassProduction(fractionOfOptimum=fractionOfBiomassOptimum)

    def __loadModel(self, fileName, workDir=None):
        """
        Reads the SBML file containing the GEM. Removes blocked
        reactions i.e., reactions that cannot carry flux in Sv = 0, and splits
        reversible reactions into two irreversible reactions.

        Parameters
        ----------
        fileName: string
                  The path to the file containing the SBML model
        Returns
        -------
         GEM: cobrapy class model
              The transformed genome-scale model
        """
        if workDir is not None:
            path2File = workDir + '/' + fileName
        else:
            path2File = fileName

        modelName, fileExtension = fileName.split('.')
        self.name = modelName
        warnings.filterwarnings('ignore')
        if fileExtension in ['xml', 'sbml']:
            self.GEM = cobra.io.read_sbml_model(path2File)
        elif fileExtension == 'json':
            self.GEM = cobra.io.load_json_model(path2File)
        elif fileExtension == 'mat':
            self.GEM = cobra.io.load_matlab_model(path2File)
        warnings.resetwarnings()

    def __addMetabolicMacrosystems(self):
        df = pd.read_excel(self.workDir + '/' + self.name + '_subsystems.xlsx')
        met_systems = pd.Series(df.Systems.values, index=df.Subsystems).to_dict()
        for idx, rxn in enumerate(self.GEM.reactions):
            try:
                self.GEM.reactions[idx].macrosystem = met_systems[rxn.subsystem]
            except Exception:
                self.GEM.reactions[idx].macrosystem = 'Unassigned'

    def __enableUptakeOfCarbonSources(self):
        self.GEM.reactions.get_by_id('EX_glyc__R_e').lower_bound = -1000
        self.GEM.reactions.get_by_id('EX_ac_e').lower_bound = -1000

    def __removeBlockedReactions(self, v_eps):
        blockedRxns = cobra.flux_analysis.find_blocked_reactions(
            self.GEM, zero_cutoff=v_eps, open_exchanges=False)
        self.blockedReactions = blockedRxns
        for rxn in blockedRxns:
            self.GEM.reactions.get_by_id(rxn).remove_from_model(remove_orphans=True)

    def __splitReversibleReactions(self):
        convert_to_irreversible(self.GEM)

    def __removeReactionsWithZeroUpperBound(self):
        FakeRev = [rxn for rxn in range(len(self.GEM.reactions))
                   if self.GEM.reactions[rxn].upper_bound == 0]
        for rxn in FakeRev:
            self.GEM.reactions[rxn].remove_from_model(remove_orphans=True)

    def saveMatlabModel(self, workDir=None):
        if workDir is None:
            workDir = self.workDir
        cobra.io.save_matlab_model(self.GEM, workDir + '/' + self.name + '.mat')

    def updateExchangeReactionBounds(self, carbonSource=None, carbonUptakeRate=20):
        """
        Update exchange reaction bounds to simulate appropriate growth medium
        conditions.
        """
        ExchangeRxnIDs = [rxn.id for rxn in self.GEM.exchanges if len(rxn.reactants) == 0]
        for ID in ExchangeRxnIDs:
            try:
                if self.__isOrganicExchange(ID):
                    self.GEM.reactions.get_by_id(ID).upper_bound = 0
            except Exception:
                pass
        self.__setEcoliCarbonSourceUptake(carbonSource, carbonUptakeRate)
        self.carbonSource = carbonSource

    def __isOrganicExchange(self, ID):
        compoundAtoms = list(self.GEM.reactions.get_by_id(ID).products[0].formula)
        cond = (('C' in compoundAtoms)
                & ('H' in compoundAtoms)
                & ('o' not in compoundAtoms))  # discards cobalamine
        return cond

    def __setEcoliCarbonSourceUptake(self, carbonSource, carbonUptakeRate):
        """
        Set uptake rate for the selected carbon source for the E. coli model (iJO1366)
        """
        carbonSource = carbonSource.lower()
        if carbonSource in 'glucose':
            uptakeRxns = ['EX_glc__D_e_reverse']
        elif carbonSource in 'acetate':
            uptakeRxns = ['EX_ac_e_reverse']
        elif carbonSource in 'glycerate':
            uptakeRxns = ['EX_glyc__R_e_reverse']
        elif carbonSource in 'all':
            uptakeRxns = ['EX_glc__D_e_reverse', 'EX_ac_e_reverse', 'EX_glyc__R_e_reverse']
        for rxn in uptakeRxns:
            self.GEM.reactions.get_by_id(rxn).upper_bound = carbonUptakeRate

    def setMinimumBiomassProduction(self, ReactionID='biomass', fractionOfOptimum=0.95):
        """
        Constraints the reaction indicated in ReactionID to produce a fraction of the
        optimal value, specified in fractionOfOptimum. If ReactionID is left as None or
        'biomass', the function tries to find the biomass reaction and constraints biomass
        production. Either an ID or a reaction index can be given for the reaction.
        """
        if ReactionID is None or ReactionID.lower() in 'biomass':
            BiomassID = self.__getBiomassReactionID()
            if len(BiomassID) > 1:
                ReactionID = BiomassID[0]
                self.ObjectiveReactionID = ReactionID
                # Block alternative biomass reaction(s)
                for ID in BiomassID[1:]:
                    self.GEM.reactions.get_by_id(ID).upper_bound = 0

        if isinstance(ReactionID, list):
            ReactionID = ReactionID[0]
        
        # Optimize model
        ReactionName = self.GEM.reactions.get_by_id(ReactionID).name
        self.GEM.objective = self.GEM.reactions.get_by_any(ReactionID)
        vbioMax = self.GEM.optimize().objective_value
        self.GEM.reactions.get_by_id(ReactionID).lower_bound = fractionOfOptimum*vbioMax
        if self.verbose:
            print('Maximizing: ' + ReactionID + ', ' + ReactionName)
            print('Maximum growth rate under ' + self.carbonSource + ': ' + str(vbioMax) + ' h^{-1}')

    def __getBiomassReactionID(self):
        """
        Tries to find the biomass reaction in the GEM
        """
        reactionIDs = np.array(self.getReactionIDs())

        def getBiomassReactionByName():
            reactionNames = [rxn.name for rxn in self.GEM.reactions]
            biomassReactionName = [name for name in reactionNames
                                   if re.search('(?i)(biomass|growth)', name)]
            if biomassReactionName:
                return [reactionIDs[reactionNames.index(name)]
                        for name in biomassReactionName]
            else:
                return []

        biomassReactionID = [ID for ID in reactionIDs
                             if re.search('(?i)(biomass|growth)', ID)]

        if not biomassReactionID:
            biomassReactionID = getBiomassReactionByName()
        if not biomassReactionID:
            raise ValueError('Biomass reaction not found, provide biomass reaction ID')

        return biomassReactionID

    def getExtremeFluxes(self):
        """
        Conducts a Flux Variabilty Analysis in R and returns the 2d arrays FVAmin, FVAmax,
        containing the flux distributions which are solutions to each minimization and
        maximizing of each reaction in the model, as well as FVArange, a 2d array with the
        classic fva flux ranges per reaction in the model. The native cobra version of this
        function is not employed here because it does not return FVAmin and FVAmax, only
        the flux ranges. Returns a dictionary with fields: FVArange, FVAmin and FVAmax.
        """
        S = self.getStoichiometricMatrix()
        FVArange, FVAmin, FVAmax = FVA(S, v_lb=self.getLowerBounds(), v_ub=self.getUpperBounds())

        return {'FVArange': np.asarray(FVArange),
                'FVAmin': np.asarray(FVAmin),
                'FVAmax': np.asarray(FVAmax)}

    def getFluxSample(self, nsamples=5000):
        """
        Generates a sample of the flux cone. It uses the default sampler in cobrapy
        """
        optGPS = OptGPSampler(self.GEM, thinning=100, processes=3)
        samplerSample = optGPS.sample(nsamples)
        sample = samplerSample[optGPS.validate(samplerSample) == "v"]
        return sample

    def getFluxSampleInRprogram(self, nsamples=5000, lb=None, ub=None):
        """
        Generates a sample of the flux cone. It uses a custom R program ("sampleFluxCone")
        to obtain the sample, the lower and upper flux bounds can be specified as numpy
        arrays, otherwise they are taken from the model object.
        m
        """
        if lb is None:
            lb = self.getLowerBounds()
        if ub is None:
            ub = self.getUpperBounds()
        S = self.getStoichiometricMatrix()
        sample = np.array(sampleFluxCone(S, n_samples=nsamples, v_lb=lb, v_ub=ub))
        df = pd.DataFrame(sample.transpose(), columns=self.getReactionIDs())
        return df

    def findFullyCoupledWithSameFlux(self, fctable=None):
        """
        Find fully coupled reaction pairs with the same flux value across the flux cone
        """
        if fctable is None:
            raise AttributeError('fctable missing!')
        fcRatios = self.__computeFullyCoupledRatios(fctable)
        fcRatios[np.where(fcRatios != 1)] = 0
        equalFlux = []
        for column in range(np.size(fcRatios, 1)):
            rxns = np.where(fcRatios[:, column] == 1)[0].tolist()
            if rxns:
                rxns.append(column)
                rxns.sort()
                equalFlux.append(rxns)
        equalFlux = np.unique(np.array(equalFlux)).tolist()
        return equalFlux

    def __computeFullyCoupledRatios(self, fctable):
        """
        Finds the flux ratio of all fully coupled pairs in a GEM. Returns a  2D array
        where entries equal to 1 indicate that these rection pairs have equal flux values.
        """
        temp = copy.deepcopy(fctable)
        temp[np.diag_indices_from(temp)] = 0
        # temp[np.tril_indices_from(temp)] = 0
        fcPairs = np.where(temp == 1)
        npairs = len(fcPairs[0])
        nrxns = self.numberOfReactions
        tempGEM = self.GEM.copy()
        fcRatios = np.zeros((nrxns, nrxns))
        for pairIdx in range(npairs):
            rxn_i, rxn_j = fcPairs[0][pairIdx], fcPairs[1][pairIdx]
            tempGEM.objective = tempGEM.reactions[rxn_i]
            fluxes = np.round(tempGEM.optimize().fluxes, 6)
            # try:
            fcRatios[rxn_i, rxn_j] = fluxes[rxn_i] / fluxes[rxn_j]
            # fcRatios[rxn_j, rxn_i] = 1 / fcRatios[rxn_i, rxn_j]
        return fcRatios

    def findCandidatePairs(self, nsamples=5000, fva_filter=True):
        """
        Discard pairs with v_j > v_i in the sample and where vjmax_j <= vjmax_i in
        the vjmax vector and vimin_i >= vimin_j.
        """
        if self.verbose:
            print('Finding candidate ordered reaction pairs')
        if fva_filter:
            FVAout = self.getExtremeFluxes()
            FVAmin, FVAmax = FVAout['FVAmin'], FVAout['FVAmax']
        else:
            FVAmin, FVAmax = None, None
#         fluxSample = np.round(self.getFluxSample(nsamples).values.transpose(), 5)
        fluxSample = np.round(self.getFluxSampleInRprogram(nsamples).values.transpose(), 5)
        candidatePairs = []
        for rxn_i in range(self.numberOfReactions):
            for rxn_j in range(self.numberOfReactions):
                if isCandidatePair(fluxSample, rxn_i, rxn_j, FVAmin=FVAmin, FVAmax=FVAmax):
                    candidatePairs.append([rxn_i, rxn_j])

        candidatePairs = np.asarray(candidatePairs)
        if self.verbose:
            print('There are: ' + str(len(candidatePairs)) + ' candidate pairs out of ' +
                  str(0.5*self.numberOfReactions*(self.numberOfReactions - 1)) + ' total pairs')

        self.candidatePairs = candidatePairs

    def exportToCSV(self, directory, attributes=['S', 'lb', 'ub', 'candidatePairs'],
                   nametag=None):
        """
        Export attributes to csv in the specified directory. Default directory is the
        working directory defined for the class Model
        """
        if directory is None:
            raise ValueError('Missing directory to save files in!')
        if nametag is None:
            tag = ''
        else:
            tag = '_' + nametag

        self.lb = self.getLowerBounds()
        self.ub = self.getUpperBounds()
        self.S = self.getStoichiometricMatrix()
        for attribute in attributes:
            item = getattr(self, attribute)
            np.savetxt(f'{directory}/{self.name}_{attribute}{tag}.csv',
                       item, delimiter=',')

    def getFluxOrders(self, AdjacencyMatrix=None, fctable=None):
        """
        Instantiates class FluxOrder
        Arguments
        ---------
        A: numpy 2D array,
           The adjacency matrix of the Hasse diagram containing the flux order
           relations.
        """
        FluxOrders = FluxOrder(Model=self, AdjacencyMatrix=AdjacencyMatrix, fctable=fctable)
        return FluxOrders

    def parseData(self):
        """
        Instantiates class DataParser
        """
        Parser = DataParser(self, workDir=self.workDir + '/Data')
        return Parser
    
    def getReactionsWithGeneData(self, geneWithDataIDs):
        """
        Returns a list with all reactions in the model that have associated gene data
        Arguments:
        ---------
        geneWithDataIDs: a list containing the IDs of genes with available data
        """
        rxnsWithData = []
        for rxn in self.GEM.reactions:
            genes = [gene.id for gene in rxn.genes if gene.id in geneWithDataIDs]
            if len(genes) > 0:
                rxnsWithData.append(rxn.id)
        return rxnsWithData

    
    
# Other functions
def getFluxSampleInRprogram(S, nsamples=5000, lb=None, ub=None):
    """
    Generates a sample of the flux cone. It uses a custom R program ("sampleFluxCone") to
    obtain the sample, the lower and upper flux bounds and the stoichiometric
    matrix have to be specified as numpy arrays.
    """
    sample = sampleFluxCone(S, n_samples=nsamples, v_lb=lb, v_ub=ub)
    return sample


def convert_to_irreversible(cobra_model):
    """
    Split reversible reactions into two irreversible reactions: one going in
    the forward direction, the other in the backward direction. In this manner,
    all reactions in the model carry non-negative flux values. Forward reactions
    are tagged as "forward" while backward reactions as "backward".

    cobra_model: A Model object which will be modified in place.
    Modified from the deprecated cobrapy version by Semidan Robaina,
    February 2019.
    """
    reactions_to_add = []
    coefficients = {}

    def onlyBackward(reaction):
        return reaction.lower_bound < 0 and reaction.upper_bound <= 0

    def backwardAndForward(reaction):
        return reaction.lower_bound < 0 and reaction.upper_bound > 0

    def changeDirection(reaction):
        def swapSign(number):
            return -number
        lb = swapSign(reaction.upper_bound)
        ub = swapSign(reaction.lower_bound)
        reaction.lower_bound = lb
        reaction.upper_bound = ub
        reaction.objective_coefficient * -1
        reaction.notes["reflection"] = 'only reverse'
        reaction.id += '_reverse'
        reaction.name += '_reverse'
        for met in reaction._metabolites.keys():
            reaction._metabolites[met] *= -1

    def createBackwardReaction(reaction):
        backward_reaction = cobraReaction(reaction.id + '_reverse')
        backward_reaction.lower_bound = 0
        backward_reaction.upper_bound = -reaction.lower_bound
        reaction_dict = {k: v * -1
                         for k, v in iteritems(reaction._metabolites)}
        backward_reaction.add_metabolites(reaction_dict)
        backward_reaction._model = reaction._model
        backward_reaction._genes = reaction._genes
        for gene in reaction._genes:
            gene._reaction.add(backward_reaction)
        backward_reaction.subsystem = reaction.subsystem
        backward_reaction.name = reaction.name + '_reverse'
        backward_reaction._gene_reaction_rule = reaction._gene_reaction_rule
        coefficients[backward_reaction] = reaction.objective_coefficient * -1
        return backward_reaction

    for reaction in cobra_model.reactions:
        if onlyBackward(reaction):
            changeDirection(reaction)
        elif backwardAndForward(reaction):
            backward_reaction = createBackwardReaction(reaction)
            reactions_to_add.append(backward_reaction)
            reaction.lower_bound = 0

    cobra_model.add_reactions(reactions_to_add)
    set_objective(cobra_model, coefficients, additive=True)
