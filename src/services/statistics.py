"""
Statistics calculation service for cycle tracking data.
"""
from typing import Dict, List
from statistics import mean
from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType

def calculate_phase_statistics(events: List[CycleEvent]) -> Dict:
    """
    Calculate statistics for each phase.
    
    Args:
        events: List of cycle events to analyze
        
    Returns:
        Dictionary containing statistics for each phase
    """
    phase_data = {phase.value: {"durations": [], "pain_levels": [], "energy_levels": []} 
                 for phase in TraditionalPhaseType}
    
    for event in events:
        phase = event.state
        phase_data[phase]["durations"].append(1)  # Each event represents one day
        if event.pain_level is not None:
            phase_data[phase]["pain_levels"].append(event.pain_level)
        if event.energy_level is not None:
            phase_data[phase]["energy_levels"].append(event.energy_level)
    
    statistics = {}
    for phase, data in phase_data.items():
        statistics[phase] = {
            "average_duration": mean(data["durations"]) if data["durations"] else 0,
            "occurrence_count": len(data["durations"]),
            "average_pain_level": mean(data["pain_levels"]) if data["pain_levels"] else None,
            "average_energy_level": mean(data["energy_levels"]) if data["energy_levels"] else None
        }
    
    return statistics

def calculate_cycle_statistics(events: List[CycleEvent]) -> Dict:
    """
    Calculate overall cycle statistics.
    
    Args:
        events: List of cycle events to analyze
        
    Returns:
        Dictionary containing cycle statistics
    """
    if not events:
        return {
            "average_cycle_length": 0,
            "min_cycle_length": 0,
            "max_cycle_length": 0,
            "total_cycles": 0
        }
    
    # Sort events by date
    sorted_events = sorted(events, key=lambda x: x.date)
    
    # Find cycle lengths by looking for menstruation phases
    cycle_lengths = []
    last_menstruation = None
    
    for event in sorted_events:
        if event.state == TraditionalPhaseType.MENSTRUATION.value:
            if last_menstruation:
                cycle_length = (event.date - last_menstruation).days
                if 15 <= cycle_length <= 45:  # Filter out unlikely cycle lengths
                    cycle_lengths.append(cycle_length)
            last_menstruation = event.date
    
    if not cycle_lengths:
        return {
            "average_cycle_length": 0,
            "min_cycle_length": 0,
            "max_cycle_length": 0,
            "total_cycles": 0
        }
    
    return {
        "average_cycle_length": mean(cycle_lengths),
        "min_cycle_length": min(cycle_lengths),
        "max_cycle_length": max(cycle_lengths),
        "total_cycles": len(cycle_lengths)
    }
