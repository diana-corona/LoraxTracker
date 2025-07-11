"""
Service module for generating shopping lists based on predicted phases.
"""
from typing import List, Dict, Set
from datetime import date, timedelta

from src.models.phase import Phase, FunctionalPhaseType
from src.services.phase import get_current_phase, predict_next_phase

class ShoppingListGenerator:
    """Generator for phase-appropriate shopping lists."""
    
    @staticmethod
    def generate_weekly_list(current_phase: Phase) -> Dict[str, List[str]]:
        """
        Generate a categorized shopping list for the upcoming week.
        
        Args:
            current_phase: Current phase to base predictions on
            
        Returns:
            Dictionary of categorized shopping items
        """
        # Get phases for the next week
        phases = [current_phase]
        next_phase = current_phase
        for _ in range(6):  # Look ahead 6 more days
            next_phase = predict_next_phase(next_phase)
            phases.append(next_phase)
        
        # Collect unique ingredients needed for all phases
        ingredients: Dict[str, Set[str]] = {
            "proteinas": set(),
            "vegetales": set(),
            "frutas": set(),
            "grasas": set(),
            "carbohidratos": set(),
            "suplementos": set(),
            "otros": set()
        }
        
        for phase in phases:
            items = ShoppingListGenerator._get_phase_ingredients(phase.functional_phase)
            for category, items_set in items.items():
                ingredients[category].update(items_set)
        
        # Convert sets to sorted lists
        return {
            category: sorted(items)
            for category, items in ingredients.items()
        }
    
    @staticmethod
    def _get_phase_ingredients(phase_type: FunctionalPhaseType) -> Dict[str, Set[str]]:
        """Get recommended ingredients for a specific phase."""
        base_ingredients = {
            "proteinas": set(),
            "vegetales": set(),
            "frutas": set(),
            "grasas": set(),
            "carbohidratos": set(),
            "suplementos": set(),
            "otros": set()
        }
        
        if phase_type == FunctionalPhaseType.POWER:
            base_ingredients.update({
                "grasas": {
                    "aguacate",
                    "aceite de oliva",
                    "aceite de coco",
                    "ghee (mantequilla clarificada)",
                    "nueces variadas"
                },
                "proteinas": {
                    "pescado",
                    "huevos",
                    "tofu",
                    "pollo orgánico"
                },
                "vegetales": {
                    "brócoli",
                    "coles de Bruselas",
                    "col rizada",
                    "kale",
                    "bok choy",
                    "ajo",
                    "cebolla",
                    "puerro",
                    "raíz de diente de león",
                    "alcachofa",
                    "espinaca",
                    "germinados"
                },
                "otros": {
                    "kimchi",
                    "chucrut",
                    "yogur",
                    "kéfir"
                },
                "frutas": {
                    "arándanos",
                    "fresas"
                }
            })
            
        elif phase_type == FunctionalPhaseType.MANIFESTATION:
            base_ingredients.update({
                "vegetales": {
                    "remolacha",
                    "zanahoria",
                    "nabo",
                    "hinojo",
                    "coliflor",
                    "kale",
                    "brócoli",
                    "pepinillos fermentados",
                    "perejil",
                    "cebolla morada",
                    "rábanos"
                },
                "frutas": {
                    "toronja",
                    "piña",
                    "mango",
                    "papaya",
                    "bayas variadas"
                },
                "otros": {
                    "chocolate amargo",
                    "aceitunas",
                    "vino tinto (opcional)",
                    "almendras",
                    "anacardos",
                    "nueces de Brasil"
                }
            })
            
        else:  # NURTURE
            base_ingredients.update({
                "carbohidratos": {
                    "camote",
                    "yuca",
                    "papa roja",
                    "calabaza butternut",
                    "betabel",
                    "ñame",
                    "avena",
                    "arroz integral",
                    "quinoa",
                    "lentejas"
                },
                "frutas": {
                    "plátano",
                    "dátiles",
                    "higos",
                    "manzanas"
                },
                "otros": {
                    "semillas de girasol",
                    "chocolate amargo",
                    "garbanzos",
                    "manzanilla",
                    "jengibre",
                    "hinojo"
                },
                "proteinas": {
                    "pollo para caldo",
                    "pavo",
                    "legumbres variadas"
                },
                "suplementos": {
                    "magnesio",
                    "vitamina B6",
                    "omega-3"
                }
            })
        
        return base_ingredients
