import numpy as np
import pandas as pd
import copy
from matplotlib import pyplot as plt
import rpy2.robjects as ro
from rpy2.robjects import numpy2ri
import networkx as nx
import collections
import itertools
import warnings
from scipy import stats as st

from Helper_methods import getAreaAboveZero, getFluxOrderDataFrame
from Plot_methods import plotOrderedCoupledPieCharts, plotValuesPerGraphLevel

ro.r['source']('Rfunctions.R')
sampleFluxCone = ro.r['sampleFluxCone']
getFluxOrders = ro.r['get_flux_orders']
numpy2ri.activate()

"""
Numpy intends to deprecate the matrix object, currently the only
way to handle sparse matrices is through scipy sparse matrix class,
and Numpy does not provide an alternative:
https://github.com/scikit-learn/scikit-learn/issues/12327
Hence, filter DeprecationWarning for now...
"""
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)


class FluxOrder:
    """
    Provides methods to find the flux-ordered reaction pairs of a GEM
    """
    def __init__(self, Model, AdjacencyMatrix=None, fctable=None, carbonSource=None):
        self.Model = Model
        self.carbonSource = carbonSource
        if AdjacencyMatrix is None:
            self.A = self.getAdjacencyMatrix()
        else:
            self.A = AdjacencyMatrix
        if fctable is None:
            warnings.warn('fctable missing..')
        else:
            self.fctable = fctable
        self.verbose = True

    def getAdjacencyMatrix(self):
        """
        This is a wrapper function over the R function to obtain the
        adjacency matrix of the Hasse diagram. Returns a pandas dataframe
        """
        if not hasattr(self.Model, 'candidatePairs'):
            self.Model.findCandidatePairs()
        else:
            self.removeFullyCoupledCandidatePairsWithEqualFluxes()

        # call R function (R starts indexing at 1)
        if self.verbose:
            print('Finding flux order relations...')
        A = np.asarray(getFluxOrders(self.Model.getStoichiometricMatrix(),
                       candidatePairs=self.Model.candidatePairs + 1,
                       v_lb=self.Model.getLowerBounds(),
                       v_ub=self.Model.getUpperBounds()))
        if self.verbose:
            print('There are: ' + str(sum(sum(A))) + ' true ordered pairs out of '
                  + str(0.5*self.Model.numberOfReactions*(self.Model.numberOfReactions - 1))
                  + ' total pairs')
        self.A = A
        return A

    def removeFullyCoupledCandidatePairsWithEqualFluxes(self):
        """
        Removes fully coupled pairs with flux ratio of 1 from the list of candidate pairs
        since fully coupled pairs can create cycles in the flux order graph.
        """
        fcRatios = self.__computeFullyCoupledRatios()
        del_pairs_idx = [idx for idx, pair in enumerate(self.Model.candidatePairs)
                         if fcRatios[pair[0], pair[1]] == 1]
        self.Model.candidatePairs = np.delete(self.Model.candidatePairs, del_pairs_idx, 0)
        return del_pairs_idx

    def setAdjacencyMatrix(self, A=None):
        """
        Method to add the adjacency matrix of the order relations to the Order object.
        Useful when the adjacency matrix is computed outside the Order object (e.g. in R)
        """
        if A is None:
            raise ValueError('Adjacency matrix must be provided!')
        else:
            self.A = A

    def __findFullyCoupledWithSameFlux(self):
        """
        Find fully coupled reaction pairs with the same flux value across the flux cone
        """
        if self.fctable is None:
            raise AttributeError('fctable missing!')
        fcRatios = self.__computeFullyCoupledRatios()
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

    def __computeFullyCoupledRatios(self):
        """
        Computes the flux ratio of all fully coupled pairs in a GEM. Returns a  2D array
        with the ij (row/column) entry equal to the flux ratio of the pair r_i/r_j.
        """
        warnings.filterwarnings('ignore')
        temp = copy.deepcopy(self.fctable)
        temp[np.diag_indices_from(temp)] = 0
        temp[np.tril_indices_from(temp)] = 0
        fcPairs = np.where(temp == 1)
        npairs = len(fcPairs[0])
        nrxns = self.Model.numberOfReactions
        tempGEM = self.Model.GEM.copy()
        fcRatios = np.zeros((nrxns, nrxns))
        for pairIdx in range(npairs):
            rxn_i, rxn_j = fcPairs[0][pairIdx], fcPairs[1][pairIdx]
            tempGEM.objective = tempGEM.reactions[rxn_i]
            fluxes = np.round(tempGEM.optimize().fluxes, 6)
            fcRatios[rxn_i, rxn_j] = fluxes[rxn_i] / fluxes[rxn_j]
            fcRatios[rxn_j, rxn_i] = 1 / fcRatios[rxn_i, rxn_j]
        warnings.resetwarnings()
        return fcRatios

    def __collapseFullyCoupledWithEqualFlux(self):
        """
        Returns a modified adjacency matrix where fully coupled reactions with equal
        flux are lumped together in the same node. Returns a modified model where fully
        coupled reactions with equal flux are lumped together in the same reaction
        """
        fcWithSameFlux = self.__findFullyCoupledWithSameFlux()
        collapsed_Adjacency_Matrix = getFluxOrderDataFrame(self.A, self.Model)
        collapsed_GEM = self.Model.GEM.copy()

        def collapseDataFrameEntries(df, IDs):
            collapsed_label = '||'.join(IDs)
            collapsed_df = df.drop(index=IDs[1:], columns=IDs[1:]).rename(
                index={IDs[0]: collapsed_label},
                columns={IDs[0]: collapsed_label})
            return collapsed_df

        def collapseGEMreactions(GEM, IDs):
            collapsed_label = '||'.join(IDs)
            for rxn_ID in IDs[1:]:
                GEM.reactions.get_by_id(
                    rxn_ID).remove_from_model(remove_orphans=True)
            collapsed_GEM.reactions.get_by_id(IDs[0]).id = collapsed_label
            return collapsed_GEM

        reactionIDs = np.array(self.Model.getReactionIDs())
        for rxns in fcWithSameFlux:
            collapsed_rxn_IDs = reactionIDs[rxns]

            collapsed_Adjacency_Matrix = collapseDataFrameEntries(
                collapsed_Adjacency_Matrix, collapsed_rxn_IDs)

            collapsed_GEM = collapseGEMreactions(collapsed_GEM, collapsed_rxn_IDs)

        return {'A': collapsed_Adjacency_Matrix, 'GEM': collapsed_GEM}

    def getGraph(self):
        """
        Construct a the transitive reduction of the graph representing flux
        order relations. Only after calling either of both
        buildFluxOrderDataFrame or findFluxOrderRelations methods.

        Returns
        -------
        A networkx graph object
        """
        if not hasattr(self, 'A'):
            raise ValueError("""Adjacency matrix missing! Call
                             .buildFluxOrderDataFrame or
                              .findFluxOrderRelations first""")

        collapsed = self.__collapseFullyCoupledWithEqualFlux()
        collapsed_Adjacency_Matrix = collapsed['A']
        collapsed_GEM = collapsed['GEM']
        A = collapsed_Adjacency_Matrix.values

        G = nx.from_numpy_matrix(A, create_using=nx.DiGraph())
        G_plus = nx.transitive_reduction(G)

        nodeMap = {}
        nodeAttributes = {}
        nodes = list(G_plus.nodes)
        reactions = collapsed_GEM.reactions
        for i in range(len(nodes)):
            nodeMap[nodes[i]] = reactions[nodes[i]].id
            nodeAttributes[nodes[i]] = {'name': reactions[nodes[i]].name,
                                        'subsystem': reactions[nodes[i]].subsystem,
                                        'macrosystem': reactions[nodes[i]].macrosystem
                                        }

        nx.set_node_attributes(G_plus, nodeAttributes)
        G_out = nx.relabel_nodes(G_plus, nodeMap, copy=False)
        isolated_nodes = list(nx.isolates(G_out))
        G_out.remove_nodes_from(isolated_nodes)
        self.G = G_out
        return OrderGraph(G_out)

    def evaluateFluxCouplingRelations(self, ax=None, colors=None):
        """
        Evaluates which ordered reaction pairs are also part of any flux coupling
        relationship, i.e., fully coupled, directionally coupled. Returns a dictionary
        with two arrays, the name of the coupling type, and the number of ordered pairs in
        each category. Plotly axis object can be provided, in which case a pie plot is
        returned with the colors contained in colors. The order of the coupling type is:
        uncoupled, full, partial and directional.
        """
        if not hasattr(self, 'A'):
            raise ValueError("""Adjacency matrix missing!
                             Call .buildFluxOrderDataFrame or
                              .findFluxOrderRelations first""")

        if self.fctable is None:
            raise ValueError('fctable with coupling relations is missing')

        fullyCoupledRatios = self.__computeFullyCoupledRatios()
        self.__removeFullyCoupledWithEqualFluxes(fullyCoupledRatios)
        fullyCoupledTable = self.__extractFullyCoupled()
        partiallyCoupledTable = self.__extractPartiallyCoupled()
        directionallyCoupledTable = self.__extractDirectionallyCoupled()
        coupledOrderedPairs = [self.__countCoupledAndOrderedPairs(table)
                               for table in [fullyCoupledTable, partiallyCoupledTable,
                                             directionallyCoupledTable]]
        totalCoupledPairs = [self.__countCoupledPairs(table)
                             for table in [fullyCoupledTable, partiallyCoupledTable,
                                           directionallyCoupledTable]]
        numberOfOrderedPairs = sum(sum(self.A))
        numberOfCoupledOrderedPairs = sum(coupledOrderedPairs)
        numberOfTotalCoupledPairs = sum(totalCoupledPairs)

        size = ([numberOfOrderedPairs - numberOfCoupledOrderedPairs]
                + [self.__countCoupledAndOrderedPairs(table)
                for table in [fullyCoupledTable, partiallyCoupledTable,
                              directionallyCoupledTable]])
        total = sum(size)
        names = ['uncoupled (' + str(round(100*size[0]/total, 2)) + '%)',
                 'full (' + str(round(100*(size[1]/total), 2)) + '%)', 'partial ('
                 + str(round(100*(size[2]/total), 2)) + '%)', 'directional ('
                 + str(round(100*(size[3]/total), 2)) + '%)']

        data = {'values': size, 'labels': names, 'fraction ordered coupled': {}}
        if ax is not None:
            plotOrderedCoupledPieCharts(data, ax,
                                        self.Model.carbonSource.capitalize(),
                                        colors)

        # Compute fraction of partially and directionally coupled pairs that are ordered
        coupled_ordered = [100 * round(self.__countCoupledAndOrderedPairs(table)
                           / self.__countCoupledPairs(table), 5)
                           for table in [partiallyCoupledTable, directionallyCoupledTable]
                           ]

        total_coupled_ordered = round(
            100 * (numberOfCoupledOrderedPairs / numberOfTotalCoupledPairs), 5)
        coupled_ordered_data = {'partial': coupled_ordered[0],
                                'directional': coupled_ordered[1],
                                'total': total_coupled_ordered}

        data['fraction ordered coupled'] = coupled_ordered_data

        return data

    def __removeFullyCoupledWithEqualFluxes(self, fullyCoupledRatios):
        equalFullyCoupledPairs = np.where(fullyCoupledRatios == 1)
        self.fctable[equalFullyCoupledPairs] = 0

    def __extractFullyCoupled(self):
        fullyCoupledTable = np.zeros_like(self.fctable)
        fullyCoupledTable[np.where(self.fctable == 1)] = 1
        return fullyCoupledTable

    def __extractPartiallyCoupled(self):
        partiallyCoupledTable = np.zeros_like(self.fctable)
        partiallyCoupledTable[np.where(self.fctable == 2)] = 1
        return partiallyCoupledTable

    def __extractDirectionallyCoupled(self):
        directionallyCoupledTable = np.zeros_like(self.fctable)
        directionallyCoupledTable[np.where(self.fctable >= 3)] = 1
        return directionallyCoupledTable

    def __countCoupledPairs(self, coupledTable):
        return 0.5*sum(sum(coupledTable))

    def __countCoupledAndOrderedPairs(self, coupledTable):
        return len(np.argwhere(np.logical_and(self.A, coupledTable)))

    def evaluateDataOrder(self, data=None, proteinCosts=None,
                           costPercentileThresholds=[0], samplesize=10000):
        """
        Instantiates the class DataOrderEvaluator which provides methods to
        evaluate whether the flux order relation is reflected in the different
        data types
        """
        if not hasattr(self, 'A'):
            raise AttributeError('Adjacency matrix is missing!')
        if data is None:
            raise AssertionError('Need to provide data!')

        fluxOrdersDataFrame = getFluxOrderDataFrame(self.A, self.Model)

        return DataOrderEvaluator(
                fluxOrdersDataFrame, Model=self.Model, data=data).evaluateDataOrderRelation(
                proteinCosts=proteinCosts,
                costPercentileThresholds=costPercentileThresholds,
                samplesize=samplesize)


class OrderGraph:
    """
    Methods to analyze the DAG of the flux orders
    """
    def __init__(self, G):
        self.G = G
        self.verbose = True

    def getGraphLevels(self):
        """
        Classifies reactions into levels of the hiearchy in the flux orders graph.
        Returns a dictionary with keys being the level number and values lists of
        reactions
        """
        if not hasattr(self, 'G'):
            raise ValueError('OrderGraph networkx object is missing')

        nx.set_edge_attributes(self.G, 'negativeWeight', -1)
        if self.verbose:
            print('Extracting reactions in flux order DAG levels...')
        nodeLevel = {}
        sourceNodes = self.__getSourceNodes()
        for node in self.G.nodes:
            longestPathsFromSource = []
            for source in sourceNodes:
                longestPath = self.__getLongestPath(source, node)
                if longestPath is not None:
                    longestPathsFromSource.append(longestPath)
            nodeLevel[node] = max(longestPathsFromSource)

        grouppedNodeLevels = {}
        for key, value in sorted(nodeLevel.items()):
            grouppedNodeLevels.setdefault(value, []).append(key)

        sortedGroupedNodeLevels = {}
        sorted_levels = list(grouppedNodeLevels.keys())
        sorted_levels.sort()
        for level in sorted_levels:
            sortedGroupedNodeLevels[level] = grouppedNodeLevels[level]

        self.graphLevels = sortedGroupedNodeLevels
        return sortedGroupedNodeLevels

    def __getLongestPath(self, source, target):
        """
        Returns longest path between source and target
        """
        try:
            max_path_length = nx.shortest_path_length(
                self.G, source=source, target=target, weight='negativeWeight')
        except Exception:
            max_path_length = None
        return max_path_length

    def evaluateGraphLevels(self):
        """
        Provides basic statistics about the levels in the hierarchical
        flux order graph
        """
        if not hasattr(self, 'graphLevels'):
            self.getGraphLevels()

        graph_items = list(self.graphLevels.items())
        levels, reactions = map(list, zip(*graph_items))
        number_of_reactions = list(map(len, reactions))

        plt.figure(figsize=(10, 7))
        plt.bar(levels, number_of_reactions)
        # plt.gca().invert_yaxis()
        plt.xticks(levels)
        plt.title('Reactions per hierarchy level')
        plt.xlabel('level')
        plt.ylabel('counts')
        plt.show()

        levelSystems = {}
        for level, reactions in self.graphLevels.items():
            systems = self.__getReactionSystem(reactions, system_type='macrosystem')
            systems_freq = self.__getListFrequencies(systems)
            levelSystems[level] = systems_freq
        df = pd.DataFrame.from_dict(levelSystems).fillna(0).transpose()
        df = df.loc[:, df.columns != 'Unassigned']
        fig, ax = plt.subplots(nrows=2, ncols=4, sharex=False,
                               sharey=False, figsize=(16, 8))
        fig.text(0.5, 0.04, 'level', ha='center', fontsize=14)
        fig.text(0.04, 0.5, 'frequency', va='center', rotation='vertical', fontsize=14)
        fig.suptitle('Metabolic systems per hierarchy level', fontsize=14)
        plt.subplots_adjust(wspace=None, hspace=0.3)
        df.plot.bar(ax=ax, subplots=True, legend=False, rot=0, fontsize=8)
        plt.show()
        return df

    def __getReactionSystem(self, reactionList, system_type='macrosystem'):
        """
        Returns a list with the metabolic systems of the reactions in reactionList
        system_type: string, either subsystem or macrosystem
        """
        metabolic_systems = []
        for rxn in reactionList:
            system = self.G.nodes[rxn][system_type]
            if not system.isspace():
                metabolic_systems.append(system)
        return metabolic_systems

    def __getListFrequencies(self, L):
        """
        Returns a dictionary with the frequency of the elements in the list L
        """
        counter = collections.Counter(L)
        total = len(L)
        frequencies = {key: counter[key] / total for key in counter.keys()}
        return frequencies

    def __getSourceNodes(self):
        sourceNodes = [node for (node, indegree) in self.G.in_degree()
                       if (indegree == 0 and not nx.is_isolate(self.G, node))]
        return sourceNodes

    def getReactionLineageDataFrame(self):
        """
        Returns a pandas dataframe with the number of ancestors and descendants
        of each reaction in the Hasse diagram of the flux order relations. Ancestors
        are reactions that have larger of equal flux values than the reaction under
        consideration, descendants those with equal or smaller values.
        """
        isolated_nodes = list(nx.isolates(self.G))
        self.G.remove_nodes_from(isolated_nodes)
        numberOfAncestors = [len(nx.ancestors(self.G, node))
                             for node in self.G.nodes()]
        numberOfDescendants = [len(nx.descendants(self.G, node))
                               for node in self.G.nodes()]
        data = np.array([numberOfAncestors, numberOfDescendants]).transpose()
        df = pd.DataFrame(data=data, index=self.G.nodes(),
                          columns=['number of ancestors', 'number of descendants'])
        df['name'] = [self.G.nodes[df.iloc[idx].name]['name'] for idx in range(len(df))]
        df['subsystem'] = [self.G.nodes[df.iloc[idx].name]['subsystem']
                           for idx in range(len(df))]
        df.sort_values('number of descendants', axis=0, ascending=False)
        return df

    def getOrderedReactionChain(self, size='maximum', source=None):
        """
        Returns a chain of ordered reactions. It can be the shortest path between
        source and target or a chain of specified size (number of reactions)
        """
        if not hasattr(self, 'graphLevels'):
            self.graphLevels = self.getGraphLevels()

        maximumSize = len(self.graphLevels)
        if size is None:
            size = 'maximum'
        if str(size).lower() in 'maximum':
            chain_size = maximumSize
        else:
            if size > maximumSize:
                size = maximumSize
                warnings.warn('Size larger than maximum size ('
                              + str(maximumSize) + ')')
            chain_size = size

        chains = self.getRandomChain(size=chain_size, source=source)
        max_chain_size = max([len(chain) for chain in chains.values()])
        targeted_size = min(chain_size, max_chain_size)

        for key in chains.keys():
            orderedReactionChain = chains[key]
            if len(orderedReactionChain) >= targeted_size:
                break
        return orderedReactionChain

    def getRandomChain(self, size=None, source=None):
        """
        Finds a random ordered chain of reactions of size equal to "size" (int). If
        provided, source is a reaction id, the function will try to find an ordered chain
        starting from the specified reaction.
        """
        orderedReactionChain = []
        if size is None:
            size = len(self.graphLevels)
        if source is None:
            while len(orderedReactionChain) < size:
                source = np.random.choice(self.graphLevels[0])
                target = np.random.choice(self.graphLevels[size])
                try:
                    orderedReactionChain = nx.shortest_path(
                        self.G, source=source, target=target, weight='negativeWeight')
                except Exception:
                    orderedReactionChain = []
        else:
            try:
                orderedReactionChain = nx.shortest_path(
                    self.G, source=source, weight='negativeWeight')
            except Exception:
                orderedReactionChain = []
        return orderedReactionChain


class DataOrderEvaluator:
    """
    Provides methods to evaluate whether data follows the predicted
    flux order relations
    """
    def __init__(self, fluxOrdersDataFrame, Model=None, data=None):

        if data is None:
            raise ValueError('Missing data structure!')
        else:
            self.data = data
        if (Model is None) and (data.type == 'gene'):
            raise ValueError('Missing model structure!')
        else:
            self.Model = Model
        self.verbose = True

        rxnID2Index = {}
        reactionIDs = list(fluxOrdersDataFrame.index)
        for rxn in reactionIDs:
            rxnID2Index[rxn] = reactionIDs.index(rxn)
        self.rxnID2Index = rxnID2Index

        # prepare adjacency matrix
        adjacencyMatrix = fluxOrdersDataFrame.values
        n_rxns = np.size(adjacencyMatrix, 0)
        for rxn_i in range(n_rxns):
            for rxn_j in range(rxn_i, n_rxns):
                if adjacencyMatrix[rxn_j, rxn_i] == 1:
                    adjacencyMatrix[rxn_j, rxn_i] = 0
                    adjacencyMatrix[rxn_i, rxn_j] = -1
        self.adjacencyMatrix = adjacencyMatrix

    def evaluateDataOrderRelation(self, proteinCosts=None, samplesize=100,
                                  costPercentileThresholds=[0], binRange=None,
                                  numberOfBins=None):
        """
        Evaluates the significance of the data evaluation by randomizing the
        genes assigned to ordered reaction pairs and re-evaluating the order
        relations in data in the case of gene and protein data and randomizing
        reaction names in the case of flux, Kcat, and enzyme activity data.
        """

        def isReactionData():
            return any(costPercentileThresholds) != 0 and self.data.type == 'reaction'

        if isReactionData():
            warnings.warn('Protein costs not supported in this data type')

        def unequalDataAndModelConditions():
            if self.Model is not None:
                return (hasattr(self.data, 'carbonSource')
                        and self.data.carbonSource.lower() not in self.Model.carbonSource)
            else:
                return False

        if unequalDataAndModelConditions():
            warnings.warn('Unequal model and data carbon source')

        def setProteinCostType():
            if self.data.carbonSource.lower() in 'acetate':
                costType = 'Acetate consumption'
            else:
                costType = 'Glucose consumption'
            if self.verbose:
                print('Using protein cost type: ' + costType)
            return costType

        if proteinCosts is not None and any(costPercentileThresholds) != 0:
            costType = setProteinCostType()
            self.proteinCosts = proteinCosts[['ID', costType]].rename(
                index=str, columns={costType: 'cost'})
        elif proteinCosts is None and any(costPercentileThresholds) != 0:
            raise ValueError('Missing protein cost data')

        if len(costPercentileThresholds) > 1:
            plots_data = {}
            for threshold in costPercentileThresholds:
                data = self.__runPermutationTest(samplesize, threshold,
                                                 binRange, numberOfBins)
                plots_data[threshold] = data

            return plots_data
        else:
            data = self.__runPermutationTest(samplesize, costPercentileThresholds[0],
                                             binRange, numberOfBins)
            return data

    def __runPermutationTest(self, sampleSize=100, costPercentileThreshold=0,
                             binRange=None, numberOfBins=None):
        """
        Evaluates the significance of the data evaluation by randomizing the
        genes assigned to ordered reaction pairs and re-evaluating the order
        relations in data in the case of gene and protein data
        """
        def countValuesInBins(distribution, bins):
            counts, _ = np.histogram(distribution, bins)
            return counts

        def getCumulativeDistributionData(distribution, bins):
            counts = countValuesInBins(distribution, bins)
            cumHist = np.nancumsum(counts)
            cumHist = cumHist / cumHist.max()
            return cumHist

        def getPvalue(k, n):
            """
            Computes the empirical p-value of the test as:
            p = (k + 1) / (n + 1)
            where k is the number of cases as extreme or more than the observed value
            and n is the size of the sampled distribution of statistics
            """
            return (k + 1) / (n + 1)

        if binRange is None:
            maxDiff = max(self.data.values) - min(self.data.values)
            binRange = [-maxDiff, maxDiff]
        if numberOfBins is None and self.data.type == 'gene':
            numberOfBins = 100
        else:
            numberOfBins = 10
        binEdges = np.linspace(binRange[0], binRange[1], numberOfBins)

        if self.data.type == 'gene':
            assert 0 <= costPercentileThreshold <= 100, 'Value only between 0 and 100'
            self.costPercentileThreshold = costPercentileThreshold
            reactionData = self.__getReactionGenes(self.data.index)
            permuteData = self.__permuteGenes
        else:
            if costPercentileThreshold != 0:
                warnings.warn('Protein costs not supported for this data type')
            reactionData = self.data.to_dict()
            permuteData = self.__permuteReactionData

        meanDiffDistributionOrderedPairs = self.__evalReactionData(reactionData)
        distributionSize = len(meanDiffDistributionOrderedPairs)
        if distributionSize == 0:
            raise ValueError('No data available for any flux-ordered pair')

        areaAboveZeroOfOrderedPairs = getAreaAboveZero(
            meanDiffDistributionOrderedPairs)

        countsInOrderedPairs = countValuesInBins(
            meanDiffDistributionOrderedPairs, binEdges)

        cumSumOfOrderedPairs = getCumulativeDistributionData(
            meanDiffDistributionOrderedPairs, binEdges)
        del meanDiffDistributionOrderedPairs

        countsInSample = np.zeros(numberOfBins - 1)
        n_more_extreme = 0
        sum_sample_areas = 0
        current_cumsum_min = np.ones(numberOfBins - 1)
        current_cumsum_max = np.zeros(numberOfBins - 1)

        for _ in range(sampleSize):
            permutedReactionData = permuteData(reactionData)
            meanDiffDistribution = self.__evalReactionData(permutedReactionData)
            sampledDistributionSize = len(meanDiffDistribution)

            counter = 0
            while sampledDistributionSize == 0 and counter < 10:
                permutedReactionData = permuteData(reactionData)
                meanDiffDistribution = self.__evalReactionData(permutedReactionData)
                sampledDistributionSize = len(meanDiffDistribution)
                counter += 1

            if counter >= 10:
                raise ValueError('Not enough data avaialable for flux-ordered pairs')

            countsInSample += countValuesInBins(
                meanDiffDistribution, binEdges)

            cumSum = getCumulativeDistributionData(
                meanDiffDistribution, binEdges)
            current_cumsum_min = np.minimum(cumSum, current_cumsum_min)
            current_cumsum_max = np.maximum(cumSum, current_cumsum_max)

            areaAboveZero = getAreaAboveZero(meanDiffDistribution)
            sum_sample_areas += areaAboveZero
            if areaAboveZero >= areaAboveZeroOfOrderedPairs:
                n_more_extreme += 1

            # del permutedReactionData, meanDiffDistribution

        mean_cumsum_sample = np.mean([current_cumsum_min, current_cumsum_max], axis=0)
        cumSumDistributions = {'cumSumOfOrderedPairs': cumSumOfOrderedPairs,
                               'meanCumSumsOfSamples': mean_cumsum_sample,
                               'minCumSumsOfSamples': current_cumsum_min,
                               'maxCumSumsOfSamples': current_cumsum_max}

        pValue = getPvalue(n_more_extreme, sampleSize)
        areaAboveZeroOfSample = sum_sample_areas / sampleSize

        return {'cumulative': cumSumDistributions,
                'ordered': countsInOrderedPairs,
                'sample': countsInSample,
                'distribution_size': distributionSize,
                'pvalue': pValue,
                'areaAboveZeroOfOrderedPairs': areaAboveZeroOfOrderedPairs,
                'areaAboveZeroOfSample': areaAboveZeroOfSample,
                'binEdges': binEdges,
                'cost_threshold': costPercentileThreshold,
                'carbonSource': self.data.carbonSource,
                'dataName': self.data.name}

    def __evalReactionData(self, reactionData):
        """
        Evaluates to which extent data follow the flux order
        relations predicted by the GEM.

        Arguments:
        ----------
        reactionData: dict, containing the gene IDs of each reaction in the GEM
        """
        if self.data.type == 'gene':
            if self.costPercentileThreshold > 0:
                reactionData = self.__filterCostlyGenes(reactionData, self.proteinCosts)
            reactionData = self.__extractGeneData(reactionData)

        # Make mean Data matrix and extract submatrix of
        # adjacencyMatrix of reactions with data
        rxnIndsWithData = [self.rxnID2Index[rxnID]
                           for rxnID in list(reactionData.keys())
                           if rxnID in self.rxnID2Index.keys()]

        AwithData = self.adjacencyMatrix[rxnIndsWithData, :][:, rxnIndsWithData]
        orderedPairs = np.where(AwithData != 0)
        dataValues, n = list(reactionData.values()), len(reactionData)
        dataValuesMatrix = np.broadcast_to(dataValues, (n, n))
        meanDiffMatrix = dataValuesMatrix.transpose() - dataValuesMatrix

        # Remove entries corresponding to unordered reactions
        AwithData = AwithData[orderedPairs]
        meanDiffMatrix = meanDiffMatrix[orderedPairs]
        meanDiffDistribution = np.multiply(
            AwithData, meanDiffMatrix).flatten().tolist()

        return meanDiffDistribution

    def __extractGeneData(self, reactionData):  # pre-compute to speed up loop
        rxnData = {}
        for rxn in list(reactionData.keys()):
            rxnData[rxn] = np.mean([self.data[g] for g in reactionData[rxn]])
        return rxnData

    def __getReactionGenes(self, genesWithData=None):
        """
        Returns a list of lists containing the gene IDs associated
        to each reaction in the GEM
        """
        if genesWithData is None:
            genesWithData = self.Model.geneIDs
        rxnGenesWithData = {}
        for rxn in self.Model.GEM.reactions:
            genes = [gene.id for gene in rxn.genes if gene.id in genesWithData]
            if len(genes) > 0:
                rxnGenesWithData[rxn.id] = genes

        return rxnGenesWithData

    def __filterCostlyGenes(self, rxnGenesWithData=None, proteinCosts=None):
        """
        Remove genes of proteins with metabolic cost below specified
        threshold from the reaction genes
        """
        costGenes = proteinCosts[proteinCosts['cost'] >= np.percentile(
            proteinCosts['cost'], self.costPercentileThreshold)]['ID'].values

        costlyRxnGenes = {}
        for rxn in list(rxnGenesWithData.keys()):
            costlyGenes = [gene for gene in rxnGenesWithData[rxn] if gene in costGenes]
            if len(costlyGenes) > 0:
                costlyRxnGenes[rxn] = costlyGenes

        return costlyRxnGenes

    def __permuteGenes(self, rxnGenesWithData):
        """
        Permutes genes across reactions such that reactions sharing a
        gene share also the permuted gene.
        """
        genesWithData = self.data.index
        permutedGenes = np.random.permutation(genesWithData)
        randomDict = dict(zip(genesWithData, permutedGenes))

        permutedRxnGenesWithData = {}
        for rxn in list(rxnGenesWithData.keys()):
            permutedRxnGenesWithData[rxn] = [randomDict[gene]
                                             for gene in rxnGenesWithData[rxn]
                                             if gene in genesWithData]

        return permutedRxnGenesWithData

    def __permuteReactionData(self, rxnData):
        """
        Permutes reaction data values among reactions with available data
        """
        permutedValues = np.random.permutation(list(rxnData.values()))
        permutedRxnData = {}
        for value, rxn in zip(permutedValues, list(rxnData.keys())):
            permutedRxnData[rxn] = value

        return permutedRxnData

    def evaluateGeneDataPerGraphLevel(self, Graph_Levels,
                                      statistic=None, sampleSize=None,
                                      plotTitle=None, group_levels=True,
                                      min_level_size=5):
        """
        Evaluates whether or not data values associated to enzyme genes tend to
        be higher the closer to the root the level of the flux order hierarchical graph
        in which enzymes are located.

        Arguments:
        ----------
        statistic: string,
                   "mean", "median", "min", max"
                   Default to None, the entire list of gene data values.

        sampleSize: int greater than 0,
                   Number of permutations performed in the permutation test
                   Default to None, in which case no permutation analysis is run.
        plotTitle: str, the title of the BoxPlot

        group_levels: Logical, whether or not to group graph levels into three
                      categories (first, middle, last) of levels

        min_level_size: int, minimum number of data points per level (to be
                        considered in the analysis)
        """
        statistic = statistic.lower()
        if statistic in 'mean':
            getStatistic = np.mean
        elif statistic in 'median':
            getStatistic = np.median
        elif statistic in 'minimum':
            getStatistic = np.min
        elif statistic in 'maximum':
            getStatistic = np.max
        else:
            def getStatistic(x):
                return x

        def getLevelValues(Graph_Levels, reactionGenes,
                           grouped=False, min_level_size=1):
            levelValues = {}
            for level, reactions in Graph_Levels.items():
                levelGenes = [gene for reaction in reactions
                              if reaction in reactionGenes.keys()
                              for gene in reactionGenes[reaction]]
                values = [self.data[gene] for gene in levelGenes if gene in self.data.keys()]
                if len(values) > 0:
                    levelValues[level] = values

            if grouped:
                grouped_levelValues = {}
                # partition_size = len(levelValues) // 3
                values = list(levelValues.values())
                # grouped_levelValues['first'] = list(itertools.chain.from_iterable(
                # values[:partition_size]))
                # grouped_levelValues['middle'] = list(itertools.chain.from_iterable(
                # values[partition_size:2 * partition_size]))
                # grouped_levelValues['last'] = list(itertools.chain.from_iterable(
                # values[2 * partition_size:]))

                grouped_levelValues['first'] = values[0]
                grouped_levelValues['middle'] = values[1]
                grouped_levelValues['last'] = list(itertools.chain.from_iterable(values[2:]))
                return grouped_levelValues

            else:
                for level in list(levelValues):
                    if len(levelValues[level]) < min_level_size:
                        del levelValues[level]
                return levelValues

        reactionGenes = self.__getReactionGenes()
        levelValues = getLevelValues(Graph_Levels, reactionGenes,
                                     grouped=group_levels, min_level_size=min_level_size)

        plotValuesPerGraphLevel(values=list(levelValues.values()),
                                labels=list(levelValues.keys()),
                                title=plotTitle)
        levelStatistic = [getStatistic(values) for values in levelValues.values() if values]
        significantPvalues, fraction_significant_comparisons = self.__applyMannWhitneyTestBetweenLevels(
            levelValues, alpha=0.05)
        numberOfSignificantComparisons = len(significantPvalues)

        # Run permutation analysis
        if sampleSize is not None:
            numberOfMoreExtremeSignificantComparisons = 0

            for _ in range(sampleSize):
                permutedReactionGenes = self.__permuteGenes(reactionGenes)
                permutedLevelValues = getLevelValues(Graph_Levels, permutedReactionGenes)
                permutedSignificantPvalues, _ = self.__applyMannWhitneyTestBetweenLevels(
                    permutedLevelValues, alpha=0.05)
                if len(permutedSignificantPvalues) >= numberOfSignificantComparisons:
                    numberOfMoreExtremeSignificantComparisons += 1

            permutationPvalue = (numberOfMoreExtremeSignificantComparisons + 1) / (sampleSize + 1)

        else:
            permutationPvalue = None

        return {'statistic': levelStatistic, 'pvalues': significantPvalues,
                'fraction significant comparisons': fraction_significant_comparisons,
                'permutation_pvalue': permutationPvalue}

    def __applyMannWhitneyTestBetweenLevels(self, levelValues, alpha=0.05):
        """
        Applies a Mann-Whitney test to all pairs of distributions of gene values in
        the hierarchy that follow the natural order, i.e., comparing one level to another
        downstream of the hiearchy. It also returns the fraction of evaluated comparisons
        with significant p-value.
        """
        n_levels = len(levelValues)
        values = list(levelValues.values())
        keys = list(levelValues.keys())
        number_level_comparisons = 0
        pvalues = []
        for i in range(n_levels - 1):
            for j in range(i + 1, n_levels):
                level_i, level_j = values[i], values[j]
                try:
                    MW = st.mannwhitneyu(level_i, level_j,
                                         use_continuity=True, alternative='greater')
                    pvalue = round(MW[1], 5)
                    if pvalue <= alpha:
                        pvalues.append([(keys[i], keys[j]), pvalue])
                    number_level_comparisons += 1
                except Exception:
                    pass

        fraction_significant_comparisons = len(pvalues) / number_level_comparisons
        return (pvalues, fraction_significant_comparisons)
