"""
Service module for generating and managing personalized recommendations.
"""
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta

from src.models.phase import Phase, TraditionalPhaseType, FunctionalPhaseType
from src.models.event import CycleEvent
from src.models.recommendation import Recommendation, RecommendationType
from src.services.phase import get_phase_specific_recommendations

class RecommendationEngine:
    """Engine for generating personalized recommendations based on user data."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._recommendation_cache: Dict[str, List[RecommendationType]] = {}
    
    def generate_recommendations(
        self,
        current_phase: Phase,
        historical_events: List[CycleEvent]
    ) -> Recommendation:
        """
        Generate personalized recommendations based on phase and historical data.
        
        Args:
            current_phase: Current cycle phase
            historical_events: List of past cycle events
            
        Returns:
            Recommendation object with personalized suggestions
        """
        # Calculate current cycle day
        menstruation_events = sorted(
            [e for e in historical_events if e.state == "menstruation"],
            key=lambda x: x.date,
            reverse=True
        )
        
        if menstruation_events:
            cycle_day = (date.today() - menstruation_events[0].date).days + 1
        else:
            cycle_day = 1
        
        # Get base recommendations
        base_recommendations = get_phase_specific_recommendations(
            current_phase.traditional_phase,
            current_phase.functional_phase,
            cycle_day
        )
        
        # Personalize recommendations
        personalized_recommendations = self._personalize_recommendations(
            base_recommendations,
            historical_events,
            current_phase.functional_phase
        )
        
        return Recommendation(
            user_id=self.user_id,
            phase_type=current_phase.traditional_phase.value,
            date=date.today(),
            recommendations=personalized_recommendations,
            is_implemented=False
        )
    
    def _personalize_recommendations(
        self,
        base_recommendations: List[RecommendationType],
        historical_events: List[CycleEvent],
        functional_phase: FunctionalPhaseType
    ) -> List[RecommendationType]:
        """
        Adjust recommendations based on user's historical data and functional phase.
        
        Args:
            base_recommendations: List of base recommendations for the phase
            historical_events: List of past cycle events
            functional_phase: Current functional phase type
            
        Returns:
            Adjusted list of recommendations
        """
        # Filter recent events (last 3 cycles)
        recent_events = sorted(
            historical_events,
            key=lambda x: x.date,
            reverse=True
        )[:90]  # Approximately 3 cycles
        
        # Analyze pain and energy patterns
        avg_pain, avg_energy = self._analyze_patterns(recent_events)
        
        personalized = []
        for rec in base_recommendations:
            # Adjust priority based on historical data and functional phase
            adjusted_priority = self._adjust_priority(
                rec,
                avg_pain,
                avg_energy,
                functional_phase
            )
            
            # Create new recommendation with adjusted priority
            personalized.append(
                RecommendationType(
                    category=rec.category,
                    priority=adjusted_priority,
                    description=rec.description
                )
            )
        
        # Add phase-specific additional recommendations
        additional_recs = self._get_additional_recommendations(
            avg_pain,
            avg_energy,
            functional_phase
        )
        personalized.extend(additional_recs)
        
        return sorted(personalized, key=lambda x: x.priority, reverse=True)
    
    def _analyze_patterns(
        self,
        events: List[CycleEvent]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Analyze pain and energy patterns from events."""
        pain_levels = [e.pain_level for e in events if e.pain_level is not None]
        energy_levels = [e.energy_level for e in events if e.energy_level is not None]
        
        avg_pain = sum(pain_levels) / len(pain_levels) if pain_levels else None
        avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else None
        
        return avg_pain, avg_energy
    
    def _adjust_priority(
        self,
        recommendation: RecommendationType,
        avg_pain: Optional[float],
        avg_energy: Optional[float],
        functional_phase: FunctionalPhaseType
    ) -> int:
        """Adjust recommendation priority based on patterns and phase."""
        priority = recommendation.priority
        
        # Base adjustments for pain/energy
        if recommendation.category == "exercise":
            if avg_pain and avg_pain > 3:
                priority = max(1, priority - 1)
            if avg_energy and avg_energy < 3:
                priority = max(1, priority - 1)
        
        if recommendation.category == "rest":
            if avg_pain and avg_pain > 3:
                priority = min(5, priority + 1)
            if avg_energy and avg_energy < 3:
                priority = min(5, priority + 1)
        
        # Phase-specific adjustments
        if functional_phase == FunctionalPhaseType.POWER:
            if recommendation.category == "nutrition":
                priority = min(5, priority + 1)  # Higher priority for nutrition during Power phase
            if "fasting" in recommendation.description.lower():
                priority = min(5, priority + 1)  # Higher priority for fasting recommendations
                
        elif functional_phase == FunctionalPhaseType.MANIFESTATION:
            if recommendation.category == "activity":
                priority = min(5, priority + 1)  # Higher priority for activities
                
        elif functional_phase == FunctionalPhaseType.NURTURE:
            if recommendation.category == "rest":  # This is already correct, matching for consistent casing
                priority = min(5, priority + 1)  # Higher priority for rest
            if "fasting" in recommendation.description.lower():
                priority = max(1, priority - 2)  # Lower priority for fasting
        
        return priority
    
    def _get_additional_recommendations(
        self,
        avg_pain: Optional[float],
        avg_energy: Optional[float],
        functional_phase: FunctionalPhaseType
    ) -> List[RecommendationType]:
        """Get additional phase-specific recommendations."""
        additional = []
        
        # Pain/Energy based recommendations
        if avg_pain and avg_pain > 3:
            additional.append(
                RecommendationType(
                    category="rest",
                    priority=5,
                    description="Consider pain management techniques and additional rest"
                )
            )
        
        if avg_energy and avg_energy < 3:
            additional.append(
                RecommendationType(
                    category="nutrition",
                    priority=4,
                    description="Focus on energy-rich foods and supplements"
                )
            )
        
        # Phase-specific recommendations
        if functional_phase == FunctionalPhaseType.POWER:
            if avg_energy and avg_energy > 3:
                additional.append(
                    RecommendationType(
                        category="nutrition",
                        priority=4,
                        description="Take advantage of high energy levels for fasting"
                    )
                )
                
        elif functional_phase == FunctionalPhaseType.NURTURE:
            additional.append(
                RecommendationType(
                    category="emotional",
                    priority=4,
                    description="Practice self-care and emotional connection techniques"
                )
            )
        
        return additional
    
    def update_recommendation_feedback(
        self,
        recommendation: Recommendation,
        effectiveness: int,
        feedback: Optional[str] = None
    ) -> Recommendation:
        """
        Update recommendation with user feedback.
        
        Args:
            recommendation: Original recommendation
            effectiveness: Rating from 1-5
            feedback: Optional feedback text
            
        Returns:
            Updated recommendation with feedback
        """
        return Recommendation(
            **{
                **recommendation.model_dump(),
                "effectiveness_rating": effectiveness,
                "user_feedback": feedback
            }
        )
