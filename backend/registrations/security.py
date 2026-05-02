SANCTIONED_COUNTRIES = {
    "cuba",
    "iran",
    "north korea",
    "russia",
    "syria",
}

PAYMENT_STATUS_TOKEN_SALT = "gdta2026.payment-status"
PAYMENT_STATUS_TOKEN_MAX_AGE = 24 * 60 * 60


def is_sanctioned_country(country):
    return str(country or "").strip().lower() in SANCTIONED_COUNTRIES
