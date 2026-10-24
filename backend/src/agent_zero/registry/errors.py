class RegistryError(Exception):
    pass


class VersionAlreadyPublishedError(RegistryError):
    def __init__(self, agent_id: str, version: str) -> None:
        super().__init__(f"La versión {version} de {agent_id} ya fue publicada y es inmutable.")
        self.agent_id = agent_id
        self.version = version


class VersionNotFoundError(RegistryError):
    def __init__(self, agent_id: str, version: str | None = None) -> None:
        detail = f"{agent_id} {version}" if version else agent_id
        super().__init__(f"No existe en el registro: {detail}.")
        self.agent_id = agent_id
        self.version = version


class VersionNotApprovedError(RegistryError):
    def __init__(self, agent_id: str, version: str, status: str) -> None:
        super().__init__(f"La versión {version} de {agent_id} no está aprobada (estado: {status}).")
        self.agent_id = agent_id
        self.version = version
        self.status = status


class ManifestRejectedError(RegistryError):
    def __init__(self, reasons: tuple[str, ...]) -> None:
        super().__init__("Manifiesto rechazado por Model Armor: " + "; ".join(reasons))
        self.reasons = reasons


class InvalidTransitionError(RegistryError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Transición no permitida: {current} → {target}")
        self.current = current
        self.target = target
