import pandas as pd
import collections
import re


class DataParser:
    """
    Provides methods to parse the different data sources into the
    appropriate formats
    """
    def __init__(self, Model, workDir=None):
        self.Model = Model
        if workDir is None:
            self.workDir = Model.workDir + '/Data'
        else:
            self.workDir = workDir

    def getTranscriptValues(self, carbonSources=['glucose', 'glycerate', 'acetate']):
        """
        Load data files from specified directory and extract data corresponding
        to genes in the GEM and under the specified carbon sources.
        """
        metaData = pd.read_excel(self.workDir + '/ecomics_metadata.xlsx',
                                 sheet_name='Transcriptome')

        temp = pd.read_csv(self.workDir + '/ecomics_transcriptome.txt', sep='\t').rename(
            lambda str: re.sub('m.', '', str), axis='columns')

        transcriptData = {}
        for carbonSource in carbonSources:
            if carbonSource.lower() in 'glucose':
                experimentalCondition = 'Glu'
            elif carbonSource.lower() in 'glycerate':
                experimentalCondition = 'Gly'
            elif carbonSource.lower() in 'acetate':
                experimentalCondition = 'Ace'
            transcriptData[carbonSource] = temp.loc[temp['ID'].isin(metaData[
                                    (metaData['Stress'] == 'none')
                                    & (metaData['GP Type'] == 'WT')
                                    & (metaData['Carbon'] == experimentalCondition)
                                    & (metaData['Strain Name'] == 'MG1655')]
                                    ['ID'])][temp.columns.intersection(
                                        self.Model.geneIDs)].mean().dropna()
            transcriptData[carbonSource].type = 'gene'
            transcriptData[carbonSource].carbonSource = carbonSource
            transcriptData[carbonSource].name = 'Transcript data' + ' (' + carbonSource + ')'

        return transcriptData

    def getProteinValues(self, carbonSources=['glucose', 'glycerate', 'acetate']):
        """
        Load data files from specified directory and extract data corresponding
        to reactions in the GEM (specific activities only available for growth
        on glucose). Original values are measured in
        mmol/gDW, here converted to nanomol/gDW.
        """
        temp = pd.read_excel(self.workDir + '/kcat_activity_protein_data.xlsx',
                             sheet_name='abundance mmolgCDW', header=2)

        proteinData = {}
        for carbonSource in carbonSources:
            experimentalCondition = self.__getProteinDataCondition(carbonSource)
            tempSeries = 1e6*pd.Series(data=dict(zip(temp['bnumber'], temp.filter(
                regex=experimentalCondition).mean(axis=1)))).dropna()
            tempSeries = tempSeries[tempSeries.index.intersection(self.Model.geneIDs)]
            proteinData[carbonSource] = tempSeries
            proteinData[carbonSource].type = 'gene'
            proteinData[carbonSource].carbonSource = carbonSource
            proteinData[carbonSource].name = 'Protein data' + ' (' + carbonSource + ')'

        return proteinData

    def __getProteinDataCondition(self, carbonSource):
            carbonSource = carbonSource.lower()
            if carbonSource in 'glucose':
                cond = 'GLC_'
            elif carbonSource in 'glycerate':
                cond = 'GLYC_'
            elif carbonSource in 'acetate':
                cond = 'ACE_'
            return cond

    def getProteinCosts(self):
        return pd.read_excel(self.workDir + '/protein_costs.xlsx',
                             sheet_name='ProteinDataClean', header=0)

    def getFluxValues(self):
        """
        Load data files from specified directory and extract data corresponding
        to reactions in the GEM (only growth on glucose available).
        """
        temp = pd.read_excel(self.workDir + '/ecomics_fluxome.xlsx')
        ecomicsIDs = pd.read_excel(self.workDir + '/ecomics_fluxome_rxn_ids.xlsx')

        ecomics2BIGG = {}
        for rxnID, BIGGID in zip(ecomicsIDs['Rxn #'], ecomicsIDs['BiGG ID']):
            if (BIGGID != 'na') and (BIGGID in self.Model.getReactionIDs()):
                ecomics2BIGG[rxnID] = BIGGID

        fluxData = temp[temp.columns.intersection(ecomics2BIGG.keys())].rename(
            index=str, columns=ecomics2BIGG).mean().dropna()

        # Check for reactions going in reverse in data
        for rxn, value in fluxData.items():
            if value < 0:
                fluxData.rename({rxn: rxn + '_reverse'}, inplace=True)

        fluxData.type = 'reaction'
        fluxData.carbonSource = 'glucose'
        fluxData.name = 'Flux data' + ' (glucose)'

        return fluxData

    def getKcatValues(self):
        """
        Loads data files from specified directory and extract data corresponding
        to reactions in the GEM (specific activities only available for growth
        on glucose).
        """
        temp = pd.read_excel(self.workDir + '/kcat_activity_protein_data.xlsx',
                             sheet_name='kcat 1s', header=2)

        temp['Kcat'] = (temp['kcat per active site [1/s]']
                        * temp['catalytic sites per complex'])
        KcatData = pd.Series(data=dict(zip(temp['reaction (model name)'],
                                           temp['Kcat']))).dropna()
        KcatData = KcatData[KcatData.index.intersection(self.Model.getReactionIDs())]
        KcatData.type = 'reaction'
        KcatData.carbonSource = ''
        KcatData.name = 'Kcat values'

        return KcatData

    def getActivityValues(self):
        """
        Loads data files from specified directory and extract data corresponding
        to reactions in the GEM (specific activities only available
        for growth on glucose).
        """
        temp = pd.read_excel(self.workDir + '/kcat_activity_protein_data.xlsx',
                             sheet_name='kmax umolmgmin', header=3)

        condition = 'GLC_CHEM'  # Chemostat with any glucose intake rate
        temp = temp[temp.condition.str.contains(condition, case=False)]

        activityData = pd.Series(data=dict(zip(temp['reaction (model name)'],
                                               temp['kmax [umol/mg/min]']))).dropna()
        activityData = activityData[
            activityData.index.intersection(self.Model.getReactionIDs())]
        activityData.type = 'reaction'
        activityData.carbonSource = 'glucose'
        activityData.name = 'Specific activity' + ' (glucose)'

        return activityData

    def getGeneRegulatoryInteractions(self, dataset='RegulonDB',
                                      only_strong_confidence=True):
        """
        Loads data file from specied directory and extract TF-gene
        interactions for E.coli Data obtained from the RegulonDB
        database, Gama-Castro S et al. (2016)
        """
        if not hasattr(self, 'geneDictionary'):
            self.geneDictionary = self.__buildGeneDictionary()

        if only_strong_confidence:
            selected = ['Strong', 'Confirmed']
        else:
            selected = ['Weak', 'Strong', 'Confirmed']

        dataset = dataset.lower()
        if dataset in 'regulondb':
            temp = pd.read_excel(self.workDir + '/RegulonDB_TF_gene.xlsx')
            totalGenes = temp['Target'][temp['Confidence'].isin(selected)].values
            tempDict = collections.Counter(totalGenes)
            tempDict = {self.geneDictionary[geneName]: tempDict[geneName]
                        for geneName in tempDict.keys()
                        if geneName in self.geneDictionary.keys()}
        elif dataset in 'ecolinet':
            temp = pd.read_table(self.workDir + '/EcoliNet.v1.txt', header=None)
            totalGenes = temp[1].values
            tempDict = collections.Counter(totalGenes)

        numberOfInteractions = pd.Series(data=tempDict).dropna()
        numberOfInteractions = numberOfInteractions[
            numberOfInteractions.index.intersection(self.Model.geneIDs)]
        numberOfInteractions.type = 'gene'
        numberOfInteractions.name = 'Number of Gene Regulatory Interactions'

        return numberOfInteractions

    def __buildGeneDictionary(self):
        temp = pd.read_excel(self.workDir + '/geneDictionary.xlsx').dropna()
        geneDictionary = {}
        for geneID in temp['Locus ID']:
            geneNames = temp['Gene name'][
                temp['Locus ID'] == geneID].item().replace(' ', '').split(';')
            for geneName in geneNames:
                geneDictionary[geneName] = geneID
        return geneDictionary
