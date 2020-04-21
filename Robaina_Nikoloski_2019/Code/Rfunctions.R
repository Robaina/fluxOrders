FVA <- function(S, rxns=NULL, v_lb=NULL, v_ub=NULL, round_decimals=4){

  # Computes the minimum and maximum flux ranges of a set of reactions
  #
  # Arguments
  #    S: the stoichiometric matrix of the GEM to be evaluated
  #    rxns: an array with reaction indexes to be evaluated. If left empty then
  #          computes flux ranges for all reactions.
  #    v_lb: an array with the lower flux bounds of the reactions in the GEM
  #    v_ub: an array with the upper flux bounds of the reactions in the GEM
  #    round_decimals: an integer representing the number of decimals to which
  #          the flux values are to be rounded.
  #
  # Returns
  #    List with fields
  #    FVArange: a matrix with rows representing reactions (in rxns) and columns
  #              representing the min and max flux value
  #    FVAmin:   a matrix containing all the optimal flux vectors corresponding
  #              to each optimal minimum flux value in FVArange
  #    FVAmax:   a matrix containing all the optimal flux vectors corresponding
  #              to each optimal maximum flux value in FVArange
  #
  # Dependencies:
  #    Requires a working installation of the Gurobi solver
  #    (https://www.gurobi.com, free academic licences) and the R
  #    library "gurobi". This program was written for Gurobi 7.0.2
  #
  # Semidan Robaina-Estevez, June 2018.


  library(gurobi)

  n_mets <- nrow(S)
  n_rxns <- ncol(S)

  # Prepare solver model
  if (is.null(v_lb)){
    v_lb <- rep(0, n_rxns)
  }

  if (is.null(v_ub)){
    v_ub <- rep(1e3, n_rxns)
  }

  if (is.null(rxns)){
    rxns <- 1:n_rxns
  }

  n_evrxns <- length(rxns)
  rhsvec <- rep(0, n_mets)
  sense <- rep("=", n_mets)

  # Prepare gurobi input
  model <- list()
  params <- list()
  model$A <- S
  model$sense <- sense
  model$rhs <- rhsvec
  model$lb <- v_lb
  model$ub <- v_ub
  params$OutputFlag <- 0

  FVArange <- matrix(0, n_evrxns, 2)
  FVAmin <- FVAmax <- matrix(0, n_rxns, n_evrxns)
  print("Running flux variability analyis...")
  pb <- txtProgressBar(min = 0, max = n_evrxns, style = 3)
  n <- 1
  # Loop over reactions in the GEM
  for (rxn in rxns){

    setTxtProgressBar(pb, rxn)
    cvec <- rep(0, n_rxns);
    cvec[rxn] <- 1
    model$obj <- cvec

    # Handle possible infeasibilities
    tryCatch({
      model$modelsense <- "min"
      gurmin <- gurobi(model, params)

      model$modelsense <- "max"
      gurmax <- gurobi(model, params)


      FVArange[n, 1] <- gurmin$objval
      FVArange[n, 2] <- gurmax$objval
      FVAmin[, n] <- gurmin$x
      FVAmax[, n] <- gurmax$x
      n <- n + 1

    },

    error = function(e){
    })

  }
  close(pb)
  sol <- list()
  sol$FVArange <- round(FVArange, round_decimals)
  sol$FVAmin <- round(FVAmin, round_decimals)
  sol$FVAmax <- round(FVAmax, round_decimals)
  return(sol)

}


sampleFluxCone <- function(S, n_samples = 100, v_lb = NULL,
   v_ub = NULL, round_decimals=4){

  # Computes the minimum and maximum flux ranges of a set of reactions
  #
  # Arguments
  #    S: the stoichiometric matrix of the GEM to be evaluated
  #    n_samples: integer, number of samples
  #    v_lb: an array with the lower flux bounds of the reactions in the GEM
  #    v_ub: an array with the upper flux bounds of the reactions in the GEM
  #    round_decimals: an integer representing the number of decimals to which
  #          the flux values are to be rounded.
  #
  # Returns
  #  v_sample: a 2D array with the flux samples, rows are reactions and columns sampled
  #  reaction vectors.
  #
  # Dependencies:
  #    Requires a working installation of the Gurobi solver
  #    (https://www.gurobi.com, free academic licences) and the R
  #    library "gurobi"
  #
  # Semidan Robaina-Estevez, June 2018.

  library(gurobi)

  n_mets <- nrow(S)
  n_rxns <- ncol(S)

  # Sample the flux cone of a GEM: x = {v,epsilon}
  model <- list()
  params <- list()
  model$A <- rbind(cbind(S, matrix(0, n_mets, n_rxns)), cbind(diag(n_rxns), diag(n_rxns)))

  if (is.null(v_lb)){
     v_lb <- rep(0, n_rxns)
  }

  if (is.null(v_ub)){
    v_ub <- rep(1e3, n_rxns)
  }

  model$lb <- c(v_lb, rep(-1e6, n_rxns))
  model$ub <- c(v_ub, rep(1e6, n_rxns))
  model$sense <- rep("=", n_mets + n_rxns)
  model$obj <- rep(0, 2 * n_rxns)
  model$Q <- rbind(matrix(0, n_rxns, 2 * n_rxns), cbind(matrix(0, n_rxns, n_rxns), diag(n_rxns)))
  model$modelsense <- "min"
  params$OutputFlag <- 0

  pb <- txtProgressBar(min = 1, max = n_samples, style = 3)
  v_sample <- matrix(0, n_rxns, n_samples)

  # Start loop to generate flux sample
  print("Sampling the flux cone...")

  for (n in 1:n_samples){

    setTxtProgressBar(pb, n)

    # Generate random point
    v_rand <- (v_ub - v_lb) * runif(n_rxns) + v_lb
    model$rhs <- c(rep(0, n_mets), v_rand)

    # Find closest flux vector at steady-state
    # if (round(gurmax$objval, 4) <= 1 & gurmax$status == "OPTIMAL")
    tryCatch({

      gur <- gurobi(model, params)
      v_sample[, n] <- gur$x[1:n_rxns]
    },

    error = function(e){

    })

  }
  close(pb)

  # Round to n decimal places to avoid numerical issues
  v_sample <- round(v_sample, round_decimals)

  return(v_sample)

}


get_flux_orders <- function(S, dx_eps=0, v_lb=NULL, v_ub=NULL, ncores=NULL,
                           fileDir=NULL, fileName=NULL, candidatePairs=NULL,
                           use_ratio_as_weights=FALSE){

  # Evaluates whether there exists reaction pairs i,j whose flux values
  # satisfy v_i > v_j for all v: -dx_eps <= Sv <= dx_eps. To this end, the ratio
  # v_j / v_i is maximized over the flux cone. The linear-fractional program is
  # first Charnes-Cooper transformed into a linear program.
  #
  # Arguments:
  #   S: the stoichiometric matrix S of the GEM with split reversible reactions.
  #   v_lb: flux lower bound for the reactions in the GEM (array, default 0)
  #   v_ub: flux upper bound for the reactions in the GEM (array, default 1000)
  #   v_eps: threshold to effective 0 flux value (number, default 1e-9)
  #   dx_eps: maximum deviation from steady-state (number, default 0)
  #   fileDir: a string with the directory to which the output file should be
  #   saved.
  #   ncores: an integer indicating the number of cores to be used in the
  #   parallelization (default uses all cores detected)
  #   fileName: the name of the file containing the adjacency matrix
  #   candidatePairs: a 2xn array containing n candidate pairs to be evaluated
  #   use_ratio_as_weights: true or false, if true then the entries in the
  #   adjacency matrix are the minimum flux ratios v_i / v_j
  #
  # Returns:
  #   A: an adjacency matrix of the Hasse diagram containing the order relations
  #   between pair of reactions. Entry ij (row,column) = 1 if v_i >= v_j and 0
  #   otherwise.
  #
  # Dependencies:
  #    Requires a working installation of the Gurobi solver
  #    (https://www.gurobi.com) and the R libraries gurobi, doParallel,
  #    foreach and parallel.
  #
  #
  # Example:
  #   S = as.matrix(read.table(file = 'S.csv', sep = ","))
  #   lb = as.matrix(read.table(file = 'lb.csv', sep = ","))
  #   ub = as.matrix(read.table(file = 'ub.csv', sep = ","))
  #   candPairs = as.matrix(read.table(file = 'candidatePairs.csv', sep = ","))
  #
  #   sol = get_flux_orders(S=S, v_lb=lb, v_ub=ub, candidatePairs=candPairs,
  #                         ncores=8, fileDir=WorkDir, fileName="EvAraModel_AdjMat")
  #
  # Semidan Robaina-Estevez, May 2018

  library(gurobi)
  library(Matrix)
  library(doParallel)
  library(foreach)
  library(parallel)

  # Evaluate arguments
  nrxns <- ncol(S)
  nmets <- nrow(S)

  if (is.null(v_lb)){
    v_lb <- rep(0, nrxns)
  }

  if (is.null(v_ub)){
    v_ub <- rep(1e3, nrxns)
  }

  if (is.null(ncores)){
    ncores <- detectCores()
  }

  if (is.null(candidatePairs)){
    rxn_pairs <- cbind(combn(1:nrxns, 2), combn(nrxns:1, 2))
  }
  else if (!is.null(candidatePairs)){
    if (ncol(candidatePairs) == 2){candidatePairs = t(candidatePairs)}
    rxn_pairs <- candidatePairs
  }

  # Initialize LP problem (Charnes-Cooper transformation)
  if (dx_eps == 0){
    sense <- c(rep("=", nmets), rep("<", nrxns), rep(">", nrxns), "=")
    rhsvec <- c(rep(0, nmets), rep(0, 2 * nrxns), 1)
    A11 <- cbind(S, rep(0, nmets))
    A12 <- rbind(cbind(diag(nrxns), -v_ub), cbind(diag(nrxns), -v_lb))
    A1 <- rbind(A11, A12)

  }

  else if (dx_eps > 0){
    sense <- c(rep("<", nmets), rep(">", nmets), rep("<", nrxns),
     rep(">", nrxns), "=")
    rhsvec <- c(rep(dx_eps, nmets), rep(-dx_eps, nmets), rep(0, 2 * nrxns), 1)
    A11 <- rbind(cbind(S, rep(0, nmets)), cbind(S, rep(0, nmets)))
    A12 <- rbind(cbind(diag(nrxns), -v_ub), cbind(diag(nrxns), -v_lb))
    A1 <- rbind(A11, A12)

  }

  # Prepare gurobi input
  model <- list()
  params <- list()
  model$sense <- sense
  model$rhs <- rhsvec
  model$lb <- rep(0, nrxns + 1)
  model$ub <- rep(1e9, nrxns + 1)
  model$modelsense <- "max"
  params$OutputFlag <- 0

  # Register parallel backend
  cl <- makeCluster(ncores)
  registerDoParallel(cl)

  # Obtain reaction pairs
  npairs <- ncol(rxn_pairs)
  pairs_sub <- rep(0, npairs)
  for (n in 1:npairs){
    pairs_sub[n] <- (rxn_pairs[2, n] - 1) * nrxns + rxn_pairs[1, n]
  }

  # Loop over reaction pairs to find order relations
  new_edge <- vector()

  edge_data <- foreach(n = 1:npairs, .combine = rbind,
                   .packages = "gurobi", .errorhandling = "remove") %dopar% {

    idx <- ((pairs_sub[n] - 1) %% nrxns) + 1
    jdx <- floor((pairs_sub[n] - 1) / nrxns) + 1

    # Variables, vector W and scalar t
    cvec <- rep(0, nrxns + 1)
    cvec[jdx] <- 1
    A2 <- rep(0, nrxns + 1)
    A2[idx] <- 1
    model$A <- rbind(A1, A2)
    model$obj <- cvec

    # Solve LP
    gurmax = gurobi(model, params)
    maximum_ratio <- round(gurmax$objval, 4)

    # If candidate pairs is null, check also for minimum ratio to discard fully coupled pairs
    if (is.null(candidatePairs)){
      model$obj <- -model$obj
      gurmin <- gurobi(model, params)
      minimum_ratio <- round(-gurmin$objval, 4)
      if (maximum_ratio <=1 & minimum_ratio != 1 & gurmax$status == "OPTIMAL") {
        new_edge <- c(idx, jdx, 1 / maximum_ratio)
      }
      else {
        new_edge <- NULL
      }
    }
    else {
      if (maximum_ratio <= 1 & gurmax$status == "OPTIMAL"){
        new_edge <- c(idx, jdx, 1 / maximum_ratio)
      }
      else {
        new_edge <- NULL
      }
    }

    return(new_edge)
  }
  stopCluster(cl)

  # Build adjacency matrix
  AdjMat <- matrix(data = 0, nrow = nrxns, ncol = nrxns)
  edges <- vector()
  weights <- vector()
  if (length(edge_data) > 0) {
    for (idx in 1:nrow(edge_data)) {
       edges <- rbind(edges, edge_data[idx, 1:2])
       weights[idx] <- edge_data[idx, 3]
    }
  
    if (use_ratio_as_weights) {
      AdjMat[edges] <- weights
    } else {
      AdjMat[edges] <- 1
    }
  }

  # Remove entries corresponding to inactivated exchanges (provisional)
  Inactive_exchanges <- which(v_lb == 0 & v_ub == 0)
  AdjMat[Inactive_exchanges, ] <- 0
  AdjMat[, Inactive_exchanges] <- 0

  # Save adjacency matrix to csv
  if (!is.null(fileDir) & !is.null(fileName)){
    write.table(as.matrix(AdjMat), file = paste0(fileDir,"/", fileName,".csv"),
                sep = ",", row.names = FALSE, col.names = FALSE)
  }

  return(as.matrix(AdjMat))

}


#start = Sys.time()
#sol = get_flux_orders(S = S, v_lb = lb, v_ub = ub, candidatePairs = candidatePairs, fileDir = getwd(), fileName = "A_gly_bio_0925")
#end = Sys.time()
#print(end - start)
#print(sum(rowSums(sol)))
#rm(sol)

"S = data.matrix(read.csv(file = 'iJO1366_S_0.925_glycerate.csv', sep = ',', header = FALSE))
lb = data.matrix(read.csv(file = 'iJO1366_lb_0.925_glycerate.csv', sep = ',', header = FALSE))
ub = data.matrix(read.csv(file = 'iJO1366_ub_0.925_glycerate.csv', sep = ',', header = FALSE))
candidatePairs = data.matrix(read.csv(file = 'iJO1366_candidatePairs_0.925_glycerate.csv', header = FALSE, sep = ','))
"
