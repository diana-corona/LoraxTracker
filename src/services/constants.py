"""
Constants and shared data for cycle-related services.
"""
from typing import Dict, List, Set
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType

TRADITIONAL_PHASE_RECOMMENDATIONS = {
    TraditionalPhaseType.MENSTRUATION: [
        "Rest and self-care",
        "Light exercise like walking or yoga",
        "Iron-rich foods",
        "Warm compress for cramps"
    ],
    TraditionalPhaseType.FOLLICULAR: [
        "High-intensity workouts",
        "Start new projects",
        "Social activities",
        "Learning new skills"
    ],
    TraditionalPhaseType.OVULATION: [
        "Challenging workouts",
        "Important presentations/meetings",
        "Social events",
        "Creative activities"
    ],
    TraditionalPhaseType.LUTEAL: [
        "Moderate exercise",
        "Organizational tasks",
        "Meal planning",
        "Relaxation techniques"
    ]
}

TRADITIONAL_PHASE_DURATIONS = {
    TraditionalPhaseType.MENSTRUATION: 5,
    TraditionalPhaseType.FOLLICULAR: 9,
    TraditionalPhaseType.OVULATION: 3,
    TraditionalPhaseType.LUTEAL: 11
}

TRADITIONAL_PHASE_SYMPTOMS = {
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

FUNCTIONAL_PHASE_DETAILS = {
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

PHASE_TRANSITIONS = {
    TraditionalPhaseType.MENSTRUATION: TraditionalPhaseType.FOLLICULAR,
    TraditionalPhaseType.FOLLICULAR: TraditionalPhaseType.OVULATION,
    TraditionalPhaseType.OVULATION: TraditionalPhaseType.LUTEAL,
    TraditionalPhaseType.LUTEAL: TraditionalPhaseType.MENSTRUATION
}

# Mapping of cycle days to functional phases
FUNCTIONAL_PHASE_MAPPING = [
    (1, 10, FunctionalPhaseType.POWER),
    (11, 15, FunctionalPhaseType.MANIFESTATION),
    (16, 19, FunctionalPhaseType.POWER),
    (20, 28, FunctionalPhaseType.NURTURE)
]

# Shopping list ingredients by phase
PHASE_INGREDIENTS = {
    FunctionalPhaseType.POWER: {
        "fats": {
            "avocado",
            "olive oil",
            "coconut oil",
            "ghee (clarified butter)",
            "mixed nuts"
        },
        "proteins": {
            "fish",
            "eggs",
            "tofu",
            "organic chicken"
        },
        "vegetables": {
            "broccoli",
            "brussels sprouts",
            "curly cabbage",
            "kale",
            "bok choy",
            "garlic",
            "onion",
            "leek",
            "dandelion root",
            "artichoke",
            "spinach",
            "sprouts"
        },
        "others": {
            "kimchi",
            "sauerkraut",
            "yogurt",
            "kefir"
        },
        "fruits": {
            "blueberries",
            "strawberries"
        }
    },
    FunctionalPhaseType.MANIFESTATION: {
        "vegetables": {
            "beetroot",
            "carrot",
            "turnip",
            "fennel",
            "cauliflower",
            "kale",
            "broccoli",
            "fermented pickles",
            "parsley",
            "red onion",
            "radishes"
        },
        "fruits": {
            "grapefruit",
            "pineapple",
            "mango",
            "papaya",
            "mixed berries"
        },
        "others": {
            "dark chocolate",
            "olives",
            "red wine (optional)",
            "almonds",
            "cashews",
            "brazil nuts"
        }
    },
    FunctionalPhaseType.NURTURE: {
        "carbohydrates": {
            "sweet potato",
            "cassava",
            "red potato",
            "butternut squash",
            "beetroot",
            "yam",
            "oats",
            "brown rice",
            "quinoa",
            "lentils"
        },
        "fruits": {
            "banana",
            "dates",
            "figs",
            "apples"
        },
        "others": {
            "sunflower seeds",
            "dark chocolate",
            "chickpeas",
            "chamomile",
            "ginger",
            "fennel"
        },
        "proteins": {
            "chicken for broth",
            "turkey",
            "mixed legumes"
        },
        "supplements": {
            "magnesium",
            "vitamin B6",
            "omega-3"
        }
    }
}

# Meal type icons
MEAL_ICONS = {
    "breakfast": "🥞",
    "lunch": "🥗",
    "dinner": "🍽️",
    "snack": "🍿"
}

# Shopping list category icons
SHOPPING_ICONS = {
    "proteins": "🥩",
    "vegetables": "🥬",
    "fruits": "🍎",
    "fats": "🥑",
    "carbohydrates": "🌾",
    "supplements": "💊",
    "others": "🧂",
    "pantry": "🥫",
    "basic": "📝"
}

# Common household ingredients that are assumed to be available
BASIC_INGREDIENTS: Set[str] = {
    # Seasonings
    "salt",
    "black pepper",
    "ground pepper",
    "pepper",
    
    # Oils
    "olive oil",
    "vegetable oil",
    "cooking oil",
    "oil",
    
    # Basic liquids
    "water",
    "ice water",
    "hot water",
    
    # Common spices
    "garlic powder",
    "onion powder",
    "paprika",
    "dried oregano",
    "dried basil",
    "ground cinnamon",
    
    # Basic condiments
    "mayonnaise",
    "mustard",
    "ketchup",
    
    # Pantry staples
    "flour",
    "sugar",
    "baking powder",
    "baking soda",
    "vanilla extract"
}
