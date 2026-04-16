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
    "ADDON_FOOD_ACCOMMODATION",
    "ADDON_SAFARI",
    "SAFARI_ROUTE",
    "GDTA_MEMBER",
    "GDTA_AFFILIATION",
    "COUNTRY",
    "STATE",
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
        "addon_food_accommodation_fee": food,
        "addon_safari_fee": safari,
        "total_fee": cfg["base"] + food + safari,
        "fixed_all_inclusive": cfg["fixed"],
    }


def _valid_email(email):
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email or ""))


def _yes(value):
    return str(value or "").strip().lower() in {"yes", "y", "true", "1"}


def initial_state():
    return {
        "current_step": "CONSENT",
        "is_active": True,
        "data": {
            "consent": None,
            "name": None,
            "title": None,
            "gender": None,
            "institution": None,
            "role": None,
            "registration_category": None,
            "addon_food_accommodation": "No",
            "addon_safari": "No",
            "safari_route": None,
            "gdta_member": None,
            "gdta_affiliation": None,
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
        cfg = FEE_CONFIG[value]
        if cfg["fixed"]:
            state["data"]["addon_food_accommodation"] = "No"
            state["data"]["addon_safari"] = "No"
            state["data"]["safari_route"] = None
            state["current_step"] = "GDTA_MEMBER"
        else:
            state["current_step"] = "ADDON_FOOD_ACCOMMODATION"
        return state, "Category recorded.", False

    if step == "ADDON_FOOD_ACCOMMODATION":
        if low not in {"yes", "y", "no", "n"}:
            raise ValueError("Food & accommodation add-on must be Yes or No")
        state["data"]["addon_food_accommodation"] = "Yes" if low in {"yes", "y"} else "No"
        state["current_step"] = "ADDON_SAFARI"
        return state, "Food & accommodation add-on recorded.", False

    if step == "ADDON_SAFARI":
        if low not in {"yes", "y", "no", "n"}:
            raise ValueError("Safari add-on must be Yes or No")
        state["data"]["addon_safari"] = "Yes" if low in {"yes", "y"} else "No"
        if state["data"]["addon_safari"] == "Yes":
            state["current_step"] = "SAFARI_ROUTE"
        else:
            state["data"]["safari_route"] = None
            state["current_step"] = "GDTA_MEMBER"
        return state, "Safari add-on recorded.", False

    if step == "SAFARI_ROUTE":
        normalized = low
        route_value = None
        if normalized in {"route 01", "route 1", "1", "01"}:
            route_value = SAFARI_ROUTES["route 01"]
        elif normalized in {"route 02", "route 2", "2", "02"}:
            route_value = SAFARI_ROUTES["route 02"]
        elif normalized in {"route 03", "route 3", "3", "03"}:
            route_value = SAFARI_ROUTES["route 03"]
        elif normalized in [x.lower() for x in SAFARI_ROUTES.values()]:
            for route in SAFARI_ROUTES.values():
                if normalized == route.lower():
                    route_value = route
                    break
        if not route_value:
            raise ValueError("Invalid safari route")
        state["data"]["safari_route"] = route_value
        state["current_step"] = "GDTA_MEMBER"
        return state, "Safari route recorded.", False

    if step == "GDTA_MEMBER":
        if low not in {"yes", "y", "no", "n"}:
            raise ValueError("GDTA member response must be Yes or No")
        state["data"]["gdta_member"] = "Yes" if low in {"yes", "y"} else "No"
        state["current_step"] = "GDTA_AFFILIATION"
        return state, "GDTA member response recorded.", False

    if step == "GDTA_AFFILIATION":
        if low not in {"yes", "y", "no", "n", "not sure", "notsure", "unsure"}:
            raise ValueError("GDTA affiliation must be Yes, No, or Not sure")
        if low in {"yes", "y"}:
            state["data"]["gdta_affiliation"] = "Yes"
        elif low in {"no", "n"}:
            state["data"]["gdta_affiliation"] = "No"
        else:
            state["data"]["gdta_affiliation"] = "Not sure"
        state["current_step"] = "COUNTRY"
        return state, "GDTA affiliation recorded.", False

    if step == "COUNTRY":
        if len(value) < 2:
            raise ValueError("Invalid country")
        state["data"]["country"] = value.title()
        if low == "india":
            state["current_step"] = "STATE"
        else:
            state["data"]["state"] = None
            state["current_step"] = "EMAIL"
        return state, "Country recorded.", False

    if step == "STATE":
        if len(value) < 2:
            raise ValueError("Invalid state")
        state["data"]["state"] = value.title()
        state["current_step"] = "EMAIL"
        return state, "State recorded.", False

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
