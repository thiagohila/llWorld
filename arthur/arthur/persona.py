"""Who Arthur is. For now only what the world needs: name, realm, age, traits.

The traits are the game's own agent traits (0..1) and go straight onto
Arthur's person; as chieftain he pulls the tribe's aggression toward his.
Goals, voice and limits come with his mind (stage 3).
"""

ARTHUR = {
    "name": "Arthur",
    "family": "Pendragon",
    "title": "King",
    "realm": "Kingdom of Arthur",
    "seat": "Camelot",
    "age_years": 30,
    "people": 10,
    "traits": {"aggression": 0.35, "caution": 0.55, "industry": 0.6},
}
