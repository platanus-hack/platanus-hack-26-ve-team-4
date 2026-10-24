class MemoryConfigError(RuntimeError):
    pass


class MemoryRejectedError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Escritura de memoria rechazada por Model Armor: {detail}")
        self.detail = detail
