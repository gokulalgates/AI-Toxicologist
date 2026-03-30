"""
Prediction Calibration Module
Calibrates prediction probabilities for better reliability
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from collections import defaultdict


class CalibrationModel:
    """Simple calibration model using isotonic regression approximation"""
    
    def __init__(self):
        self.calibration_map = {}  # Maps raw confidence to calibrated confidence
        self.is_fitted = False
    
    def fit(
        self,
        predictions: List[Dict],
        ground_truth: Optional[List[Dict]] = None
    ) -> None:
        """
        Fit calibration model
        
        Args:
            predictions: List of prediction dicts with confidence scores
            ground_truth: Optional ground truth labels (if available)
        """
        if ground_truth is None:
            # Use self-consistency as proxy for ground truth
            # Higher consistency = more likely to be correct
            self._fit_from_consistency(predictions)
        else:
            self._fit_from_ground_truth(predictions, ground_truth)
        
        self.is_fitted = True
    
    def _fit_from_consistency(
        self,
        predictions: List[Dict]
    ) -> None:
        """Fit calibration using self-consistency as proxy"""
        # Group predictions by confidence level
        confidence_bins = defaultdict(list)
        
        for pred in predictions:
            confidence = pred.get("confidence_score", 0.5)
            bin_idx = int(confidence * 10) / 10.0  # Bin to 0.1 precision
            confidence_bins[bin_idx].append(pred)
        
        # Estimate calibrated confidence
        # Higher consistency = higher calibrated confidence
        for bin_conf, preds in confidence_bins.items():
            if not preds:
                continue
            
            # Average consistency across predictions in this bin
            consistencies = [p.get("confidence_score", 0.5) for p in preds]
            avg_consistency = np.mean(consistencies)
            
            # Calibrate: if consistency is high, trust it more
            # Simple linear mapping (can be improved with isotonic regression)
            calibrated = min(avg_consistency * 1.1, 1.0)  # Slight boost
            self.calibration_map[bin_conf] = calibrated
    
    def _fit_from_ground_truth(
        self,
        predictions: List[Dict],
        ground_truth: List[Dict]
    ) -> None:
        """Fit calibration using ground truth labels"""
        # Group by confidence bins
        confidence_bins = defaultdict(lambda: {"correct": 0, "total": 0})
        
        for pred, truth in zip(predictions, ground_truth):
            confidence = pred.get("confidence_score", 0.5)
            bin_idx = int(confidence * 10) / 10.0
            
            # Check if prediction matches truth (simplified)
            is_correct = self._check_correctness(pred, truth)
            
            confidence_bins[bin_idx]["total"] += 1
            if is_correct:
                confidence_bins[bin_idx]["correct"] += 1
        
        # Calibrate: actual accuracy in each bin
        for bin_conf, stats in confidence_bins.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else bin_conf
            self.calibration_map[bin_conf] = accuracy
    
    def _check_correctness(
        self,
        prediction: Dict,
        ground_truth: Dict
    ) -> bool:
        """Check if prediction matches ground truth (simplified)"""
        # Compare KC statuses
        for i in range(1, 13):
            kc_num = f"kc{i}"
            status_key = f"{kc_num}_status"
            pred_status = prediction.get(status_key, "NOT_MENTIONED")
            truth_status = ground_truth.get(status_key, "NOT_MENTIONED")
            
            if pred_status != truth_status:
                return False
        
        return True
    
    def calibrate(self, confidence: float) -> float:
        """
        Calibrate a confidence score
        
        Args:
            confidence: Raw confidence score (0.0 to 1.0)
        
        Returns:
            Calibrated confidence score
        """
        if not self.is_fitted:
            return confidence  # Return as-is if not fitted
        
        # Find nearest bin
        bin_idx = int(confidence * 10) / 10.0
        
        if bin_idx in self.calibration_map:
            return self.calibration_map[bin_idx]
        
        # Interpolate between bins
        lower_bin = max([b for b in self.calibration_map.keys() if b <= bin_idx], default=0.0)
        upper_bin = min([b for b in self.calibration_map.keys() if b >= bin_idx], default=1.0)
        
        if lower_bin == upper_bin:
            return self.calibration_map.get(lower_bin, confidence)
        
        # Linear interpolation
        lower_conf = self.calibration_map.get(lower_bin, lower_bin)
        upper_conf = self.calibration_map.get(upper_bin, upper_bin)
        
        if upper_bin == lower_bin:
            return lower_conf
        
        weight = (bin_idx - lower_bin) / (upper_bin - lower_bin)
        calibrated = lower_conf + weight * (upper_conf - lower_conf)
        
        return min(max(calibrated, 0.0), 1.0)


def calibrate_predictions(
    predictions: List[Dict],
    calibration_model: Optional[CalibrationModel] = None
) -> List[Dict]:
    """
    Calibrate predictions using calibration model
    
    Args:
        predictions: List of prediction dicts with confidence scores
        calibration_model: Optional pre-fitted calibration model
    
    Returns:
        List of predictions with calibrated confidence scores
    """
    if calibration_model is None:
        # Create and fit model from predictions
        calibration_model = CalibrationModel()
        calibration_model.fit(predictions)
    
    calibrated_predictions = []
    
    for pred in predictions:
        calibrated_pred = pred.copy()
        
        # Calibrate overall confidence
        raw_confidence = pred.get("confidence_score", 0.5)
        calibrated_confidence = calibration_model.calibrate(raw_confidence)
        calibrated_pred["confidence_score"] = calibrated_confidence
        calibrated_pred["raw_confidence_score"] = raw_confidence
        
        # Calibrate per-KC confidence
        for i in range(1, 13):
            kc = f"KC{i}"
            kc_conf_key = f"{kc}_confidence"
            if kc_conf_key in pred:
                raw_kc_conf = pred[kc_conf_key]
                calibrated_kc_conf = calibration_model.calibrate(raw_kc_conf)
                calibrated_pred[kc_conf_key] = calibrated_kc_conf
                calibrated_pred[f"{kc}_raw_confidence"] = raw_kc_conf
        
        calibrated_predictions.append(calibrated_pred)
    
    return calibrated_predictions


# Global calibration model
_global_calibration_model: Optional[CalibrationModel] = None


def get_calibration_model() -> CalibrationModel:
    """Get global calibration model"""
    global _global_calibration_model
    if _global_calibration_model is None:
        _global_calibration_model = CalibrationModel()
    return _global_calibration_model
