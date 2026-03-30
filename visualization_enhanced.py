"""
Enhanced visualization module using Plotly for interactive figures.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List, Dict

def create_interactive_evidence_heatmap(evidence_matrix: pd.DataFrame, 
                                        titles: Optional[Dict[str, str]] = None) -> go.Figure:
    """
    Create an interactive heatmap of the evidence matrix using Plotly.
    
    Args:
        evidence_matrix: DataFrame with Papers as index and KCs as columns.
                        Values should be numeric scores (e.g., 0, 1, 0.5).
        titles: Optional dictionary mapping indices (PMIDs/names) to full titles
                for tooltip display.
    
    Returns:
        Plotly Figure object
    """
    # Clean data for heatmap
    # Ensure numeric
    df = evidence_matrix.select_dtypes(include=['number'])
    
    # Prepare hover text
    hover_text = []
    for index, row in df.iterrows():
        row_text = []
        for col, val in row.items():
            title = titles.get(str(index), str(index)) if titles else str(index)
            # Truncate title if too long
            if len(title) > 50:
                title = title[:47] + "..."
                
            txt = (f"Paper: {index}<br>"
                   f"Title: {title}<br>"
                   f"KC: {col}<br>"
                   f"Score: {val}")
            row_text.append(txt)
        hover_text.append(row_text)

    # Create Heatmap
    fig = go.Figure(data=go.Heatmap(
        z=df.values,
        x=df.columns,
        y=df.index,
        text=hover_text,
        hoverinfo='text',
        colorscale='RdYlGn', # Red to Green (0 to 1)
        zmin=0,
        zmax=1,
        showscale=True
    ))

    # Update Layout
    fig.update_layout(
        title='Interactive Evidence Matrix',
        xaxis_title='Key Characteristics (KCs)',
        yaxis_title='Papers / Evidence Sources',
        xaxis={'side': 'top'}, # Put KCs on top like a standard evidence map
        height=max(400, len(df) * 30), # Adjust height based on number of papers
        margin=dict(l=150, r=50, t=100, b=50)
    )

    return fig

def create_interactive_network(nodes: List[Dict], edges: List[Dict]) -> go.Figure:
    """
    Create an interactive network graph of KC relationships.
    Placeholder for future implementation.
    """
    pass
