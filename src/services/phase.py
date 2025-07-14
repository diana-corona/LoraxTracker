"""
Service module for handling menstrual cycle phases and transitions.
"""
from typing import List, Optional
from datetime import date, timedelta

from src.models.phase import Phase, TraditionalPhaseType, FunctionalPhaseType
from src.models.event import CycleEvent
from src.models.recommendation import Recommendation, RecommendationType

def get_current_phase(events: List[CycleEvent], target_date: Optional[date] = None) -> Phase:
    """
    Get the current phase based on historical events.
    
    Args:
        events: List of cycle events
        target_date: Optional specific date to analyze
        
    Returns:
        Current Phase object with both traditional and functional phase information
    """
    if not target_date:
        target_date = date.today()

    # Get most recent menstruation event
    menstruation_events = sorted(
        [e for e in events if e.state == TraditionalPhaseType.MENSTRUATION.value],
        key=lambda x: x.date,
        reverse=True
    )
    
    if not menstruation_events:
        raise ValueError("No menstruation events found")
    
    last_menstruation = menstruation_events[0]
    days_since = (target_date - last_menstruation.date).days
    
    # Determine traditional phase
    if days_since < 5:
        traditional_phase = TraditionalPhaseType.MENSTRUATION
        duration = 5
    elif days_since < 12:
        traditional_phase = TraditionalPhaseType.FOLLICULAR
        duration = 7
    elif days_since < 15:
        traditional_phase = TraditionalPhaseType.OVULATION
        duration = 3
    else:
        traditional_phase = TraditionalPhaseType.LUTEAL
        duration = 11
    
    # Map to functional phase
    functional_phase = map_to_functional_phase(traditional_phase, days_since + 1)
    
    # Get phase details
    phase_details = get_phase_details(traditional_phase, days_since + 1)
    
    start_date = target_date - timedelta(days=days_since % duration)
    end_date = start_date + timedelta(days=duration)
    
    return Phase(
        traditional_phase=traditional_phase,
        functional_phase=functional_phase,
        start_date=start_date,
        end_date=end_date,
        duration=duration,
        typical_symptoms=phase_details["traditional_symptoms"],
        dietary_style=phase_details["dietary_style"],
        fasting_protocol=phase_details["fasting_protocol"],
        food_recommendations=phase_details["food_recommendations"],
        activity_recommendations=phase_details["activity_recommendations"],
        supplement_recommendations=phase_details.get("supplement_recommendations"),
        user_notes=None
    )

def predict_next_phase(current_phase: Phase) -> Phase:
    """
    Predict the next phase based on the current phase.
    
    Args:
        current_phase: Current Phase object
        
    Returns:
        Predicted next Phase object
    """
    traditional_sequence = {
        TraditionalPhaseType.MENSTRUATION: TraditionalPhaseType.FOLLICULAR,
        TraditionalPhaseType.FOLLICULAR: TraditionalPhaseType.OVULATION,
        TraditionalPhaseType.OVULATION: TraditionalPhaseType.LUTEAL,
        TraditionalPhaseType.LUTEAL: TraditionalPhaseType.MENSTRUATION
    }
    
    next_traditional_phase = traditional_sequence[current_phase.traditional_phase]
    next_start_date = current_phase.end_date + timedelta(days=1)
    
    # Calculate cycle day for next phase
    if next_traditional_phase == TraditionalPhaseType.MENSTRUATION:
        cycle_day = 1
    elif next_traditional_phase == TraditionalPhaseType.FOLLICULAR:
        cycle_day = 6  # Day after menstruation
    elif next_traditional_phase == TraditionalPhaseType.OVULATION:
        cycle_day = 15  # Approximate ovulation
    else:  # LUTEAL
        cycle_day = 18  # Start of luteal phase
    
    # Get phase details for the next phase
    phase_details = get_phase_details(next_traditional_phase, cycle_day)
    
    # Map to functional phase
    next_functional_phase = map_to_functional_phase(next_traditional_phase, cycle_day)
    
    # Set duration based on traditional phase
    durations = {
        TraditionalPhaseType.MENSTRUATION: 5,
        TraditionalPhaseType.FOLLICULAR: 9,
        TraditionalPhaseType.OVULATION: 3,
        TraditionalPhaseType.LUTEAL: 11
    }
    
    duration = durations[next_traditional_phase]
    next_end_date = next_start_date + timedelta(days=duration - 1)
    
    return Phase(
        traditional_phase=next_traditional_phase,
        functional_phase=next_functional_phase,
        start_date=next_start_date,
        end_date=next_end_date,
        duration=duration,
        typical_symptoms=phase_details["traditional_symptoms"],
        dietary_style=phase_details["dietary_style"],
        fasting_protocol=phase_details["fasting_protocol"],
        food_recommendations=phase_details["food_recommendations"],
        activity_recommendations=phase_details["activity_recommendations"],
        supplement_recommendations=phase_details.get("supplement_recommendations"),
        user_notes=None
    )

def get_phase_details(traditional_phase: TraditionalPhaseType, cycle_day: int) -> dict:
    """
    Get detailed phase information including symptoms and recommendations.
    
    Args:
        traditional_phase: Traditional menstrual phase type
        cycle_day: Day in the cycle (1-based)
        
    Returns:
        Dictionary with phase details
    """
    # Map traditional phase and cycle day to functional phase
    functional_phase = map_to_functional_phase(traditional_phase, cycle_day)
    
    # Base symptoms by traditional phase
    traditional_symptoms = {
        TraditionalPhaseType.MENSTRUATION: [
            "Cramping and uterine contractions",
            "Lower back and abdominal pain",
            "Fatigue and low energy",
            "Headaches or migraines",
            "Changes in appetite",
            "Mood fluctuations"
        ],
        TraditionalPhaseType.FOLLICULAR: [
            "Increased energy levels",
            "Enhanced mood and optimism",
            "Better cognitive function",
            "Increased creativity",
            "Higher motivation",
            "Decreased PMS symptoms"
        ],
        TraditionalPhaseType.OVULATION: [
            "Mild pelvic pain or cramping",
            "Changes in cervical mucus",
            "Increased sex drive",
            "Breast tenderness",
            "Heightened energy levels",
            "Improved mood and confidence"
        ],
        TraditionalPhaseType.LUTEAL: [
            "Premenstrual symptoms (PMS)",
            "Mood changes and irritability",
            "Breast tenderness and swelling",
            "Fatigue and decreased energy",
            "Food cravings",
            "Bloating and water retention"
        ]
    }
    
    # Functional phase details based on Dr. Mindy Pelz's recommendations
    functional_details = {
        FunctionalPhaseType.POWER: {
            "dietary_style": "Ketobiotic",
            "fasting_protocol": "13 to 72 hours as tolerated (16:8, 24h, OMAD)",
            "food_recommendations": [
                "Healthy fats: avocado, olive oil, coconut oil, ghee",
                "Clean proteins: fish, eggs, tofu, organic chicken",
                "Cruciferous vegetables: broccoli, Brussels sprouts, kale",
                "Prebiotics: garlic, onion, leek, dandelion root",
                "Seeds: flax, chia, pumpkin, sunflower, sesame",
                "Natural probiotics: kimchi, sauerkraut, yogurt, kefir",
                "Estrogen builders: spinach, sprouts, blueberries, strawberries"
            ],
            "activity_recommendations": [
                "Low intensity exercise",
                "Gentle yoga",
                "Walking",
                "Rest as needed",
                "Meditation and relaxation practices"
            ]
        },
        FunctionalPhaseType.MANIFESTATION: {
            "dietary_style": "Transition from ketobiotic to hormone feasting",
            "fasting_protocol": "No more than 15 hours, avoid extended fasts",
            "food_recommendations": [
                "Root vegetables: beets, carrots, turnips, fennel",
                "Fresh fruits: grapefruit, berries, pineapple, mango, papaya",
                "Cruciferous vegetables: cauliflower, kale, broccoli",
                "Detox foods: fermented pickles, lemon, parsley",
                "Polyphenols: olives, red onion, dark chocolate",
                "Gut support: fermented foods, prebiotic fiber",
                "Soft nuts and seeds: almonds, cashews, Brazil nuts"
            ],
            "activity_recommendations": [
                "Moderate to high intensity exercise",
                "Social activities",
                "Creative projects",
                "Important decision making",
                "Networking and communication"
            ]
        },
        FunctionalPhaseType.NURTURE: {
            "dietary_style": "Extended hormone feasting",
            "fasting_protocol": "Avoid fasting, frequent warm meals with complex carbs",
            "food_recommendations": [
                "Root vegetables: sweet potato, yuca, red potato, butternut squash",
                "Complex carbs: oats, brown rice, quinoa",
                "Magnesium & B6: banana, sunflower seeds, dark chocolate",
                "Comfort fruits: dates, figs, cooked apple",
                "Calming teas: chamomile, ginger root, fennel",
                "Gentle proteins: chicken broth, turkey, soups"
            ],
            "activity_recommendations": [
                "Gentle restorative exercise",
                "Relaxing activities",
                "Self-care and rest",
                "Relaxation practices",
                "Time in nature"
            ],
            "supplement_recommendations": [
                "Magnesium",
                "Vitamin B6",
                "Omega-3",
                "Probiotics"
            ]
        }
    }
    
    return {
        "traditional_symptoms": traditional_symptoms[traditional_phase],
        **functional_details[functional_phase]
    }

def map_to_functional_phase(phase: TraditionalPhaseType, cycle_day: int) -> FunctionalPhaseType:
    """Map traditional phase to functional phase based on Dr. Mindy Pelz's approach."""
    if cycle_day <= 10:
        return FunctionalPhaseType.POWER
    elif cycle_day >= 11 and cycle_day <= 15:
        return FunctionalPhaseType.MANIFESTATION
    elif cycle_day >= 16 and cycle_day <= 19:
        return FunctionalPhaseType.POWER
    else:
        return FunctionalPhaseType.NURTURE

def get_phase_specific_recommendations(
    traditional_phase: TraditionalPhaseType,
    functional_phase: FunctionalPhaseType,
    cycle_day: int
) -> List[RecommendationType]:
    """
    Get detailed recommendations based on both traditional and functional phases.
    
    Args:
        traditional_phase: Traditional menstrual phase type
        functional_phase: Functional phase type (Power/Manifestation/Nurture)
        cycle_day: Day in the cycle (1-based)
        
    Returns:
        List of RecommendationType objects
    """
    phase_details = get_phase_details(traditional_phase, cycle_day)
    recommendations = []
    
    # Dietary recommendations
    recommendations.extend([
        RecommendationType(
            category="nutrition",
            priority=5,
            description=f"Dietary style: {phase_details['dietary_style']}"
        ),
        RecommendationType(
            category="nutrition",
            priority=4,
            description=f"Fasting protocol: {phase_details['fasting_protocol']}"
        )
    ])
    
    # Food recommendations
    for food_rec in phase_details['food_recommendations']:
        recommendations.append(
            RecommendationType(
                category="nutrition",
                priority=4,
                description=food_rec
            )
        )
    
    # Activity recommendations
    for activity_rec in phase_details['activity_recommendations']:
        recommendations.append(
            RecommendationType(
                category="activity",
                priority=3,
                description=activity_rec
            )
        )
    
    # Supplement recommendations if available
    if phase_details.get('supplement_recommendations'):
        for supp_rec in phase_details['supplement_recommendations']:
            recommendations.append(
                RecommendationType(
                    category="supplements",
                    priority=3,
                    description=f"Consider supplementing with {supp_rec}"
                )
            )
    
    return recommendations

def generate_phase_report(phase: Phase, events: List[CycleEvent]) -> str:
    """
    Generate a detailed report for the current phase.
    
    Args:
        phase: Current Phase object
        events: List of relevant cycle events
        
    Returns:
        Formatted report string
    """
    report = [
        "🌙 Phase Report",
        f"Traditional Phase: {phase.traditional_phase.value.title()}",
        f"Functional Phase: {phase.functional_phase.value.title()}",
        f"Duration: {phase.duration} days ({phase.start_date} to {phase.end_date})",
        "",
        "🩺 Common Symptoms:",
        *[f"• {symptom}" for symptom in phase.typical_symptoms],
        "",
        "🍽️ Dietary Style:",
        f"• {phase.dietary_style}",
        "",
        "⏱️ Fasting Protocol:",
        f"• {phase.fasting_protocol}",
        "",
        "🥗 Recommended Foods:",
        *[f"• {food}" for food in phase.food_recommendations],
        "",
        "💪 Recommended Activities:",
        *[f"• {activity}" for activity in phase.activity_recommendations],
    ]
    
    if phase.supplement_recommendations:
        report.extend([
            "",
            "💊 Supplements to Consider:",
            *[f"• {supplement}" for supplement in phase.supplement_recommendations]
        ])
    
    if events:
        recent_events = [e for e in events if e.notes and e.date >= phase.start_date]
        if recent_events:
            report.extend([
                "",
                "📝 Recent Notes:",
                *[f"• {event.date}: {event.notes}" for event in recent_events]
            ])
    
    return "\n".join(report)
