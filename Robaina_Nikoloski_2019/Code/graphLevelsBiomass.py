# Obtain pickle structure with graph levels for alpha = 1
if __name__ == '__main__':
    
    import numpy as np
    import copy
    import pickle
    from Model_module import Model
    from Order_module import FluxOrder
    
    # Problems:
    # With alpha=1 and glucose, the adjacency matrix produces a graph with cycles! not a DAG
    # Started: 11:30, 29 January
    
    def saveToPickleFile(python_object, path_to_file='object.pkl'):
        """
        Save python object to pickle file
        """
        out_file = open(path_to_file, 'wb')
        pickle.dump(python_object, out_file)
        out_file.close()
    
    workDir = 'C:/Users/tinta/OneDrive/Documents/Projects/Ordering_of_Fluxes'
    # Evaluate alpha = 1, alpha = 0.925
    alpha = 0.95
    iJO1366 = {}
    iJO1366_Orders = {}
    iJO1366_fctable = np.genfromtxt(workDir + '/Models/iJO1366/fc' + 'iJO1366' + '.csv', delimiter=',')
    temp = Model(fileName='iJO1366.json', workDir=workDir + '/Models/iJO1366')
    n_rxns = iJO1366_fctable.shape[0]
    
    for carbonSource in ['glucose']:
        
        print(f'Finding graph levels for source: {carbonSource} and alpha={alpha}...')
        A = np.genfromtxt(workDir + f'/Flux_order_graph_data/{carbonSource}/iJO1366_{carbonSource[:3]}_A_alpha={alpha}.csv', delimiter=',')
        temp.setCarbonSource(carbonSource, uptakeRate=20, fractionOfBiomassOptimum=alpha)
        iJO1366[carbonSource] = copy.deepcopy(temp)
        iJO1366[carbonSource].candidatePairs = np.array(np.where(A==1)).transpose()
        tempOrders = FluxOrder(iJO1366[carbonSource], A, iJO1366_fctable)
        
        # Remove possible cycles due to fully coupled pairs with ratio equal to 1
        print('Removing fully coupled pairs')
        deleted = tempOrders.removeFullyCoupledCandidatePairsWithEqualFluxes()
        print(f'There were a total of {len(deleted)} removed coupled pairs')
        true_ordered = tempOrders.Model.candidatePairs
        true_A = np.zeros_like(A)
        for pair in true_ordered:
            true_A[pair[0], pair[1]] = 1      
        
        # Check if reversible edges exist
        reversibles = 0
        for i in range(n_rxns):
            for j in range(n_rxns):
                if true_A[i,j] == 1 and true_A[j,i] == 1:
                    true_A[i,j] = 0
                    true_A[j,i] = 0
                    reversibles += 1
        print(f'There were a total of {reversibles} removed reversible edges')
        print(f'There are a total of {sum(sum(true_A))} ordered pairs left')
        
        iJO1366_Orders[carbonSource] = FluxOrder(iJO1366[carbonSource], true_A, iJO1366_fctable)        
        
        
        print(f'Getting graph levels for {carbonSource}, started at:')
        Graph_Levels = iJO1366_Orders[carbonSource].getGraph().getGraphLevels()
        
        # Save file
        saveToPickleFile(Graph_Levels, f'graph_levels_{carbonSource}_alpha={alpha}.pkl')