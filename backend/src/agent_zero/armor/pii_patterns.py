import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
CARD = re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])")
RUT = re.compile(r"(?<![\w.])\d{1,2}(?:\.?\d{3}){2}\s?-\s?[\dkK](?![\w])")
CEDULA = re.compile(r"(?<![A-Za-z0-9])[VvEe]\s?-\s?\d{0,3}(?:\.?\d{3}){2}(?!\d)")

PHONE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![\w+])\+56[\s-]?\d(?:[\s-]?\d){8}(?!\d)"),
    re.compile(r"(?<![\w+])56[\s-]?9(?:[\s-]?\d){8}(?!\d)"),
    re.compile(r"(?<![\w+])9[\s-]?\d{4}[\s-]?\d{4}(?![\d-])"),
    re.compile(r"(?<![\w+])\+58[\s-]?\(?0?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}(?!\d)"),
    re.compile(
        r"(?<![\w+])0\(?(?:4(?:12|14|16|24|26)|2\d{2})\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"
    ),
)
