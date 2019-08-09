import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import warnings
import seaborn as sns
from ipywidgets import widgets, interact
import rpy2.robjects as ro
from rpy2.robjects import numpy2ri
import copy
import cobra

from ipywidgets_New.interact import StaticInteract
from ipywidgets_New.widgets import RangeWidget, DropDownWidget

from Helper_methods import (
                             getSystemDistributionPerGraphLevel,
                             getSystemDistributionAcrossGraphLevels,
                             extractMetabolicSystems,
                             getListFrequencies,
                             getSystemFrequencies,
                             )
plt.style.use('seaborn')
ro.r['source']('Rfunctions.R')
FVA = ro.r['FVA']
sampleFluxCone = ro.r['sampleFluxCone']
getFluxOrders = ro.r['get_flux_orders']
numpy2ri.activate()


def plotDataOrder(data, color='#ffbf00', interactive=True, has_protein_costs=True):
    if interactive and has_protein_costs:
        plot_func = plotDataOrderInteractiveWithCosts
    elif interactive and not has_protein_costs:
        plot_func = plotDataOrderInteractiveWithoutCosts
    else:
        plot_func = plotDataOrderStatic

    return plot_func(data, color)


def plotDataOrderStatic(plot_data, color='#25a9f4'):

    distributionSize = plot_data['distribution_size']
    cumSumDistributions = plot_data['cumulative']
    countsInOrderedPairs = plot_data['ordered']
    countsInSample = plot_data['sample']
    areaOrdered = plot_data['areaAboveZeroOfOrderedPairs']
    areaSample = plot_data['areaAboveZeroOfSample']
    pvalue = plot_data['pvalue']
    binEdges = plot_data['binEdges']
    dataName = plot_data['dataName']

    is_flux_data = 'flux data' in dataName.lower()
    if is_flux_data:
        delta_str = r'$\hat{{\delta}}$'
    else:
        delta_str = r'$\delta}$'

    fig = plt.figure(figsize=(18.5, 6.5))
    suptitle = r'{data}, area({delta} > 0) = {area:.2f}'.format(
        data=dataName,
        delta=delta_str,
        area=areaOrdered)
    plt.suptitle(suptitle, fontsize=16)

    plt.subplot(121)
    title = '$p$-value = {:.4f}'.format(pvalue)
    plotCumulativeDistributions(cumSumDistributions,
                                binEdges, color, title, xlabel=delta_str)
    plt.subplot(122)
    counts = {'Ordered': countsInOrderedPairs / countsInOrderedPairs.sum(),
              'Random': countsInSample / countsInSample.sum()}
    title = 'Size = {}'.format(distributionSize)
    colors = [color, '#afafaf']
    labels = [r'{}, area({} > 0) = {:.2f}'.format(type, delta_str, area)
              for type, area in zip(list(counts.keys()), [areaOrdered, areaSample])]

    plotHistograms(counts, binEdges, colors=colors, labels=labels,
                   title=title, xlabel=delta_str)
    plt.subplots_adjust(wspace=0.3, hspace=None)
    return fig


def plotDataOrderInteractiveWithoutCosts(plot_data, color='#ffbf00'):
    """
    Plot an interactive figure (of class StaticInteract) containig the distributions of
    data differences for the ordered pairs and the permutation sample. It takes as input
    plot_data: the dictionary returned by Orders.evaluateFluxOrders() and color: a str
    containing the color code to be used when plotting the ordered data distribution.
    """
    plt.rcParams.update({'figure.max_open_warning': 0})

    def plot_func(carbonSource):
        warnings.filterwarnings('ignore')

        distributionSize = plot_data[carbonSource]['distribution_size']
        cumSumDistributions = plot_data[carbonSource]['cumulative']
        countsInOrderedPairs = plot_data[carbonSource]['ordered']
        countsInSample = plot_data[carbonSource]['sample']
        areaOrdered = plot_data[carbonSource]['areaAboveZeroOfOrderedPairs']
        areaSample = plot_data[carbonSource]['areaAboveZeroOfSample']
        pvalue = plot_data[carbonSource]['pvalue']
        binEdges = plot_data[carbonSource]['binEdges']
        dataName = plot_data[carbonSource]['dataName']

        fig = plt.figure(figsize=(20, 7))
        suptitle = r'{data}, area($\delta$ > 0) = {area:.2f}'.format(
            data=dataName,
            area=areaOrdered)
        plt.suptitle(suptitle, fontsize=16)

        plt.subplot(121)
        title = '$p$-value = {:.4f}'.format(pvalue)
        plotCumulativeDistributions(cumSumDistributions,
                                    binEdges, color, title, xlabel=r'$\delta$')
        plt.subplot(122)
        counts = {'Ordered': countsInOrderedPairs / countsInOrderedPairs.sum(),
                  'Random': countsInSample / countsInSample.sum()}
        title = 'Size = {}'.format(distributionSize)
        colors = [color, '#afafaf']
        labels = [r'{}, area($\delta$ > 0) = {:.2f}'.format(type, area)
                  for type, area in zip(list(counts.keys()), [areaOrdered, areaSample])]

        plotHistograms(counts, binEdges, colors=colors, labels=labels, title=title,
                       xlabel=r'$\delta$')
        plt.subplots_adjust(wspace=0.3, hspace=None)
        warnings.resetwarnings()
        return fig

    carbonSources = list(plot_data.keys())
    interactive_fig = StaticInteract(
        plot_func,
        carbonSource=DropDownWidget(carbonSources, description='Carbon source'),
        interact_name=plot_data[list(plot_data.keys())[0]]['dataName'].replace('(glucose)', '')
        )
    return interactive_fig


def plotDataOrderInteractiveWithCosts(plot_data, color='#ffbf00'):
    """
    Plot an interactive figure (of class StaticInteract) containig the distributions of
    data differences for the ordered pairs and the permutation sample. It takes as input
    plot_data: the dictionary returned by Orders.evaluateFluxOrders() and color: a str
    containing the color code to be used when plotting the ordered data distribution.
    """
    plt.rcParams.update({'figure.max_open_warning': 0})

    def plot_func(carbonSource, percentile):
        warnings.filterwarnings('ignore')
        distributionSize = plot_data[carbonSource][percentile]['distribution_size']
        cumSumDistributions = plot_data[carbonSource][percentile]['cumulative']
        countsInOrderedPairs = plot_data[carbonSource][percentile]['ordered']
        countsInSample = plot_data[carbonSource][percentile]['sample']
        areaOrdered = plot_data[carbonSource][percentile]['areaAboveZeroOfOrderedPairs']
        areaSample = plot_data[carbonSource][percentile]['areaAboveZeroOfSample']
        pvalue = plot_data[carbonSource][percentile]['pvalue']
        binEdges = plot_data[carbonSource][percentile]['binEdges']
        dataName = plot_data[carbonSource][percentile]['dataName']
        Plabel = '$P_{{}}$'.format(percentile)

        fig = plt.figure(figsize=(20, 7))
        suptitle = r'{data}, {plabel}, area($\hat{{\delta}}$ > 0) = {area:.2f}'.format(
            data=dataName,
            plabel=Plabel,
            area=areaOrdered)
        plt.suptitle(suptitle, fontsize=16)

        plt.subplot(121)
        title = '$p$-value = {:.4f}'.format(pvalue)
        plotCumulativeDistributions(cumSumDistributions,
                                    binEdges, color, title)
        plt.subplot(122)
        counts = {'Ordered': countsInOrderedPairs / countsInOrderedPairs.sum(),
                  'Random': countsInSample / countsInSample.sum()}
        title = 'Size = {}'.format(distributionSize)
        colors = [color, '#afafaf']
        labels = [r'{}, area($\hat{{\delta}}$ > 0) = {:.2f}'.format(type, area)
                  for type, area in zip(list(counts.keys()), [areaOrdered, areaSample])]

        plotHistograms(counts, binEdges, colors=colors, labels=labels, title=title)
        plt.subplots_adjust(wspace=0.3, hspace=None)
        warnings.resetwarnings()
        return fig

    carbonSources = list(plot_data.keys())
    percentiles = list(plot_data['glucose'].keys())
    PLabels = ['P' + str(p) for p in percentiles]
    interactive_fig = StaticInteract(
        plot_func,
        carbonSource=DropDownWidget(carbonSources, description='Carbon source'),
        percentile=DropDownWidget(percentiles, description='Percentile', labels=PLabels),
        interact_name=plot_data['glucose'][0]['dataName'].replace('(glucose)', '')
        )
    return interactive_fig


def plotCumulativeDistributions(distributions=None, binEdges=None,
                                color='#ffbf00', title=None, xlabel=r'$\hat{\delta}$'):
    sampleDist = distributions['cumSumOfOrderedPairs']
    minDist = distributions['minCumSumsOfSamples']
    maxDist = distributions['maxCumSumsOfSamples']
    meanDist = distributions['meanCumSumsOfSamples']

    if title is not None:
        plt.title(title, fontsize=17)
    plt.xlabel(xlabel, fontsize=14)
    plt.ylabel('$area$', fontsize=14)
    plt.plot(binEdges[1:], sampleDist, color=color, linewidth=2.5)
    plt.plot(binEdges[1:], meanDist, color='black', linewidth=1.5)
    plt.fill_between(binEdges[1:], minDist, maxDist, color='#dddddd')


def plotHistograms(counts, bins, colors=None, labels=None,
                   title=None, xlabel=r'$\hat{\delta}$'):
    """
    Plot histograms from counts and bins, counts can be an array of
    arrays of counts, bins must be a single array of bin edges
    (same bins for all distributions)
    """
    if colors is None:
        colors = [None for _ in len(counts)]
    if labels is None:
        labels = [None for _ in len(counts)]
    if title is not None:
        plt.title(title, fontsize=17)
    plt.xlabel(xlabel, fontsize=14)
    plt.ylabel('$frequency$', fontsize=14)

    centroids = (bins[1:] + bins[:-1]) / 2
    names = list(counts.keys())
    for datatype, color, label in zip(names, colors, labels):

        sns.distplot(centroids, bins=bins, hist=True, kde=False,
                     kde_kws={'shade': True,
                              'linewidth': 3},
                     hist_kws={'weights': counts[datatype],
                               'range': (min(bins), max(bins)),
                               'edgecolor': color},
                     label=label, color=color)

    plt.legend(fontsize=12)


def plotValuesPerGraphLevel(values, labels=None, title=None):
    """
    Plots the distributions of number of regulatory events per hierarchy
    level
    """
    plt.figure(figsize=(12, 8))
    plt.boxplot(values, meanline=False, showmeans=True)
    plt.ylabel('values')
    if labels is not None:
        plt.xticks(list(range(1, len(values) + 1)), labels, fontsize=16)
    if title is not None:
        plt.title(title, fontsize=18, pad=20)
    locs, _ = plt.xticks()
    ax = plt.gca()
    sizes = [len(v) for v in values]
    for loc, size in zip(locs, sizes):
        plt.text(loc, 0.9, str(size),
                 transform=ax.get_xaxis_transform(),
                 fontsize=12)
    plt.show()


def plotLevelSubsystems(Model, graph_reactions, fig_dpi=100):
    """
    Computes the frequencies of the subsystems of the reactions appearing
    in the specified graph level which have the specified macrosystem
    """
    GEM = Model.GEM
    macrosystems = ['Amino acid metabolism', 'Carbohydrate metabolism', 'Cell wall biosynthesis',
                    'Cofactor and vitamin metabolism', 'Energy and maintenance', 'Lipid metabolism',
                    'Nucleotide metabolism', 'Transport']

    macrosystem_frequencies_per_level = getSystemDistributionPerGraphLevel(
        GEM, graph_reactions, 'macrosystem')

    macrosystem_frequencies_across_levels = getSystemDistributionAcrossGraphLevels(
        GEM, graph_reactions, 'macrosystem')

    def plot_func(macrosystem, macro_freq_type, level_number, save_fig):
        if macro_freq_type > 0:
            macro_frequencies = macrosystem_frequencies_per_level
            ylabel = 'frequency in level'
        else:
            macro_frequencies = macrosystem_frequencies_across_levels
            ylabel = 'frequency'
        total_subsystems = {}
        level_reactions = graph_reactions[level_number]
        fig, axs = plt.subplots(nrows=2, ncols=1, sharex=False, sharey=False, figsize=(14, 12))
        plt.subplots_adjust(wspace=None, hspace=0.3)

        # Plot macrosystems
        df1 = pd.DataFrame.from_dict(macro_frequencies[macrosystem])
        ax1 = df1.plot.bar(ax=axs[0], rot=0, fontsize=12)
        for p in ax1.patches:
            height = round(p.get_height(), 2)
            if height > 0:
                ax1.annotate(format(height, '.2f'),
                             (p.get_x() * 1.005, p.get_height() * 1.008))
        axs[0].set_title(macrosystem, fontsize=16)
        axs[0].set_ylabel(ylabel)
        axs[0].set_xlabel('graph level')

        # Plot subsystems
        for source in level_reactions.keys():
            subsystems = extractMetabolicSystems(GEM, level_reactions[source],
                                                 'subsystem', macrosystem)
            total_subsystems[source] = getListFrequencies(subsystems)

        df2 = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in total_subsystems.items()]))
        try:
            df2.plot(ax=axs[1], kind='bar', rot=75, fontsize=12)
            axs[1].set_title('Subsystems in level ' + str(level_number), fontsize=16)
            axs[1].set_ylabel('frequency')
        except Exception:
            axs[1].set_title('No data available', fontsize=16)

        if save_fig:
            plt.savefig('figure.png', dpi=fig_dpi, bbox_inches="tight")

    interact(plot_func,
             macrosystem=macrosystems,
             macro_freq_type=widgets.Dropdown(
                 options=[('across graph levels', 0), ('per graph level', 1)],
                 value=0,
                 description='frequency'),
             level_number=widgets.IntSlider(
                 value=0, min=0,  max=20, step=1, description='graph level', readout=True),
             save_fig=widgets.ToggleButton(
                 value=False, description='Save figure', disabled=False,
                 layout=widgets.Layout(margin='3% 0 3% 8%'))
             )


def plotLevelSubsystemsStatic(Model, graph_reactions):
    """
    Computes the frequencies of the subsystems of the reactions appearing
    in the specified graph level which have the specified macrosystem
    """
    GEM = Model.GEM
    macrosystems = ['Amino acid metabolism', 'Carbohydrate metabolism', 'Cell wall biosynthesis',
                    'Cofactor and vitamin metabolism', 'Energy and maintenance', 'Lipid metabolism',
                    'Nucleotide metabolism', 'Transport']
    macrosystem_frequencies_per_level = getSystemDistributionPerGraphLevel(
        GEM, graph_reactions, 'macrosystem')
    plt.rcParams.update({'figure.max_open_warning': 0})

    def plot_func(a_macrosystem, b_level_number):

        total_subsystems = {}
        macro_frequencies = macrosystem_frequencies_per_level
        ylabel = 'frequency in level'
        level_reactions = graph_reactions[b_level_number]
        fig, axs = plt.subplots(nrows=2, ncols=1, sharex=False, sharey=False, figsize=(14, 12))
        plt.subplots_adjust(wspace=None, hspace=0.3)

        # Plot macrosystems
        df1 = pd.DataFrame.from_dict(macro_frequencies[a_macrosystem])
        ax1 = df1.plot.bar(ax=axs[0], rot=0, fontsize=12)
        for p in ax1.patches:
            height = round(p.get_height(), 2)
            if height > 0:
                ax1.annotate(format(height, '.2f'),
                             (p.get_x() * 1.005, p.get_height() * 1.008))
        axs[0].set_title(a_macrosystem, fontsize=16)
        axs[0].set_ylabel(ylabel)
        axs[0].set_xlabel('graph level')

        # Plot subsystems
        for source in level_reactions.keys():
            subsystems = extractMetabolicSystems(GEM, level_reactions[source],
                                                 'subsystem', a_macrosystem)
            total_subsystems[source] = getListFrequencies(subsystems)

        df2 = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in total_subsystems.items()]))
        try:
            df2.plot(ax=axs[1], kind='bar', rot=75, fontsize=12)
            axs[1].set_title('Subsystems in level ' + str(b_level_number), fontsize=16)
            axs[1].set_ylabel('frequency in level')
        except Exception:
            axs[1].set_title('No data available', fontsize=16)

        return fig

    static_fig = StaticInteract(plot_func,
                                a_macrosystem=DropDownWidget(macrosystems,
                                                             description='macrosystem'),
                                b_level_number=RangeWidget(0, 20, step=1, default=0,
                                                           width=200, description='graph level'),
                                interact_name='DAG_systems'
                                )
    return static_fig


def plotTotalSystemsDistribution(Model, shared_reactions, exclusive_reactions,
                                 systemType='macrosystem',
                                 carbonSources=['glucose', 'acetate', 'glycerate']):
    """
    Generates a stacked barplot depicting the distribution of macro or subsystems found in
    the totality of the reactions present in the flux-order graph per carbon source.
    Returns the pandas dataframe employed to generate de plot.
    """
    # Compute frequencies
    GEM = Model.GEM
    total_shared_system_frequencies = getSystemFrequencies(
        GEM, shared_reactions, systemType)

    total_exclusive_system_frequencies = {}
    for carbonSource in carbonSources:
        total_exclusive_system_frequencies[carbonSource] = getSystemFrequencies(
            GEM, exclusive_reactions, systemType, carbonSource)

    # Plot stacked bar plots of total macrosystem frequencies
    df = pd.DataFrame.from_dict(total_exclusive_system_frequencies,
                                orient='index')
    df2 = pd.Series(total_shared_system_frequencies, name='Shared')
    df3 = df.append(df2, ignore_index=False)
    # Plot
    df3.plot.barh(stacked=True, rot=0, legend=False, figsize=(12, 8), fontsize=16)
    plt.xlabel('frequency', fontsize=16)
    plt.title('Macrosystems across levels', fontsize=18, pad=20)
    plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
    plt.subplots_adjust(right=0.6)
    plt.show()
    return df3


def plotNumberOfReactionsPerGraphLevel(Graph_Levels):
    """
    Plot barplot with the number of reactions per graph level for each carbon source
    """
    number_of_reactions_per_level, total_number_reactions = {}, {}
    level_with_P90_reactions = {}
    carbonSources = Graph_Levels.keys()
    max_number_of_levels = max([len(Graph_Levels[source]) for source in carbonSources])

    for carbonSource in carbonSources:
        number_of_reactions_per_level[carbonSource] = []
        total_number_reactions[carbonSource] = sum([len(Graph_Levels[carbonSource][L])
                                                    for L in Graph_Levels[carbonSource].keys()])
        for level_number in range(max_number_of_levels):
            try:
                n_reactions = len(
                    Graph_Levels[carbonSource][level_number])
            except Exception:
                n_reactions = 0
            number_of_reactions_per_level[carbonSource].append(n_reactions)
            cum_sum = sum(number_of_reactions_per_level[carbonSource])
            is_P90_level = ((cum_sum >= 0.9 * total_number_reactions[carbonSource])
                            & (carbonSource not in level_with_P90_reactions.keys()))
            if is_P90_level:
                level_with_P90_reactions[carbonSource] = level_number

    df = pd.DataFrame.from_dict(number_of_reactions_per_level)
    ax = df.plot.bar(rot=0, figsize=(12, 8))
    ax.set_xlabel('level', fontsize=16)
    ax.set_ylabel('counts', fontsize=16)
    ax.set_title('Number of reactions across DAG levels', fontsize=17, pad=20)
    # Add vertical line in level with >= 90% of reactions
    n_P90 = max(level_with_P90_reactions.values())
    x_P90_position = 1.15 * ax.patches[n_P90].get_x()
    ax.axvline(x_P90_position, color='k', linestyle='--')
    ax.text(1.1 * x_P90_position, 500, '$P_{{90}}$ (level: {})'.format(n_P90), fontsize=18)
    return df


def plotMacrosystemFrequencyPerGraphLevel(macrosystem_frequencies):
    """
    Plot barplot with the frequency of macrosystems per
    graph level for each carbon source
    """
    if isinstance(next(iter(macrosystem_frequencies.values())), dict):
        data_type = 'exclusive'
    else:
        data_type = 'shared'

    fig, axs = plt.subplots(nrows=4, ncols=2, sharex=False,
                            sharey=False, figsize=(14, 18))
    fig.text(0.5, 0.04, 'level', ha='center', fontsize=14)
    fig.text(0.04, 0.5, 'frequency per level', va='center', rotation='vertical', fontsize=14)
    fig.suptitle(('Metabolic macrosystems of '
                  + data_type
                  + ' ordered reaction pairs per hierarchy level'),
                 fontsize=14)
    plt.subplots_adjust(wspace=None, hspace=0.5)

    if data_type is 'shared':
        df = pd.DataFrame.from_dict(macrosystem_frequencies)
        if 'Unassigned' in df.columns:
            df.drop(['Unassigned'], axis=1)
        df.plot.bar(ax=axs, subplots=True, legend=False, rot=0, fontsize=8)
    else:
        i = 0
        for system in macrosystem_frequencies.keys():
            df = pd.DataFrame.from_dict(macrosystem_frequencies[system])
            if 'Unassigned' in df.columns:
                df.drop(['Unassigned'], axis=1)
            df.plot.bar(ax=axs[i // 2][i % 2], rot=0, title=system)
            i += 1


def plotOrderedCoupledPieCharts(data, ax, pie_name=None, colors=None):
    """
    Plots pie charts with the fraction of coupled reaction pairs
    """
    size = data['values']
    names = data['labels']
    _, texts = ax.pie(size, labels=names, colors=colors,
                      shadow=True, textprops={'fontsize': 14},
                      labeldistance=0.7, startangle=0,
                      explode=(0.05, 0.3, 0.1, 0.05))
    innerCircle = plt.Circle((0, 0), 0.5, color='white')
    ax.text(-0.27, 0, pie_name, {'fontsize': 16})
    for t in texts:
        t.set_fontsize(16)
    ax.add_artist(innerCircle)


def plotFractionOfCoupledOrdered(data):
    df = pd.DataFrame.from_dict(data)
    df.plot(kind='bar', rot=40, stacked=True, fontsize=18, figsize=(10, 9),
            color=['#dddddd', '#1d93f4'], legend=True)

    plt.ylabel('%', fontsize=16)
    plt.title('Ordered pairs per coupling type', fontsize=14)
    plt.xticks(np.arange(3), ('partial', 'directional'), fontsize=14)
    plt.show()


def plotOrderExample(min_flux=0, max_flux=1000, range_step=100,
                     default_value=600, description='$v_j^{ub}$'):

    def plot_example(fluxUpperBound):

        fig = plt.figure(figsize=(10, 8))
        plt.xlabel('$v_j$', fontsize=18)
        plt.ylabel('$v_i$', fontsize=18)
        x = np.linspace(0, 1000, 10)
        plt.vlines(fluxUpperBound, 1000, 0, colors='orange', linewidth=3)

        line1, = plt.plot(x, x, color='black', linestyle='--', label='$v_i=v_j$')
        line2, = plt.plot(x, 0.5*x + 200, color='blue', linewidth=3, label='$v_i=0.5v_j+200$')
        line3, = plt.plot(x, 2*x + 250, color='red', linewidth=3, label='$v_i=2v_j+250$')
        plt.ylim(0, 1000)
        plt.xlim(0, 1000)
        xfill = np.linspace(0, fluxUpperBound, 10)
        plt.fill_between(xfill, 0.5*xfill + 200, 2*xfill + 250, color='lightgrey')

        plt.legend(handles=[line1, line2, line3], loc=4, frameon=False)
        plt.text(300, 600, '$v_i>v_j$', fontsize=18)
        plt.text(600, 300, '$v_i<v_j$', fontsize=18)

        return fig

    interactive_fig = StaticInteract(plot_example,
                   fluxUpperBound=RangeWidget(min_flux, max_flux, step=range_step,
                                              default=default_value, width=200,
                                              description=description,
                                              show_range=False),
                   interact_name='plot_example'
                   )
    return interactive_fig


def plotSolutionSpace(model, v_i, v_j, v_i_max=None, n_points=100,
                      plot_diagonal=True, r_i_nickname=None, r_j_nickname=None,
                      plot_title=None):
    """
    Plots the feasible solution space of reactions v_i and v_j
    (v_i in the x axis) in a 2D plot.

    Arguments:
    ---------
    model: cobra model object, the GEM model of the system
    v_i, v_j: str or int, the reaction ids or indices in the GEM
    """
    warnings.filterwarnings('ignore')
    GEM = copy.deepcopy(model)
    rxn_i, rxn_j = GEM.reactions.get_by_any(v_i)[0], GEM.reactions.get_by_any(v_j)[0]
    if r_i_nickname is None:
        rxn_i_id = rxn_i.id
    else:
        rxn_i_id = r_i_nickname
    if r_j_nickname is None:
        rxn_j_id = rxn_j.id
    else:
        rxn_j_id = r_j_nickname
    if v_i_max is None:
        v_i_max = rxn_i.upper_bound

    GEM.objective = rxn_j
    v_i_seq = np.linspace(0, v_i_max, n_points)
    v_j_min_seq, v_j_max_seq = np.zeros(len(v_i_seq)), np.zeros(len(v_i_seq))
    for i, v in enumerate(v_i_seq):
        rxn_i.upper_bound = v
        GEM.objective.direction = 'min'
        sol_min = GEM.optimize()
        # print('min status ' + str(i) + ' ' + sol_min.status)
        if sol_min.status != 'infeasible':
            v_j_min_seq[i] = sol_min.objective_value

        GEM.objective.direction = 'max'
        sol_max = GEM.optimize()
        # print('max_status ' + str(i) + ' ' + sol_max.status)
        if sol_max.status != 'infeasible':
            v_j_max_seq[i] = sol_max.objective_value

    plt.figure(figsize=(12, 8))
    plt.xlabel('$v_{' + rxn_i_id + '}$')
    plt.ylabel('$v_{' + rxn_j_id + '}$')
    if plot_title is not None:
        plt.title(plot_title, fontsize=18)
    if plot_diagonal:
        plt.plot(v_i_seq, v_i_seq, color='green', linestyle='dashed',
                 label='$v_{' + rxn_i_id + '}= v_{' + rxn_j_id + '}$')
        plt.text(v_i_max / 3, 1.1 * v_i_max / 4,
                 '$v_{' + rxn_i_id + '}>' + 'v_{' + rxn_j_id + '}$', fontsize=18)
        plt.text(1.3 * v_i_max / 3, 3 * v_i_max / 4,
                 '$v_{' + rxn_i_id + '}<' + 'v_{' + rxn_j_id + '}$', fontsize=18)
    plt.plot(v_i_seq, v_j_min_seq, color='blue',
             label='$v^{min}_{' + rxn_j_id + '}$')
    plt.plot(v_i_seq, v_j_max_seq, color='orange',
             label='$v^{max}_{' + rxn_j_id + '}$')
    plt.fill_between(v_i_seq, v_j_min_seq, v_j_max_seq, color='lightgrey')
    plt.legend()
    plt.show()
    warnings.resetwarnings()


def plotFluxSampleOfOrderedChain(Model, ordered_chain):
    """
    Obtains a random flux sample and plots the flux values for the reactions
    in the supplied flux-ordered reaction chain. Model is a Model object from
    Model_module, ordered_chain a list with reaction ids of the cobra model.
    """
    def getLowerBound(GEM, rxn_id):
        return GEM.reactions.get_by_id(rxn_id).lower_bound

    fraction_of_optimum = 0.95
    target_rxn_id = ordered_chain[-1]
    old_rxn_lb = getLowerBound(Model.GEM, target_rxn_id)
    new_rxn_lb = fraction_of_optimum * cobra.flux_analysis.flux_variability_analysis(
        Model.GEM, reaction_list=target_rxn_id, fraction_of_optimum=0).maximum.item()
    try:
        Model.GEM.reactions.get_by_id(target_rxn_id).lower_bound = new_rxn_lb
        # fluxSample = iJO1366[example_source].getFluxSampleInRprogram(nsamples=500)
        # use this function (in R) if cobra sampling doesn't work
        fluxSample = Model.getFluxSample(nsamples=100)
    except Exception:
        print('Failed, try different lower bound')

    Model.GEM.reactions.get_by_id(target_rxn_id).lower_bound = old_rxn_lb

    # Plot flux sample for the reactions in the chain
    fluxSample[ordered_chain].transpose().plot(legend=False, figsize=(12, 8))
    plt.title('Flux sample of ordered reaction chain', fontsize=18, pad=20)
    plt.ylabel('v', fontsize=18)
    plt.xticks(range(len(ordered_chain)), ordered_chain, fontsize=16)
    plt.show()
