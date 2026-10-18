from core.search.constants import CHECKBOX_GROUPS

ACTIVITY_OKVED: dict[str, list[str]] = {
    "vent_mount": ["43.22", "43.21"],
    "ovik_design": ["71.12", "71.11"],
    "general_contract": ["41.20", "42.11"],
    "industrial_prod": ["24.10", "20.11", "10.11"],
    "commercial_build": ["41.10", "68.20"],
    "residential_build": ["41.10", "68.32"],
    "reconstruction": ["43.39", "43.91"],
    "energy_tek": ["35.11", "35.30", "06.10"],
    "infrastructure": ["42.11", "42.12", "52.23"],
    "food_pharma": ["10.11", "21.20"],
}

ACTIVITY_SEGMENT: dict[str, str] = {
    "vent_mount": "installer",
    "ovik_design": "designer",
    "general_contract": "contractor",
    "industrial_prod": "industrial",
    "commercial_build": "contractor",
    "residential_build": "contractor",
    "reconstruction": "contractor",
    "energy_tek": "industrial",
    "infrastructure": "contractor",
    "food_pharma": "industrial",
}

ALL_CHECKBOX_IDS = [
    item["id"]
    for group in CHECKBOX_GROUPS
    for item in group["items"]
]


def resolve_okved_codes(selected: list[str]) -> list[str]:
    codes: list[str] = []
    for checkbox_id in selected:
        codes.extend(ACTIVITY_OKVED.get(checkbox_id, []))
    return sorted(set(codes))


def resolve_primary_segment(selected: list[str]) -> str:
    for checkbox_id in selected:
        if checkbox_id in ACTIVITY_SEGMENT:
            return ACTIVITY_SEGMENT[checkbox_id]
    if "gov_tenders" in selected:
        return "contractor"
    return "installer"
