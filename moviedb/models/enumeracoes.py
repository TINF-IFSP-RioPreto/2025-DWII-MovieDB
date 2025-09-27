from enum import Enum


class JWT_action(Enum):
    """
    Enumeração que define as ações possíveis para tokens JWT.

    Attributes:
       NO_ACTION: Nenhuma ação específica indicada
       VALIDAR_EMAIL: Token usado para validação de email
       RESET_PASSWORD: Token usado para reset de senha
       PENDING_2FA: Token usado para indicar pendência de autenticação de dois fatores
    """
    NO_ACTION = 0
    VALIDAR_EMAIL = 1
    RESET_PASSWORD = 2
    PENDING_2FA = 3
    ACTIVATING_2FA = 4
