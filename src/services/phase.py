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
    elif days_since < 14:
        traditional_phase = TraditionalPhaseType.FOLLICULAR
        duration = 9
    elif days_since < 17:
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
            "dietary_style": "Ketobiótico",
            "fasting_protocol": "13 a 72 horas según tolerancia (16:8, 24h, OMAD)",
            "food_recommendations": [
                "Grasas saludables: aguacate, aceite de oliva, aceite de coco, ghee",
                "Proteínas limpias: pescado, huevo, tofu, pollo orgánico",
                "Crucíferas: brócoli, coles de Bruselas, col rizada, kale",
                "Prebióticos: ajo, cebolla, puerro, raíz de diente de león",
                "Semillas: linaza, chía, calabaza, girasol, ajonjolí",
                "Probióticos naturales: kimchi, chucrut, yogur, kéfir",
                "Estrógeno-builders: espinaca, germinados, arándanos, fresas"
            ],
            "activity_recommendations": [
                "Ejercicio de baja intensidad",
                "Yoga suave",
                "Caminatas",
                "Descanso según necesidad",
                "Meditación y prácticas de relajación"
            ]
        },
        FunctionalPhaseType.MANIFESTATION: {
            "dietary_style": "Transición entre ketobiótico y hormone feasting",
            "fasting_protocol": "No más de 15 horas, evitar ayunos largos",
            "food_recommendations": [
                "Vegetales de raíz: remolacha, zanahoria, nabo, hinojo",
                "Frutas frescas: toronja, bayas, piña, mango, papaya",
                "Crucíferas: coliflor, kale, brócoli",
                "Alimentos desintoxicantes: pepinillos fermentados, limón",
                "Polifenoles: aceitunas, cebolla morada, chocolate amargo",
                "Apoyo intestinal: alimentos fermentados, fibra prebiótica",
                "Semillas y nueces suaves: almendras, anacardos, nueces"
            ],
            "activity_recommendations": [
                "Ejercicio de intensidad moderada a alta",
                "Actividades sociales",
                "Proyectos creativos",
                "Toma de decisiones importantes",
                "Networking y comunicación"
            ]
        },
        FunctionalPhaseType.NURTURE: {
            "dietary_style": "Hormone Feasting extendido",
            "fasting_protocol": "Evitar el ayuno, comidas frecuentes y cálidas",
            "food_recommendations": [
                "Tubérculos: camote, yuca, papa roja, calabaza butternut",
                "Carbohidratos complejos: avena, arroz integral, quinoa",
                "Magnesio y B6: plátano, semillas de girasol, chocolate",
                "Frutas reconfortantes: dátiles, higos, manzana cocida",
                "Tés calmantes: manzanilla, jengibre, hinojo",
                "Proteínas suaves: caldo de pollo, pavo, sopas"
            ],
            "activity_recommendations": [
                "Ejercicio suave y restaurativo",
                "Actividades relajantes",
                "Autocuidado y descanso",
                "Prácticas de relajación",
                "Tiempo en la naturaleza"
            ],
            "supplement_recommendations": [
                "Magnesio",
                "Vitamina B6",
                "Omega-3",
                "Probióticos"
            ]
        }
    }
    
    return {
        "traditional_symptoms": traditional_symptoms[traditional_phase],
        **functional_details[functional_phase]
    }

def map_to_functional_phase(phase: TraditionalPhaseType, cycle_day: int) -> FunctionalPhaseType:
    """Map traditional phase to functional phase based on Dr. Mindy Pelz's approach."""
    if phase in [TraditionalPhaseType.MENSTRUATION, TraditionalPhaseType.FOLLICULAR] and cycle_day <= 10:
        return FunctionalPhaseType.POWER
    elif phase == TraditionalPhaseType.OVULATION or (cycle_day >= 11 and cycle_day <= 15):
        return FunctionalPhaseType.MANIFESTATION
    elif cycle_day >= 16:
        # Early luteal is also Power phase
        return FunctionalPhaseType.POWER if cycle_day <= 19 else FunctionalPhaseType.NURTURE
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
            category="nutricion",
            priority=5,
            description=f"Estilo alimenticio: {phase_details['dietary_style']}"
        ),
        RecommendationType(
            category="nutricion",
            priority=4,
            description=f"Protocolo de ayuno: {phase_details['fasting_protocol']}"
        )
    ])
    
    # Food recommendations
    for food_rec in phase_details['food_recommendations']:
        recommendations.append(
            RecommendationType(
                category="nutricion",
                priority=4,
                description=food_rec
            )
        )
    
    # Activity recommendations
    for activity_rec in phase_details['activity_recommendations']:
        recommendations.append(
            RecommendationType(
                category="actividad",
                priority=3,
                description=activity_rec
            )
        )
    
    # Supplement recommendations if available
    if phase_details.get('supplement_recommendations'):
        for supp_rec in phase_details['supplement_recommendations']:
            recommendations.append(
                RecommendationType(
                    category="suplementos",
                    priority=3,
                    description=f"Considerar suplementación con {supp_rec}"
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
        "🌙 Reporte de Fase",
        f"Fase Tradicional: {phase.traditional_phase.value.title()}",
        f"Fase Funcional: {phase.functional_phase.value.title()}",
        f"Duración: {phase.duration} días ({phase.start_date} a {phase.end_date})",
        "",
        "🩺 Síntomas Comunes:",
        *[f"• {symptom}" for symptom in phase.typical_symptoms],
        "",
        "🍽️ Estilo Alimenticio:",
        f"• {phase.dietary_style}",
        "",
        "⏱️ Protocolo de Ayuno:",
        f"• {phase.fasting_protocol}",
        "",
        "🥗 Alimentos Recomendados:",
        *[f"• {food}" for food in phase.food_recommendations],
        "",
        "💪 Actividades Recomendadas:",
        *[f"• {activity}" for activity in phase.activity_recommendations],
    ]
    
    if phase.supplement_recommendations:
        report.extend([
            "",
            "💊 Suplementos a Considerar:",
            *[f"• {supplement}" for supplement in phase.supplement_recommendations]
        ])
    
    if events:
        recent_events = [e for e in events if e.notes and e.date >= phase.start_date]
        if recent_events:
            report.extend([
                "",
                "📝 Notas Recientes:",
                *[f"• {event.date}: {event.notes}" for event in recent_events]
            ])
    
    return "\n".join(report)
