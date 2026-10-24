MIN_CARD_DIGITS = 13
MAX_CARD_DIGITS = 19
RUT_FACTORS = (2, 3, 4, 5, 6, 7)


def digits_only(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def passes_luhn(number: str) -> bool:
    digits = digits_only(number)
    if not MIN_CARD_DIGITS <= len(digits) <= MAX_CARD_DIGITS:
        return False
    if len(set(digits)) == 1:
        return False
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def rut_check_digit(body: str) -> str:
    total = sum(
        int(char) * RUT_FACTORS[index % len(RUT_FACTORS)]
        for index, char in enumerate(reversed(body))
    )
    remainder = 11 - total % 11
    if remainder == 11:
        return "0"
    if remainder == 10:
        return "K"
    return str(remainder)


def is_valid_rut(value: str) -> bool:
    cleaned = value.replace(".", "").replace(" ", "").upper()
    body, separator, check = cleaned.partition("-")
    if not separator or not body.isdigit() or not 1 <= len(body) <= 8 or len(check) != 1:
        return False
    return rut_check_digit(body) == check
