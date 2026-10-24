from agent_zero.runtime.handlers import RunHandler


class UnknownHandlerError(LookupError):
    def __init__(self, name: str) -> None:
        super().__init__(f"No existe un manejador registrado con el nombre {name}.")
        self.name = name


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, RunHandler] = {}

    def register(self, handler: RunHandler) -> None:
        self._handlers[handler.name] = handler

    def get(self, name: str) -> RunHandler:
        handler = self._handlers.get(name)
        if handler is None:
            raise UnknownHandlerError(name)
        return handler

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))
