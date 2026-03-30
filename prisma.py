"""
PRISMA 2020 flow diagram and reporting
"""

from typing import List, Dict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from evidence_models import PRISMARecord


def create_prisma_flow_diagram(prisma_record: PRISMARecord) -> plt.Figure:
    """
    Create PRISMA 2020 flow diagram
    """
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.axis('off')
    
    # Colors
    box_color = '#E8F4F8'
    arrow_color = '#333333'
    
    # Box dimensions
    box_width = 8
    box_height = 0.8
    box_spacing = 1.2
    
    y_start = 13
    
    # Identification
    id_box = mpatches.FancyBboxPatch(
        (1, y_start), box_width, box_height,
        boxstyle="round,pad=0.1", 
        facecolor=box_color, edgecolor='black', linewidth=1.5
    )
    ax.add_patch(id_box)
    ax.text(5, y_start + box_height/2, 
            f"Records identified\n(n={prisma_record.total_records_identified})",
            ha='center', va='center', fontsize=10, weight='bold')
    
    # Databases searched
    y = y_start - box_spacing
    db_text = f"Databases searched: {', '.join(prisma_record.databases_searched)}"
    ax.text(5, y, db_text, ha='center', fontsize=9, style='italic')
    
    # Duplicates removed
    y -= box_spacing * 0.8
    dup_box = mpatches.FancyBboxPatch(
        (1, y - box_height/2), box_width, box_height,
        boxstyle="round,pad=0.1",
        facecolor=box_color, edgecolor='black', linewidth=1.5
    )
    ax.add_patch(dup_box)
    ax.text(5, y, 
            f"Duplicates removed\n(n={prisma_record.duplicates_removed})",
            ha='center', va='center', fontsize=10)
    
    # Arrow down
    ax.arrow(5, y - box_height/2 - 0.1, 0, -0.3, 
             head_width=0.3, head_length=0.1, fc=arrow_color, ec=arrow_color)
    
    # Records screened
    y -= box_spacing
    screen_box = mpatches.FancyBboxPatch(
        (1, y - box_height/2), box_width, box_height,
        boxstyle="round,pad=0.1",
        facecolor=box_color, edgecolor='black', linewidth=1.5
    )
    ax.add_patch(screen_box)
    ax.text(5, y,
            f"Records screened\n(n={prisma_record.records_screened_title_abstract})",
            ha='center', va='center', fontsize=10, weight='bold')
    
    # Arrow down
    ax.arrow(5, y - box_height/2 - 0.1, 0, -0.3,
             head_width=0.3, head_length=0.1, fc=arrow_color, ec=arrow_color)
    
    # Excluded (title/abstract)
    y -= box_spacing
    excl_box = mpatches.FancyBboxPatch(
        (1, y - box_height/2), box_width/2 - 0.5, box_height,
        boxstyle="round,pad=0.1",
        facecolor='#FFE6E6', edgecolor='black', linewidth=1.5
    )
    ax.add_patch(excl_box)
    ax.text(2.5, y,
            f"Records excluded\n(n={prisma_record.records_excluded_title_abstract})",
            ha='center', va='center', fontsize=9)
    
    # Sought for retrieval
    sought_box = mpatches.FancyBboxPatch(
        (box_width/2 + 1.5, y - box_height/2), box_width/2 - 0.5, box_height,
        boxstyle="round,pad=0.1",
        facecolor=box_color, edgecolor='black', linewidth=1.5
    )
    ax.add_patch(sought_box)
    ax.text(6.5, y,
            f"Records sought for retrieval\n(n={prisma_record.records_sought_full_text})",
            ha='center', va='center', fontsize=9)
    
    # Arrow from excluded to right
    ax.arrow(box_width/2 + 1.5, y - box_height/2 - 0.1, 0, -0.3,
             head_width=0.3, head_length=0.1, fc=arrow_color, ec=arrow_color)
    
    # Not retrieved
    y -= box_spacing
    not_ret_box = mpatches.FancyBboxPatch(
        (box_width/2 + 1.5, y - box_height/2), box_width/2 - 0.5, box_height,
        boxstyle="round,pad=0.1",
        facecolor='#FFE6E6', edgecolor='black', linewidth=1.5
    )
    ax.add_patch(not_ret_box)
    ax.text(6.5, y,
            f"Records not retrieved\n(n={prisma_record.records_not_retrieved})",
            ha='center', va='center', fontsize=9)
    
    # Assessed for eligibility
    y -= box_spacing
    assess_box = mpatches.FancyBboxPatch(
        (box_width/2 + 1.5, y - box_height/2), box_width/2 - 0.5, box_height,
        boxstyle="round,pad=0.1",
        facecolor=box_color, edgecolor='black', linewidth=1.5
    )
    ax.add_patch(assess_box)
    ax.text(6.5, y,
            f"Records assessed for eligibility\n(n={prisma_record.records_assessed_full_text})",
            ha='center', va='center', fontsize=9, weight='bold')
    
    # Arrow down
    ax.arrow(6.5, y - box_height/2 - 0.1, 0, -0.3,
             head_width=0.3, head_length=0.1, fc=arrow_color, ec=arrow_color)
    
    # Excluded (full text)
    y -= box_spacing
    excl_ft_box = mpatches.FancyBboxPatch(
        (box_width/2 + 1.5, y - box_height/2), box_width/2 - 0.5, box_height,
        boxstyle="round,pad=0.1",
        facecolor='#FFE6E6', edgecolor='black', linewidth=1.5
    )
    ax.add_patch(excl_ft_box)
    excl_reasons = "\n".join([f"{k}: {v}" for k, v in list(prisma_record.exclusion_reasons.items())[:3]])
    ax.text(6.5, y,
            f"Records excluded\n(n={prisma_record.records_excluded_full_text})\n{excl_reasons}",
            ha='center', va='center', fontsize=8)
    
    # Included
    y -= box_spacing
    incl_box = mpatches.FancyBboxPatch(
        (box_width/2 + 1.5, y - box_height/2), box_width/2 - 0.5, box_height,
        boxstyle="round,pad=0.1",
        facecolor='#E6FFE6', edgecolor='black', linewidth=2
    )
    ax.add_patch(incl_box)
    ax.text(6.5, y,
            f"Studies included\n(n={prisma_record.studies_included})",
            ha='center', va='center', fontsize=10, weight='bold')
    
    # Title
    ax.text(5, 14, f"PRISMA 2020 Flow Diagram\n{prisma_record.chemical_name}",
            ha='center', fontsize=12, weight='bold')
    
    plt.tight_layout()
    return fig


def generate_prisma_text_summary(prisma_record: PRISMARecord) -> str:
    """
    Generate text summary of PRISMA flow
    """
    summary = f"""
PRISMA 2020 Flow Summary for {prisma_record.chemical_name}
{'='*60}

IDENTIFICATION:
- Databases searched: {', '.join(prisma_record.databases_searched)}
- Total records identified: {prisma_record.total_records_identified}
- Duplicates removed: {prisma_record.duplicates_removed}

SCREENING:
- Records screened (title/abstract): {prisma_record.records_screened_title_abstract}
- Records excluded (title/abstract): {prisma_record.records_excluded_title_abstract}
- Records sought for retrieval: {prisma_record.records_sought_full_text}
- Records not retrieved: {prisma_record.records_not_retrieved}

ELIGIBILITY:
- Records assessed for eligibility: {prisma_record.records_assessed_full_text}
- Records excluded (full text): {prisma_record.records_excluded_full_text}
  Exclusion reasons:
"""
    for reason, count in prisma_record.exclusion_reasons.items():
        summary += f"    - {reason}: {count}\n"
    
    summary += f"""
INCLUDED:
- Studies included: {prisma_record.studies_included}
- Search date: {prisma_record.search_date}
"""
    
    return summary
