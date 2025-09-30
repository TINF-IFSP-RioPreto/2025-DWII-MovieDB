import base64
import hashlib
from threading import RLock
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app
from sqlalchemy import String, TypeDecorator


class EncryptedType(TypeDecorator):
    """Tipo personalizado do SQLAlchemy para criptografia automática de dados.

    Este tipo automaticamente: a) criptografa dados durante a escrita no banco; b) descriptografa
    dados durante a leitura do banco, e; c) mantém compatibilidade com valores None/NULL.
    """

    impl = String
    cache_ok = True

    # Cache global thread-safe para instâncias Fernet
    _fernet_cache: Dict[str, Fernet] = {}
    _cache_lock = RLock()

    def __init__(self, encryption_key: str = None, salt_key: str = None, *args, **kwargs):
        """Inicializa o tipo criptografado com configuração lazy.

        Args:
            encryption_key (Optional[str]): Chave de criptografia no current_app.config.
            salt_key (Optional[str]): Valor do salt no current_app.config.
            *args: Argumentos adicionais posicionais.
            **kwargs: Argumentos adicionais nomeados.
        """
        # @formatter:on
        super().__init__(*args, **kwargs)

        self.encryption_key = encryption_key or "ENCRYPTION_KEY"
        self.salt_key = salt_key or "ENCRYPTION_SALT"

    def _get_encryption_key_and_salt(self) -> tuple[str, Union[bytes, str]]:
        """Recupera a chave de criptografia e o salt do current_app.config.

        Returns:
            tuple[str, Union[bytes, str]]: Tuple contendo a chave de criptografia e o salt.

        Raises:
            RuntimeError: Se o contexto da aplicação Flask não está disponível.
            ValueError: Se as chaves de configuração não estão definidas.
            TypeError: Se o salt não é str ou bytes.
        """
        if not current_app:
            raise RuntimeError("O contexto da aplicação Flask não está disponível.")

        encryption_key = current_app.config.get(self.encryption_key)
        if not encryption_key:
            raise ValueError(f"A chave de configuração '{self.encryption_key}' não está definida.")

        salt = current_app.config.get(self.salt_key)
        if not salt:
            raise ValueError(f"A chave de configuração '{self.salt_key}' não está definida.")

        # Converter salt para bytes se necessário
        if isinstance(salt, str):
            # Se for string ASCII, converter para bytes
            if all(32 <= ord(c) <= 126 for c in salt):
                salt_bytes = salt.encode('utf-8')
            else:
                # Se for string hexadecimal, converter de hex
                try:
                    salt_bytes = bytes.fromhex(salt)
                except ValueError:
                    # Se for base64, decodificar
                    try:
                        salt_bytes = base64.urlsafe_b64decode(salt.encode('ascii'))
                    except Exception:
                        # Fallback: usar hash da string
                        salt_bytes = hashlib.sha256(salt.encode()).digest()
        elif isinstance(salt, bytes):
            salt_bytes = salt
        else:
            raise TypeError(f"Salt deve ser str ou bytes, recebido: {type(salt)}")

        return encryption_key, salt_bytes

    def _get_fernet(self) -> Fernet:
        """Obtém instância Fernet com cache thread-safe.

        Returns:
            Fernet: Instância Fernet configurada.
        """
        # Criar chave de cache baseada na configuração
        encryption_key, salt_bytes = self._get_encryption_key_and_salt()
        cache_key = f"{encryption_key}:{salt_bytes.hex()}"

        with self._cache_lock:
            if cache_key not in self._fernet_cache:
                kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt_bytes,
                        iterations=100000,
                )
                fernet_key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
                self._fernet_cache[cache_key] = Fernet(fernet_key)

            return self._fernet_cache[cache_key]

    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """Criptografa valor para armazenamento.

        Args:
            value (Any): Valor a ser criptografado.
            dialect: Dialeto do SQLAlchemy.

        Returns:
            Optional[str]: Valor criptografado em base64 ou None.

        Raises:
            TypeError: Se o valor não pode ser convertido para string.
        """
        if value is None:
            return None

        try:
            value_str = str(value)
        except Exception as e:
            raise TypeError(f"Não foi possível converter o valor para string: {e}")

        fernet = self._get_fernet()
        encrypted_bytes = fernet.encrypt(value_str.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('ascii')

    def process_result_value(self, value: Any, dialect) -> Optional[str]:
        """Descriptografa valor do banco.

        Args:
            value (Any): Valor criptografado do banco de dados.
            dialect: Dialeto do SQLAlchemy.

        Returns:
            Optional[str]: Valor descriptografado ou None.

        Raises:
            ValueError: Se houver erro ao descriptografar dados.
        """
        if value is None:
            return None

        try:
            fernet = self._get_fernet()
            encrypted_bytes = base64.urlsafe_b64decode(value.encode('ascii'))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Erro ao descriptografar dados: {e}")
