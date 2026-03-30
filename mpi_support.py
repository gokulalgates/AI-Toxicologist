"""
MPI (Message Passing Interface) support for distributed computing.

Optional module for running across multiple nodes/machines.
Requires: pip install mpi4py
"""

try:
    # Try to import MPI - catch both ImportError and OSError (library not found)
    from mpi4py import MPI
    MPI_AVAILABLE = True
except (ImportError, OSError, RuntimeError):
    # OSError: libmpi.so not found
    # RuntimeError: MPI initialization failed
    # ImportError: mpi4py not installed
    MPI_AVAILABLE = False
    MPI = None
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)

from typing import Any, Dict, List


def is_mpi_available() -> bool:
    """Check if MPI is available"""
    return MPI_AVAILABLE


def get_mpi_comm():
    """Get MPI communicator if available"""
    if not MPI_AVAILABLE:
        return None
    return MPI.COMM_WORLD


def get_mpi_rank() -> int:
    """Get MPI rank (process ID)"""
    if not MPI_AVAILABLE:
        return 0
    return MPI.COMM_WORLD.Get_rank()


def get_mpi_size() -> int:
    """Get MPI size (total number of processes)"""
    if not MPI_AVAILABLE:
        return 1
    return MPI.COMM_WORLD.Get_size()


def distribute_work_mpi(items: List[Any]) -> List[Any]:
    """
    Distribute work items across MPI processes.
    
    Args:
        items: List of items to process
    
    Returns:
        List of items assigned to this process
    """
    if not MPI_AVAILABLE:
        return items

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Distribute items across processes
    items_per_process = len(items) // size
    remainder = len(items) % size

    start_idx = rank * items_per_process + min(rank, remainder)
    end_idx = start_idx + items_per_process + (1 if rank < remainder else 0)

    return items[start_idx:end_idx]


def gather_results_mpi(results: List[Any]) -> List[Any]:
    """
    Gather results from all MPI processes.
    
    Args:
        results: Results from this process
    
    Returns:
        Combined results from all processes (only on rank 0)
    """
    if not MPI_AVAILABLE:
        return results

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    # Gather all results to rank 0
    all_results = comm.gather(results, root=0)

    if rank == 0:
        # Flatten and return combined results
        combined = []
        for r in all_results:
            combined.extend(r)
        return combined
    else:
        return []


def run_mpi_analysis(abstracts: List[Dict], model_name: str, analysis_func) -> List[Dict]:
    """
    Run analysis using MPI for distributed processing.
    
    Args:
        abstracts: List of abstracts to analyze
        model_name: Model name to use
        analysis_func: Function to analyze single abstract
    
    Returns:
        List of analysis results (only on rank 0)
    """
    if not MPI_AVAILABLE:
        # Fallback to regular processing
        return [analysis_func(abstract, model_name) for abstract in abstracts]

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Distribute abstracts across processes
    local_abstracts = distribute_work_mpi(abstracts)

    # Process local abstracts
    local_results = []
    for abstract in local_abstracts:
        result = analysis_func(abstract, model_name)
        local_results.append(result)

    # Gather results from all processes
    all_results = comm.gather(local_results, root=0)

    if rank == 0:
        # Combine and return results
        combined = []
        for r in all_results:
            combined.extend(r)
        return combined
    else:
        return []


def print_mpi_info():
    """Print MPI information"""
    if MPI_AVAILABLE:
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
        size = comm.Get_size()
        print(f"MPI: Rank {rank}/{size-1} of {size} processes")
    else:
        print("MPI not available. Install with: pip install mpi4py")
