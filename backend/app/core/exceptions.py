class AppError(Exception):
    """Erro base da aplicação."""
    pass


class NotFoundError(AppError):
    """Recurso não encontrado."""
    pass


class InvalidChemicalDataError(AppError):
    """Dados químicos inválidos."""
    pass


class ImmutablePackageError(AppError):
    """Tentativa de alterar um pacote químico imutável."""
    pass


class DuplicateResourceError(AppError):
    """Recurso duplicado."""
    pass


class DatabaseIntegrityError(AppError):
    """Erro de integridade no banco de dados."""
    pass


