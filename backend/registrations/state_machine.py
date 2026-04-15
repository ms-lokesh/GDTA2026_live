import re


FEE_CONFIG = {
    "Student": {"currency": "INR", "base": 500, "food": 500, "safari": 500, "fixed": False},
    "Academician": {"currency": "INR", "base": 2000, "food": 500, "safari": 500, "fixed": False},
    "Industry People": {"currency": "INR", "base": 7500, "food": 0, "safari": 0, "fixed": True},
    "Foreign Student": {"currency": "USD", "base": 15, "food": 0, "safari": 0, "fixed": True},
    "Foreign Academician": {"currency": "USD", "base": 100, "food": 0, "safari": 0, "fixed": True},
    "Foreign Industry People": {"currency": "USD", "base": 100, "food": 0, "safari": 0, "fixed": True},
    "Foreign Delegate": {"currency": "USD", "base": 100, "food": 0, "safari": 0, "fixed": True},
}

SAFARI_ROUTES = {
    "route 01": "Route 01 - Spiritual Origins & Sacred Landscapes",
    "route 02": "Route 02 - Urban Pulse & Living Heritage",
    "route 03": "Route 03 - Industrial Legacy & Rural Faith",
}

FLOW = [
    "CONSENT",
    "NAME",
    "INSTITUTION",
    "ROLE",
    "CATEGORY",
    "ADDONS",
    "COUNTRY",
    "EMAIL",
    "REVIEW",
    "CONFIRM",
    "COMPLETE",
]


def compute_fee(category, addon_food=False, addon_safari=False):
    cfg = FEE_CONFIG.get(category)
    if not cfg:
        return None
    food = 0 if cfg["fixed"] else (cfg["food"] if addon_food else 0)
    safari = 0 if cfg["fixed"] else (cfg["safari"] if addon_safari else 0)
    return {
        "fee_currency": cfg["currency"],
        "base_fee": cfg["base"],
        "addon_food_fee": food,
        "addon_safari_fee": safari,
        "total_fee": cfg["base"] + food + safari,
        "fixed_all_inclusive": cfg["fixed"],
    }


def _valid_email(email):
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email or ""))


def initial_state():
    return {
        "current_step": "CONSENT",
        "is_active": True,
        "data": {
            "consent": None,
            "name": None,
            "institution": None,
            "role": None,
            "registration_category": None,
            "addon_food": False,
            "addon_safari": False,
            "safari_route": None,
            "country": None,
            "state": None,
            "email": None,
        },
    }


def process(state, answer):
    step = state["current_step"]
    value = (answer or "").strip()
    low = value.lower()

    if step == "CONSENT":
        if low in {"no", "n"}:
            state["is_active"] = False
            state["current_step"] = "COMPLETE"
            return state, "Consent denied. Registration terminated.", True
        if low in {"yes", "y"}:
            state["data"]["consent"] = "Yes"
            state["current_step"] = "NAME"
            return state, "Consent recorded.", False
        raise ValueError("Consent must be Yes or No")

    if step == "NAME":
        if len(value) < 2:
            raise ValueError("Invalid name")
        state["data"]["name"] = value.title()
        state["current_step"] = "INSTITUTION"
        return state, "Name recorded.", False

    if step == "INSTITUTION":
        if len(value) < 2:
            raise ValueError("Invalid institution")
        state["data"]["institution"] = value
        state["current_step"] = "ROLE"
        return state, "Institution recorded.", False

    if step == "ROLE":
        if len(value) < 2:
            raise ValueError("Invalid role")
        state["data"]["role"] = value
        state["current_step"] = "CATEGORY"
        return state, "Role recorded.", False

    if step == "CATEGORY":
        if value not in FEE_CONFIG:
            raise ValueError("Invalid category")
        state["data"]["registration_category"] = value
        state["current_step"] = "ADDONS"
        return state, "Category recorded.", False

    if step == "ADDONS":
        parts = [p.strip().lower() for p in value.split(",")]
        state["data"]["addon_food"] = "food" in parts
        state["data"]["addon_safari"] = "safari" in parts
        if not state["data"]["addon_safari"]:
            state["data"]["safari_route"] = None
        state["current_step"] = "COUNTRY"
        return state, "Add-ons recorded.", False

    if step == "COUNTRY":
        if len(value) < 2:
            raise ValueError("Invalid country")
        state["data"]["country"] = value.title()
        if value.lower() != "india":
            state["data"]["state"] = None
        state["current_step"] = "EMAIL"
        return state, "Country recorded.", False

    if step == "EMAIL":
        if not _valid_email(value):
            raise ValueError("Invalid email")
        state["data"]["email"] = value.lower()
        state["current_step"] = "REVIEW"
        return state, "Email recorded.", False

    if step == "REVIEW":
        if low == "continue":
            state["current_step"] = "CONFIRM"
            return state, "Review complete.", False
        raise ValueError("Type 'continue' to proceed")

    if step == "CONFIRM":
        if low != "confirm":
            raise ValueError("Type 'confirm' to submit")
        state["current_step"] = "COMPLETE"
        state["is_active"] = False
        return state, "Registration complete.", True

    raise ValueError("Invalid state")
