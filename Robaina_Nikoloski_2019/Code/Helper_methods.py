import numpy as np
import pandas as pd
from collections import Counter
import re
import copy
import scipy
import rpy2.robjects as ro
from rpy2.robjects import numpy2ri

ro.r['source']('Rfunctions.R')
FVA = ro.r['FVA']
sampleFluxCone = ro.r['sampleFluxCone']
getFluxOrders = ro.r['get_flux_orders']
numpy2ri.activate()


def isCandidatePair(fluxSample, rxn_i, rxn_j, FVAmin=None, FVAmax=None):
    cond1 = (all(fluxSample[rxn_j, :] <= fluxSample[rxn_i, :])
             and not all(fluxSample[rxn_j, :] == fluxSample[rxn_i, :]))
    if FVAmin is not None and FVAmax is not None:
        cond2 = ((FVAmax[rxn_j, rxn_j] <= FVAmax[rxn_i, rxn_j])
                 and (FVAmin[rxn_i, rxn_i] >= FVAmin[rxn_j, rxn_i]))
        return cond1 and cond2
    else:
        return cond1


def getDirectionalCouplingAdjacencyMatrix(fctable):
    dir_coupling_code = 3
    B = copy.deepcopy(fctable)
    B[np.where(B != dir_coupling_code)] = 0
    return B


def multipleIntersect(arrays):
    """
    Applies numpy intersect1d method to multiple arrays to return the intersection of
    all of them.
    """
    n_arrays = len(arrays)
    intersect = np.intersect1d(arrays[0], arrays[1])

    if n_arrays < 2:
        raise ValueError('Comparison between at least 2 arrays!')
    if n_arrays == 2:
        return intersect
    else:
        n_arrays_left = n_arrays - 2
        while n_arrays_left > 0:
            intersect = np.intersect1d(intersect, arrays[n_arrays - n_arrays_left])
            n_arrays_left -= 1
        return intersect


def getExclusiveReactions(reaction_arrays, level_number, exclusive_carbon_source, rest_sources):
    """
    Finds exclusive reactions between the exclusive carbon source and the rest of sources at
    the specfied level of the flux orders graph
    """
    reactions_to_compare = []
    for source in rest_sources:
        reactions_to_compare += reaction_arrays[source][level_number]
    return np.setdiff1d(
        reaction_arrays[exclusive_carbon_source][level_number], reactions_to_compare)


def extractMetabolicSystems(GEM, reactions_list, systemType, macrosystem=None):
    """
    Extracts a list of metabolic subsystems or macrosystems as specified in "systemType"
    from the list of reactions in "reaction_list". If macrosystem is not None,
    then subsystems are retrieved such that the reactions also belong to the specified
    macrosystem. GEM is the cobra model used to generate the list of reactions. The returned
    list may contain repeated systems.
    """
    if macrosystem is not None:
        systemType = 'subsystem'
    systems = []
    GEM_rxns = [rxn.id for rxn in GEM.reactions]

    def validReaction(rxn_id):
        if macrosystem is not None:
            cond = (rxn_id in GEM_rxns
                    and GEM.reactions.get_by_id(rxn_id).macrosystem in macrosystem)
        else:
            cond = rxn_id in GEM_rxns
        return cond

    for multiple_rxn_id in reactions_list:
        rxn_ids = re.split(r'\|\|', multiple_rxn_id)  # deals with collapsed fully coupled reactions

        for rxn_id in rxn_ids:
            if validReaction(rxn_id):
                systems.append(getattr(GEM.reactions.get_by_id(rxn_id), systemType))

    return systems


def extractSharedAndExclusiveReactions(Graph_Levels,
                                       carbonSources=['glucose', 'acetate', 'glycerate']):
    """
    Extracts the sets of shared reactions in the flux-order graph among the carbon
    sources and of exclusive reactions to each carbon source.
    """
    # Count levels
    levels, reactions, number_of_reactions = {}, {}, {}
    for carbonSource in carbonSources:
        graph_items = list(Graph_Levels[carbonSource].items())
        levels[carbonSource], reactions[carbonSource] = map(list, zip(*graph_items))
        number_of_reactions[carbonSource] = list(map(len, reactions[carbonSource]))

    # Find common and exclusive reactions per level
    shared_reactions, exclusive_reactions = {}, {}
    min_number_of_levels = min([len(levels[source]) for source in carbonSources])
    for level_number in range(min_number_of_levels):
        shared_reactions[level_number] = multipleIntersect(
            [reactions[source][level_number] for source in carbonSources])

        exclusive_reactions[level_number] = {}
        for carbonSource in carbonSources:
            rest_sources = [source for source in carbonSources if source is not carbonSource]

            exclusive_reactions[level_number][carbonSource] = getExclusiveReactions(
                reactions, level_number, carbonSource, rest_sources)

    return [shared_reactions, exclusive_reactions]


def getListFrequencies(a_list):
    return {k: round(v / len(a_list), 5) for k, v in Counter(a_list).items()}


def getSystemFrequencies(GEM, graph_reactions, system_type, carbonSource=None):
    """
    Get dictionary of macrosystem or subsystem frequencies in the total set of reactions
    of the flux orders graph
    """
    systems = []
    for level_number in graph_reactions.keys():
        if carbonSource is not None:
            systems += extractMetabolicSystems(
                GEM, graph_reactions[level_number][carbonSource], system_type)
        else:
            systems += extractMetabolicSystems(
                GEM, graph_reactions[level_number], system_type)
    return getListFrequencies(systems)


def getSystemDistributionPerGraphLevel(GEM, reactions_list, systemType='subsystem',
                                       carbonSources=['glucose', 'acetate', 'glycerate']):
    """
    Computes the frequency distribution of metabolic systems of systemType: subsystem or
    macrosystem per graph level.
    """
    def getSystemFrequency(system, systems_list):
        n_systems = len(systems_list)
        if n_systems > 0:
            return systems_list.count(system) / n_systems
        else:
            return 0

    def removeAllFromList(the_list, element_to_remove):
        while the_list.count(element_to_remove) > 0:
            the_list.remove(element_to_remove)
        return the_list

    total_systems = np.unique(
        np.array([getattr(GEM.reactions[i], systemType)
                  for i in range(len(GEM.reactions))])).tolist()
    # Remove unassigned systems
    total_systems = removeAllFromList(total_systems, 'Unassigned')

    is_exclusive_reaction = isinstance(reactions_list[0], dict)
    system_frequencies = {}

    for system in total_systems:

        if is_exclusive_reaction:
            system_frequencies[system] = {}

            for carbonSource in carbonSources:
                system_frequencies[system][carbonSource] = []
                for level_number in reactions_list.keys():

                    systems_list = extractMetabolicSystems(
                        GEM, reactions_list[level_number][carbonSource], systemType)
                    systems_list = removeAllFromList(systems_list, 'Unassigned')

                    system_frequencies[system][carbonSource].append(
                        getSystemFrequency(system, systems_list))
        else:
            system_frequencies[system] = []
            for level_number in reactions_list.keys():
                    systems_list = extractMetabolicSystems(
                           GEM, reactions_list[level_number], systemType)
                    system_frequencies[system].append(
                        getSystemFrequency(system, systems_list))

    return system_frequencies


def getSystemDistributionAcrossGraphLevels(GEM, reactions_list, systemType='subsystem',
                                           carbonSources=['glucose', 'acetate', 'glycerate']):
    """
    Computes the frequency distribution of metabolic systems of systemType: subsystem or
    macrosystem per graph level.
    Returns, list of lists of floats.
    """
    def removeAllFromList(the_list, element_to_remove):
        while the_list.count(element_to_remove) > 0:
            the_list.remove(element_to_remove)
        return the_list

    def getSystemCounts(system, systems_list):
        n_systems = len(systems_list)
        if n_systems > 0:
            return systems_list.count(system)
        else:
            return 0

    system_IDs = np.unique(
        np.array([getattr(GEM.reactions[i], systemType)
                  for i in range(len(GEM.reactions))])).tolist()
    # Remove unassigned systems
    system_IDs = removeAllFromList(system_IDs, 'Unassigned')

    system_frequencies, system_counts = {}, {}
    for system in system_IDs:

        system_counts[system], system_frequencies[system] = {}, {}
        for carbonSource in carbonSources:
            total_systems_list = []
            system_counts[system][carbonSource], system_frequencies[system][carbonSource] = [], []
            for level_number in reactions_list.keys():

                level_systems_list = extractMetabolicSystems(
                    GEM, reactions_list[level_number][carbonSource], systemType)
                level_systems_list = removeAllFromList(level_systems_list, 'Unassigned')
                total_systems_list.extend(level_systems_list)

                system_counts[system][carbonSource].append(
                    getSystemCounts(system, level_systems_list))

            system_frequencies[system][carbonSource] = [counts / getSystemCounts(system, total_systems_list)
                                                        for counts in system_counts[system][carbonSource]]

    return system_frequencies


"""
Functions to compute flux orders in the small network used to obtain the 13-C based
flux values. The small network was reconstructed manually from the supplementary figure
and table S4-S5 of the publication: from which 75% of the flux data employed here came
from. These functions are essentially the same as those used with the iJO1366 model.
"""


def getFluxOrdersForFluxDataNetwork(FluxDataNetwork, carbonUptakeRate=20, fva_filter=True):
    """
    Compute flux orders in the flux data network.
    Arguments:
    ---------
    FluxDataNetwork: pands DataFrame containing the stoichiometric matrix of the
    experimental network, supplied as excel file in supplementary information.
    carbonUptakeRate: float, the maximum allowed intake flux rate of the carbon source.
    fva_filter: boolean, whether to use additional filter to find candidate flux-ordered
    pairs, requires conducting Flux Variabilty Analysis in R.
    """
    # Prepare flux bounds
    FluxDataNetwork_lb = np.zeros((len(FluxDataNetwork.columns)))
    FluxDataNetwork_ub = 1000 * np.ones((len(FluxDataNetwork.columns)))
    # Set glucose intake to carbonUptakeRate (mmol.DW.h-1)
    FluxDataNetwork_ub[0] = 20

    # Find candidate pairs
    flux_sample = sampleFluxCone(FluxDataNetwork.values, n_samples=5000,
                                 v_lb=FluxDataNetwork_lb, v_ub=FluxDataNetwork_ub)
    flux_sample = np.array(flux_sample)

    if fva_filter:
        _, FVAmin, FVAmax = FVA(FluxDataNetwork.values,
                                v_lb=FluxDataNetwork_lb, v_ub=FluxDataNetwork_ub)
        FVAmin, FVAmax = np.array(FVAmin), np.array(FVAmax)
    else:
        FVAmin, FVAmax = None, None

    n_rxns = len(FluxDataNetwork.columns)
    candidatePairs = []
    for rxn_i in range(n_rxns):
        for rxn_j in range(n_rxns):
            if isCandidatePair(flux_sample, rxn_i, rxn_j, FVAmin=FVAmin, FVAmax=FVAmax):
                candidatePairs.append([rxn_i, rxn_j])

    candidatePairs = np.array(candidatePairs)
    print('There are: ' + str(len(candidatePairs)) + ' candidate pairs out of '
          + str(int(0.5*n_rxns*(n_rxns - 1))) + ' total pairs')

    # Find flux orders
    fluxOrders = getFluxOrders(FluxDataNetwork.values, v_lb=FluxDataNetwork_lb,
                               v_ub=FluxDataNetwork_ub, candidatePairs=candidatePairs + 1)

    FluxDataNetwork_Orders = pd.DataFrame(
        np.array(fluxOrders), index=FluxDataNetwork.columns, columns=FluxDataNetwork.columns)

    # Split lumped reactions to compare results with iJO1366 model
    for rxn_name in FluxDataNetwork_Orders.columns:
        if ',' in rxn_name:
            rxn_1_id, rxn_2_id = rxn_name.split(',')
            # Duplicate column
            FluxDataNetwork_Orders[rxn_2_id] = pd.Series(
                FluxDataNetwork_Orders[rxn_name], index=FluxDataNetwork_Orders.index)
            # Rename old lumped reaction
            FluxDataNetwork_Orders = FluxDataNetwork_Orders.rename(
                index=str, columns={rxn_name: rxn_1_id})

    for rxn_name in FluxDataNetwork_Orders.index:
        if ',' in rxn_name:
            rxn_1_id, rxn_2_id = rxn_name.split(',')
            # Duplicate row
            FluxDataNetwork_Orders.loc[rxn_2_id] = pd.Series(
                FluxDataNetwork_Orders.loc[rxn_name], index=FluxDataNetwork_Orders.columns)
            # Rename old lumped reaction
            FluxDataNetwork_Orders = FluxDataNetwork_Orders.rename(
                columns=str, index={rxn_name: rxn_1_id})

    n_ordered_pairs = sum(sum(FluxDataNetwork_Orders.values))
    print('There are: ' + str(int(n_ordered_pairs)) + ' ordered pairs out of '
          + str(len(candidatePairs)) + ' candidate pairs')

    return FluxDataNetwork_Orders


def getSharedOrderedPairs(fluxOrders1, fluxOrders2, reactionsWithData=None):
    """
    Find the set of shared ordered reaction pairs between fluxOrders1 and fluxOrders2,
    is reactionsWithData is given, a list of reaction ids for which flux data is available,
    then the set of shared reactions with data is also returned. Both, fluxOrders1 and
    fluxOrders2 are pandas dataframes.
    """
    def hasData(rxn_pair_ids, rxns_with_data):
        return rxn_pair_ids[0] in rxns_with_data and rxn_pair_ids[1] in rxns_with_data

    def reactionOrderIsShared(fluxOrders1, fluxOrders2, rxn_i, rxn_j):
        try:
            cond = (fluxOrders1.loc[rxn_i][rxn_j] == 1
                    and fluxOrders2.loc[rxn_i][rxn_j] == 1)
        except Exception:
            cond = False
        return cond

    output = {}
    rxn_list = fluxOrders1.index
    shared_ordered_pairs = [[rxn_i, rxn_j] for rxn_i in rxn_list for rxn_j in rxn_list
                            if reactionOrderIsShared(fluxOrders1, fluxOrders2, rxn_i, rxn_j)]
    output['total'] = shared_ordered_pairs

    if reactionsWithData is not None:
        shared_ordered_pairs_with_data = [rxn_pair for rxn_pair in shared_ordered_pairs
                                          if hasData(rxn_pair, reactionsWithData)]
    output['with data'] = shared_ordered_pairs_with_data

    return output


def getAreaAboveZero(distribution):
    distribution = np.round(distribution, 3)
    return len(np.where(np.asarray(distribution) > 0)[0]) / len(distribution)


def getAreaAboveZeroFromCounts(counts, bins):
    first_positive = np.where(bins > 0)[0][0]
    positive_counts = sum([counts[i] for i in range(first_positive + 1, len(counts))])
    total_counts = sum(counts)
    return positive_counts / total_counts


def getFluxOrderDataFrame(A, Model):
    """
    Build pandas dataframe with the flux order relations, reaction IDs are
    displayed as row and column names.

    Arguments
    ---------
    A: numpy 2D array,
       The adjacency matrix of the Hasse diagram containing the flux order
       relations.
    """
    reactionIDs = np.array(Model.getReactionIDs())
    if scipy.sparse.issparse(A):
        A = A.todense()
    fluxOrders = pd.DataFrame(data=A, index=reactionIDs,
                              columns=reactionIDs)
    return fluxOrders
