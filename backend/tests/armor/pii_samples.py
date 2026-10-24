VALID_CARDS: tuple[str, ...] = ("4111 1111 1111 1111", "5500-0000-0000-0004", "378282246310005")
INVALID_CARDS: tuple[str, ...] = ("4111 1111 1111 1112", "1234 5678 9012 3456", "9876543210123")
VALID_RUTS: tuple[str, ...] = ("12.345.678-5", "76.086.428-5", "11.111.111-1", "7654321-6")
INVALID_RUTS: tuple[str, ...] = ("12.345.678-9", "76.086.428-1")
CEDULAS: tuple[str, ...] = ("V-12345678", "E-1234567", "V-12.345.678", "e-987654321")
EMAILS: tuple[str, ...] = ("maria.perez@tienda.cl", "juan+pedidos@correo.com.ve")
PHONES: tuple[str, ...] = (
    "+56 9 8765 4321",
    "+56987654321",
    "9 8765 4321",
    "+58 412-1234567",
    "+584141234567",
    "0412-1234567",
    "04241234567",
    "0212 555 12 34",
)

ZERO_WIDTH_SPACE = chr(0x200B)
NO_BREAK_SPACE = chr(0xA0)
FULLWIDTH_AT = chr(0xFF20)

EVASIVE_CARDS: tuple[str, ...] = (
    "4111.1111.1111.1111",
    "4111/1111/1111/1111",
    f"4111{NO_BREAK_SPACE}1111{NO_BREAK_SPACE}1111{NO_BREAK_SPACE}1111",
    f"4111{ZERO_WIDTH_SPACE}1111{ZERO_WIDTH_SPACE}1111{ZERO_WIDTH_SPACE}1111",
)
EVASIVE_CEDULAS: tuple[str, ...] = ("V12345678", "V 12345678", "E1234567")
EVASIVE_EMAILS: tuple[str, ...] = (
    f"juan@ejem{ZERO_WIDTH_SPACE}plo.com",
    f"juan{FULLWIDTH_AT}ejemplo.com",
    f"ju{ZERO_WIDTH_SPACE}an@ejemplo.com",
)
