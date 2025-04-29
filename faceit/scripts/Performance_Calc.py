import numpy as np
import logging

# Set up logging
logger = logging.getLogger(__name__)

class PerformanceCalculator:
    """Class for calculating player performance metrics"""
    
    # Default baseline values that represent average performance
    DEFAULT_KD = 1.0
    DEFAULT_KR = 0.72
    BASELINE_SCORE = 5.0  # Middle point on a 1-10 scale
    
    @staticmethod
    def calculate(kd, kr, discrep):
        """Calculate a performance score based on deviation from baseline KD, KR, and ELO discrepancy"""
        logger.debug(f"Calculating performance with KD: {kd}, KR: {kr}, Discrep: {discrep}")
        
        # Calculate deviations from baseline values
        kd_deviation = kd - PerformanceCalculator.DEFAULT_KD  # How much better/worse than default KD
        kr_deviation = kr - PerformanceCalculator.DEFAULT_KR  # How much better/worse than default KR
        
        # Apply a dynamic weighting to ELO discrepancy based on its absolute value
        # For large discrepancies (both positive and negative), reduce the impact
        abs_discrep = abs(discrep)
        
        # The larger the discrepancy, the less it should impact the score
        if abs_discrep > 500:
            discrep_weight = 0.2  # Very small weight for large discrepancies
        elif abs_discrep > 300:
            discrep_weight = 0.5  # Small weight for medium discrepancies
        else:
            discrep_weight = 0.8  # Higher weight for small discrepancies
        
        # Apply a softer sigmoid function to normalize the elo discrepancy
        # Scale to a smaller range (-0.6 to +0.6)
        discrep_factor = 1.2 / (1 + np.exp(-discrep / 1500)) - 0.6
        
        # Apply the dynamic weight to the discrepancy factor
        adjusted_discrep = discrep_factor * discrep_weight
        
        # Calculate performance adjustment from baseline
        # Higher weights for KD and KR deviations to make them more impactful
        kd_component = kd_deviation * 2.5  # Increased weight for KD deviation
        kr_component = kr_deviation * 4.0  # Increased weight for KR deviation
        discrep_component = adjusted_discrep * 0.5
        
        performance_adjustment = kd_component + kr_component + discrep_component
        
        # Apply adjustment to baseline score (5.0)
        adjusted_performance = PerformanceCalculator.BASELINE_SCORE + performance_adjustment
        
        # Ensure the value is in the 1-10 range
        performance = min(max(adjusted_performance, 1), 10)
        
        # Enhanced logging for better debugging
        logger.info(f"PERFORMANCE DETAILS - Player with KD: {kd:.2f}, KR: {kr:.2f}")
        logger.info(f"  Default Values: KD: {PerformanceCalculator.DEFAULT_KD}, KR: {PerformanceCalculator.DEFAULT_KR}")
        logger.info(f"  Deviations: KD: {kd_deviation:.2f}, KR: {kr_deviation:.2f}")
        logger.info(f"  ELO Discrepancy: {discrep} (abs: {abs_discrep}, weight: {discrep_weight})")
        logger.info(f"  Components: KD: {kd_component:.2f}, KR: {kr_component:.2f}, Discrep: {discrep_component:.2f}")
        logger.info(f"  Adjustment: {performance_adjustment:.2f}, Baseline: {PerformanceCalculator.BASELINE_SCORE}")
        logger.info(f"  Final Score: {performance:.2f}")
        
        return performance

# For backward compatibility
def Performance(kd, kr, discrep):
    """Legacy function that uses the class method"""
    return PerformanceCalculator.calculate(kd, kr, discrep)