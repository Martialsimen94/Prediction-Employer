"""Domain-level exceptions, translated to HTTP responses by main.py's
centralized exception handlers instead of scattering try/except across
every endpoint."""


class NotFoundError(Exception):
    def __init__(self, resource: str, identifier: object) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} {identifier!r} not found")


class ConflictError(Exception):
    pass


class ValidationError(Exception):
    pass
