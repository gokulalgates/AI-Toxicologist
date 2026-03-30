"""
Multi-Reviewer System: Multiple LLM models act as independent reviewers
Consolidates results similar to human multi-reviewer systematic reviews
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from collections import Counter, defaultdict
from reliability import cohens_kappa, gwets_ac1
import pandas as pd


def consolidate_kc_analyses(
    all_analyses: List[List[Dict]], 
    models: List[str],
    consensus_method: str = "majority"
) -> Tuple[List[Dict], Dict]:
    """
    Consolidate KC analyses from multiple models (reviewers)
    
    Args:
        all_analyses: List of analysis lists, one per model
                      Each inner list contains dicts with KC statuses
        models: List of model names
        consensus_method: "majority" (voting) or "weighted" (by model quality)
    
    Returns:
        consolidated_analyses: List of consolidated analysis dicts (one per paper)
        agreement_stats: Dictionary with agreement statistics
    """
    if not all_analyses or len(all_analyses) == 0:
        return [], {}
    
    num_papers = len(all_analyses[0])
    num_models = len(all_analyses)
    
    # Verify all models analyzed same number of papers
    for i, analyses in enumerate(all_analyses):
        if len(analyses) != num_papers:
            raise ValueError(f"Model {models[i]} analyzed {len(analyses)} papers, expected {num_papers}")
    
    consolidated_analyses = []
    agreement_stats = {
        "models": models,
        "num_papers": num_papers,
        "kc_agreement": {},  # Per-KC agreement
        "paper_agreement": [],  # Per-paper agreement
        "overall_agreement": {}
    }
    
    # Process each paper
    for paper_idx in range(num_papers):
        paper_analyses = [analyses[paper_idx] for analyses in all_analyses]
        
        # Consolidate KC statuses
        consolidated = {
            "paper_index": paper_idx,
            "pmid": paper_analyses[0].get("pmid", "unknown"),
            "title": paper_analyses[0].get("title", ""),
            "reviewer_analyses": {model: analysis for model, analysis in zip(models, paper_analyses)},
            "consensus": {},
            "agreement_scores": {}
        }
        
        # For each KC, determine consensus
        kc_names = [f"KC{i}" for i in range(1, 13)]
        
        for kc in kc_names:
            status_key = f"{kc.lower()}_status"
            
            # Collect all model ratings for this KC
            ratings = []
            for analysis in paper_analyses:
                status = analysis.get(status_key, "NOT_MENTIONED")
                ratings.append(status)
            
            # Determine consensus
            if consensus_method == "majority":
                # Majority voting
                rating_counts = Counter(ratings)
                most_common = rating_counts.most_common(1)[0]
                consensus_status = most_common[0]
                consensus_count = most_common[1]
                consensus_confidence = consensus_count / num_models
                
            elif consensus_method == "weighted":
                # Weighted voting based on model performance/quality
                # Model weights based on size and capability (calibrated on validation)
                MODEL_WEIGHTS = {
                    "llama3.2": 1.0,      # Best performance (70B)
                    "mixtral": 0.95,     # Excellent (47B)
                    "llama3.1": 0.85,    # Good (8B)
                    "mistral": 0.80,     # Good (7B)
                    "llama3": 0.80,      # Good (8B)
                    "phi3": 0.75,        # Moderate (3.8B)
                    "gemma2": 0.75,      # Moderate
                    "qwen2.5": 0.75,     # Moderate
                }
                
                weighted_votes = defaultdict(float)
                for rating, model in zip(ratings, models):
                    weight = MODEL_WEIGHTS.get(model, 0.5)  # Default weight for unknown models
                    weighted_votes[rating] += weight
                
                # Get rating with highest weighted vote
                consensus_status = max(weighted_votes.items(), key=lambda x: x[1])[0]
                total_weight = sum(weighted_votes.values())
                consensus_confidence = weighted_votes[consensus_status] / total_weight if total_weight > 0 else 0.0
                consensus_count = sum(1 for r in ratings if r == consensus_status)
                
                # Create rating_counts for votes dict (needed for display)
                rating_counts = Counter(ratings)
            else:
                raise ValueError(f"Unknown consensus_method: {consensus_method}")
            
            # Calculate agreement for this KC
            agreement_rate = consensus_count / num_models
            
            consolidated["consensus"][kc] = {
                "status": consensus_status,
                "confidence": consensus_confidence,
                "votes": dict(rating_counts),
                "agreement_rate": agreement_rate
            }
            
            consolidated["consensus"][status_key] = consensus_status
            
            # Track agreement stats per KC
            if kc not in agreement_stats["kc_agreement"]:
                agreement_stats["kc_agreement"][kc] = {
                    "total_ratings": 0,
                    "agreements": 0,
                    "disagreements": 0
                }
            
            agreement_stats["kc_agreement"][kc]["total_ratings"] += num_models
            agreement_stats["kc_agreement"][kc]["agreements"] += consensus_count
            agreement_stats["kc_agreement"][kc]["disagreements"] += (num_models - consensus_count)
        
        # Calculate overall agreement for this paper (across all KCs)
        all_agreement_rates = [v["agreement_rate"] for v in consolidated["consensus"].values() if isinstance(v, dict) and "agreement_rate" in v]
        paper_avg_agreement = np.mean(all_agreement_rates) if all_agreement_rates else 0.0
        
        consolidated["agreement_scores"]["overall"] = paper_avg_agreement
        consolidated["agreement_scores"]["num_kcs_with_consensus"] = sum(1 for v in consolidated["consensus"].values() 
                                                                         if isinstance(v, dict) and v.get("agreement_rate", 0) == 1.0)
        
        agreement_stats["paper_agreement"].append({
            "paper_index": paper_idx,
            "pmid": consolidated["pmid"],
            "avg_agreement": paper_avg_agreement,
            "perfect_consensus_kcs": consolidated["agreement_scores"]["num_kcs_with_consensus"]
        })
        
        consolidated_analyses.append(consolidated)
    
    # Calculate overall agreement statistics
    all_paper_agreements = [p["avg_agreement"] for p in agreement_stats["paper_agreement"]]
    agreement_stats["overall_agreement"] = {
        "mean_agreement": np.mean(all_paper_agreements) if all_paper_agreements else 0.0,
        "std_agreement": np.std(all_paper_agreements) if all_paper_agreements else 0.0,
        "min_agreement": np.min(all_paper_agreements) if all_paper_agreements else 0.0,
        "max_agreement": np.max(all_paper_agreements) if all_paper_agreements else 0.0
    }
    
    # Calculate inter-model agreement (pairwise kappa)
    if num_models >= 2:
        kappa_results = []
        for i in range(num_models):
            for j in range(i + 1, num_models):
                # Extract ratings for all papers and KCs for this pair
                model_i_ratings = []
                model_j_ratings = []
                
                for paper_idx in range(num_papers):
                    analysis_i = all_analyses[i][paper_idx]
                    analysis_j = all_analyses[j][paper_idx]
                    
                    for kc in kc_names:
                        status_key = f"{kc.lower()}_status"
                        model_i_ratings.append(analysis_i.get(status_key, "NOT_MENTIONED"))
                        model_j_ratings.append(analysis_j.get(status_key, "NOT_MENTIONED"))
                
                # Calculate kappa
                kappa_result = cohens_kappa(model_i_ratings, model_j_ratings)
                kappa_results.append({
                    "model_1": models[i],
                    "model_2": models[j],
                    "kappa": kappa_result["kappa"],
                    "interpretation": kappa_result["interpretation"],
                    "observed_agreement": kappa_result["observed_agreement"]
                })
        
        agreement_stats["inter_model_agreement"] = {
            "pairwise_kappa": kappa_results,
            "mean_kappa": np.mean([k["kappa"] for k in kappa_results]) if kappa_results else 0.0
        }
    
    return consolidated_analyses, agreement_stats


def rank_papers_by_consensus(
    consolidated_analyses: List[Dict],
    ranking_method: str = "agreement"
) -> List[Dict]:
    """
    Rank papers by consensus strength and evidence quality
    
    Args:
        consolidated_analyses: List of consolidated analysis dicts
        ranking_method: "agreement" (by agreement rate) or "evidence" (by number of supported KCs)
    
    Returns:
        Ranked list of papers with scores
    """
    ranked_papers = []
    
    for consolidated in consolidated_analyses:
        paper_score = 0.0
        
        if ranking_method == "agreement":
            # Score based on agreement rate
            paper_score = consolidated["agreement_scores"]["overall"]
        
        elif ranking_method == "evidence":
            # Score based on number of supported KCs with high consensus
            supported_count = 0
            for kc in [f"KC{i}" for i in range(1, 13)]:
                kc_data = consolidated["consensus"].get(kc, {})
                if isinstance(kc_data, dict):
                    if kc_data.get("status") == "SUPPORTED" and kc_data.get("confidence", 0) >= 0.67:  # 2/3 consensus
                        supported_count += 1
            paper_score = supported_count
        
        elif ranking_method == "combined":
            # Combined score: agreement * evidence strength
            agreement_score = consolidated["agreement_scores"]["overall"]
            supported_count = 0
            for kc in [f"KC{i}" for i in range(1, 13)]:
                kc_data = consolidated["consensus"].get(kc, {})
                if isinstance(kc_data, dict):
                    if kc_data.get("status") == "SUPPORTED" and kc_data.get("confidence", 0) >= 0.67:
                        supported_count += 1
            evidence_score = supported_count / 12.0  # Normalize to 0-1
            paper_score = (agreement_score * 0.5) + (evidence_score * 0.5)
        
        ranked_papers.append({
            **consolidated,
            "ranking_score": paper_score
        })
    
    # Sort by score (descending)
    ranked_papers.sort(key=lambda x: x["ranking_score"], reverse=True)
    
    # Add rank
    for i, paper in enumerate(ranked_papers):
        paper["rank"] = i + 1
    
    return ranked_papers


def create_consensus_evidence_matrix(
    consolidated_analyses: List[Dict],
    kc_names: List[str]
) -> pd.DataFrame:
    """
    Create evidence matrix from consolidated analyses
    Shows consensus status for each paper-KC combination
    """
    data = []
    
    for consolidated in consolidated_analyses:
        row = {
            "Paper": f"Paper {consolidated['paper_index'] + 1}",
            "PMID": consolidated.get("pmid", "N/A"),
            "Title": consolidated.get("title", "")[:50] + "..." if len(consolidated.get("title", "")) > 50 else consolidated.get("title", ""),
            "Agreement": f"{consolidated['agreement_scores']['overall']:.2%}",
            "Rank": consolidated.get("rank", "N/A")
        }
        
        # Add KC columns with consensus status
        for kc in kc_names:
            kc_data = consolidated["consensus"].get(kc, {})
            if isinstance(kc_data, dict):
                status = kc_data.get("status", "NOT_MENTIONED")
                confidence = kc_data.get("confidence", 0.0)
                
                # Encode: 1=SUPPORTED (high consensus), 0.5=SUPPORTED (low consensus), 0=NOT_MENTIONED, -1=REFUTED
                if status == "SUPPORTED":
                    if confidence >= 0.67:  # 2/3 consensus
                        row[kc] = 1
                    else:
                        row[kc] = 0.5
                elif status == "REFUTED":
                    row[kc] = -1
                else:
                    row[kc] = 0
            else:
                row[kc] = 0
        
        data.append(row)
    
    df = pd.DataFrame(data)
    return df


def create_agreement_heatmap(
    agreement_stats: Dict,
    models: List[str]
) -> Dict:
    """
    Create data for agreement heatmap showing inter-model agreement
    """
    if "inter_model_agreement" not in agreement_stats:
        return {}
    
    pairwise_kappa = agreement_stats["inter_model_agreement"]["pairwise_kappa"]
    
    # Create matrix
    n = len(models)
    agreement_matrix = np.ones((n, n))  # Diagonal is 1.0 (self-agreement)
    
    model_to_idx = {model: i for i, model in enumerate(models)}
    
    for pair in pairwise_kappa:
        idx1 = model_to_idx[pair["model_1"]]
        idx2 = model_to_idx[pair["model_2"]]
        kappa = pair["kappa"]
        agreement_matrix[idx1, idx2] = kappa
        agreement_matrix[idx2, idx1] = kappa  # Symmetric
    
    return {
        "matrix": agreement_matrix.tolist(),
        "models": models,
        "mean_kappa": agreement_stats["inter_model_agreement"]["mean_kappa"]
    }
