SECTION_MAP = {
    "title": "title",
    "abstract": "abstract",
    "keywords": "keywords",

    "intro": "introduction",
    "introduction": "introduction",
    "background": "introduction",

    "method": "methodology",
    "methods": "methodology",
    "methodology": "methodology",

    "result": "results",
    "results": "results",

    "conclusion": "conclusion",
    "concluding remarks": "conclusion",

    "reference": "references",
    "references": "references"
}

EXPECTED_SECTIONS = [
    "title",
    "abstract",
    "keywords",
    "introduction",
    "methodology",
    "results",
    "conclusion",
    "references"
]

def normalize_section_name(name: str):
    return SECTION_MAP.get(name.lower().strip(), None)