"""
Utilities for saving plots and figures to disk.
"""

import os
from datetime import datetime
from typing import Optional

import matplotlib.pyplot as plt


def save_plot(fig: plt.Figure, filename: str, output_dir: str = "results",
              chemical_name: Optional[str] = None, dpi: int = 300,
              formats: list = ['png', 'pdf']) -> dict:
    """
    Save a matplotlib figure to disk in multiple formats.
    
    Args:
        fig: Matplotlib figure to save
        filename: Base filename (without extension)
        output_dir: Base output directory
        chemical_name: Chemical name for subdirectory organization
        dpi: Resolution for raster formats
        formats: List of formats to save ('png', 'pdf', 'svg', 'jpg')
    
    Returns:
        Dict with saved file paths
    """
    saved_files = {}

    # Create output directory
    if chemical_name:
        safe_name = "".join(c for c in chemical_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        chem_dir = os.path.join(output_dir, safe_name)
    else:
        chem_dir = output_dir

    os.makedirs(chem_dir, exist_ok=True)

    # Create subdirectory for plots
    plots_dir = os.path.join(chem_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # Add timestamp to filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{filename}_{timestamp}"

    # Save in each requested format
    for fmt in formats:
        if fmt.lower() == 'png':
            filepath = os.path.join(plots_dir, f"{base_filename}.png")
            fig.savefig(filepath, dpi=dpi, bbox_inches='tight', format='png')
            saved_files['png'] = filepath
        elif fmt.lower() == 'pdf':
            filepath = os.path.join(plots_dir, f"{base_filename}.pdf")
            fig.savefig(filepath, bbox_inches='tight', format='pdf')
            saved_files['pdf'] = filepath
        elif fmt.lower() == 'svg':
            filepath = os.path.join(plots_dir, f"{base_filename}.svg")
            fig.savefig(filepath, bbox_inches='tight', format='svg')
            saved_files['svg'] = filepath
        elif fmt.lower() == 'jpg' or fmt.lower() == 'jpeg':
            filepath = os.path.join(plots_dir, f"{base_filename}.jpg")
            fig.savefig(filepath, dpi=dpi, bbox_inches='tight', format='jpg')
            saved_files['jpg'] = filepath

    return saved_files


def save_all_plots(heatmap_fig: Optional[plt.Figure] = None,
                   network_fig: Optional[plt.Figure] = None,
                   prisma_fig: Optional[plt.Figure] = None,
                   rob_heatmap_fig: Optional[plt.Figure] = None,
                   rob_summary_fig: Optional[plt.Figure] = None,
                   output_dir: str = "results",
                   chemical_name: Optional[str] = None,
                   dpi: int = 300) -> dict:
    """
    Save all plots from an analysis session.
    
    Args:
        heatmap_fig: Evidence matrix heatmap figure
        network_fig: Causal pathway network figure
        prisma_fig: PRISMA flow diagram figure
        rob_heatmap_fig: Risk-of-bias heatmap figure
        rob_summary_fig: Risk-of-bias summary figure
        output_dir: Base output directory
        chemical_name: Chemical name for subdirectory
        dpi: Resolution for raster formats
    
    Returns:
        Dict with all saved file paths
    """
    all_saved = {}

    if heatmap_fig:
        try:
            saved = save_plot(heatmap_fig, "evidence_matrix_heatmap",
                            output_dir, chemical_name, dpi)
            all_saved['heatmap'] = saved
            print(f"Saved evidence matrix heatmap: {saved.get('png', 'N/A')}")
        except Exception as e:
            print(f"Warning: Could not save heatmap: {e}")

    if network_fig:
        try:
            saved = save_plot(network_fig, "causal_pathway_network",
                            output_dir, chemical_name, dpi)
            all_saved['network'] = saved
            print(f"Saved causal pathway network: {saved.get('png', 'N/A')}")
        except Exception as e:
            print(f"Warning: Could not save network graph: {e}")

    if prisma_fig:
        try:
            saved = save_plot(prisma_fig, "prisma_flow_diagram",
                            output_dir, chemical_name, dpi)
            all_saved['prisma'] = saved
            print(f"Saved PRISMA flow diagram: {saved.get('png', 'N/A')}")
        except Exception as e:
            print(f"Warning: Could not save PRISMA diagram: {e}")

    if rob_heatmap_fig:
        try:
            saved = save_plot(rob_heatmap_fig, "risk_of_bias_heatmap",
                            output_dir, chemical_name, dpi)
            all_saved['rob_heatmap'] = saved
            print(f"Saved risk-of-bias heatmap: {saved.get('png', 'N/A')}")
        except Exception as e:
            print(f"Warning: Could not save RoB heatmap: {e}")

    if rob_summary_fig:
        try:
            saved = save_plot(rob_summary_fig, "risk_of_bias_summary",
                            output_dir, chemical_name, dpi)
            all_saved['rob_summary'] = saved
            print(f"Saved risk-of-bias summary: {saved.get('png', 'N/A')}")
        except Exception as e:
            print(f"Warning: Could not save RoB summary: {e}")

    return all_saved
