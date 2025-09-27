from time import time
from typing import Any, Dict, Optional

import jwt
from flask import current_app

from moviedb.models.enumeracoes import JWT_action


def create_jwt_token(action: JWT_action = JWT_action.NO_ACTION,
                     sub: Any = None,
                     expires_in: int = 600,
                     extra_data: Optional[Dict[Any, Any]] = None) -> str:
    """
    Cria um token JWT com os parâmetros fornecidos.

    Args:
        action: A ação para a qual o token está sendo usado (opcional).
        sub: O assunto do token (por exemplo, email do usuário).
        expires_in: O tempo de expiração do token em segundos. Se for negativo, o token não
        expira. Default de 10min
        extra_data: Dicionário com dados adicionais para incluir no payload (opcional).

    Returns:
        O token JWT codificado com as reivindicações sub, iat, nbf, action e, opcionalmente,
        exp e extra_data.

    Raises:
        ValueError: Se o objeto 'sub' não puder ser convertido em string.
    """

    if not hasattr(type(sub), '__str__'):  # isinstance(sub, (str, int, float, uuid.UUID)):
        raise ValueError(f"Tipo de objeto 'sub' inválido: {type(sub)}")

    agora = int(time())
    payload = {
        'sub'   : str(sub),
        'iat'   : agora,
        'nbf'   : agora,
        'action': action.name
    }
    if expires_in > 0:
        payload['exp'] = agora + expires_in
    if extra_data is not None and isinstance(extra_data, dict):
        payload['extra_data'] = extra_data
    return jwt.encode(payload=payload,
                      key=current_app.config.get('SECRET_KEY'),
                      algorithm='HS256')


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verifica um token JWT e retorna suas reivindicações.

    Args:
        token: O token JWT a ser verificado.

    Returns:
        Um dicionário contendo as reivindicações do token.
        O dicionário sempre conterá uma chave 'valid' (booleano).
        Se o token for inválido, uma chave 'reason' pode estar presente.
        Se o token for válido, ele conterá 'sub', 'action', 'age' e 'extra_data' (se presentes).
    """
    claims: Dict[str, Any] = {'valid': False}

    try:
        payload = jwt.decode(token,
                             key=current_app.config.get('SECRET_KEY'),
                             algorithms=['HS256'])

        if not 'sub' in payload:
            claims.update({'reason': "missing_sub"})
            return claims

        acao = JWT_action[payload.get('action', 'NO_ACTION')]
        claims.update({'valid' : True,
                       'sub'   : payload.get('sub', None),
                       'action': acao})

        if 'iat' in payload:
            claims.update({'age': int(time()) - int(payload.get('iat'))})

        if 'extra_data' in payload:
            claims.update({'extra_data': payload.get('extra_data')})

    except jwt.ExpiredSignatureError as e:
        current_app.logger.error("JWT Expired: %s" % (e,))
        claims.update({'reason': "expired"})
    except jwt.InvalidTokenError as e:
        current_app.logger.error("Invalid JWT: %s" % (e,))
        claims.update({'reason': "invalid"})
    except jwt.InvalidSignatureError as e:
        current_app.logger.error("Invalid JWT signature: %s" % (e,))
        claims.update({'reason': "bad_signature"})
    except ValueError as e:
        current_app.logger.error("ValueError: %s" % (e,))
        claims.update({'reason': "valueerror"})

    return claims
