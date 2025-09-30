import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import List

from sqlalchemy import delete, insert
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from moviedb import db
from moviedb.models.autenticacao import Backup2FA, User


class KeepForDays(Enum):
    """ Enumeração que define opções para o número de dias para manter dados antes de removê-los
    fisicamente."""
    ZERO = 0
    ONE_WEEK = 7
    TWO_WEEKS = 14
    THREE_WEEKS = 21
    ONE_MONTH = 30
    TWO_MONTHS = 60
    THREE_MONTHS = 90
    SIX_MONTHS = 180
    ONE_YEAR = 365


class Backup2FAService:
    """Serviço responsável pela gestão de códigos de backup 2FA."""

    # Conjunto de caracteres sem ambiguidade visual
    CHARSET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    CODIGO_LENGTH = 6

    @staticmethod
    def _obter_tokens(usuario: User, unused_only: bool = False) -> List['Backup2FA']:
        """
        Recupera todos os códigos de backup 2FA do usuário.

        Args:
            usuario (User): Instância do usuário cujos códigos serão listados.
            unused_only (bool): Se True, retorna apenas códigos não utilizados.

        Returns:
            list[Backup2FA]: Lista de códigos de backup 2FA disponíveis.
        """
        if unused_only:
            return list(
                Backup2FA.get_all_by(criteria={"usuario_id": usuario.id, "utilizado": False}).all())
        else:
            return list(Backup2FA.get_all_by(criteria={"usuario_id": usuario.id}).all())

    @staticmethod
    def _gerar_codigo_aleatorio() -> str:
        """Gera um código aleatório usando charset seguro."""
        return ''.join(
                secrets.choice(Backup2FAService.CHARSET)
                for _ in range(Backup2FAService.CODIGO_LENGTH)
        )

    @staticmethod
    def _invalidar_codigo(backup_code: Backup2FA,
                          keep_for_days: KeepForDays = KeepForDays.ONE_MONTH) -> None:
        """
        Marca o código como utilizado e define a data de remoção efetiva do banco.

        Args:
            backup_code (Backup2FA): Instância do código de backup a ser invalidado.
            keep_for_days (KeepForDays): Número de dias para manter o código marcado como usado
                antes de removê-lo fisicamente (default: 30)
        """
        agora = datetime.now()
        backup_code.utilizado = True
        backup_code.dta_uso = agora
        backup_code.dta_para_remocao = agora + timedelta(days=keep_for_days.value)

    @staticmethod
    def consumir_token(usuario: User, token: str,
                       keep_for_days: KeepForDays = KeepForDays.ONE_MONTH) -> bool:
        """
        Verifica e consome o token de backup 2FA, marcando-o como utilizado e definindo a data de
            remoção efetiva do banco.

        Args:
            usuario (User): Instância do usuário ao qual o código pertence.
            token (str): Código de backup 2FA a ser verificado.
            keep_for_days (KeepForDays): Número de dias para manter o código marcado como usado
                antes de removê-lo fisicamente (default: 30)

        Returns:
            bool: True se o código existir e estiver não utilizado, False caso contrário.
        """
        try:
            # Busca códigos não utilizados do usuário
            codigos_disponiveis = Backup2FAService._obter_tokens(usuario, unused_only=True)

            for backup_code in codigos_disponiveis:
                if check_password_hash(backup_code.hash_codigo, token):
                    Backup2FAService._invalidar_codigo(backup_code, KeepForDays(keep_for_days))
                    db.session.commit()
                    return True

            return False

        except SQLAlchemyError:
            db.session.rollback()
            return False

    @staticmethod
    def contar_tokens_disponiveis(usuario: User) -> int:
        """
        Conta a quantidade de códigos de backup 2FA ainda não utilizados do usuário.

        Args:
            usuario (User): Instância do usuário cujo códigos serão contados.

        Returns:
            int: Número de códigos de backup 2FA disponíveis.
        """
        tokens = Backup2FAService._obter_tokens(usuario, unused_only=True)
        return len(tokens)

    @staticmethod
    def invalidar_codigos(usuario: User, keep_for_days: KeepForDays = KeepForDays.ONE_MONTH) -> int:
        """
        Marca todos os códigos do usuário como utilizados.

        Args:
            usuario (User): Instância do usuário cujos códigos serão invalidados.
            keep_for_days (int): Número de dias para manter o código marcado como usado antes de
                removê-lo fisicamente (default: 30)

        Returns:
            int: Número de códigos marcados como usados.
        """
        try:
            codigos_validos = Backup2FAService._obter_tokens(usuario, unused_only=True)

            count = 0
            for codigo in codigos_validos:
                Backup2FAService._invalidar_codigo(codigo, keep_for_days)
                count += 1

            db.session.commit()
            return count

        except SQLAlchemyError:
            db.session.rollback()
            return 0

    @staticmethod
    def gerar_novos_codigos(usuario: User, quantidade: int = 5) -> List[str]:
        """
        Gera novos códigos de backup, removendo os anteriores não utilizados.

        Args:
            usuario: Instância do usuário
            quantidade: Número de códigos a gerar

        Returns:
            Lista com os códigos em texto plano (para exibir ao usuário)

        Raises:
            SQLAlchemyError: Em caso de erro na transação
        """
        try:
            # Remove códigos não utilizados
            qtd = Backup2FAService.invalidar_codigos(usuario)

            # Gera novos códigos
            codigos_texto_plano = []
            novos_backups = []

            for _ in range(quantidade):
                codigo_plano = Backup2FAService._gerar_codigo_aleatorio()
                codigo_hash = generate_password_hash(codigo_plano)

                codigos_texto_plano.append(codigo_plano)
                novos_backups.append({"hash_codigo": codigo_hash,
                                      "usuario_id" : usuario.id,
                                      "utilizado"  : False})
            db.session.execute(insert(Backup2FA), novos_backups)
            db.session.commit()

            return codigos_texto_plano

        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    @staticmethod
    def remover_codigos_expirados() -> int:
        """
        Remove fisicamente do banco todos os códigos que já passaram da data de remoção.

        Idealmente executado por uma tarefa Celery periódica (uma vez ao dia).

        Returns:
            int: Número de códigos removidos.
        """
        try:
            agora = datetime.now()
            stmt = delete(Backup2FA).where(
                    Backup2FA.dta_para_remocao.isnot(None),
                    Backup2FA.dta_para_remocao <= agora)
            result = db.session.execute(stmt)
            db.session.commit()
            return result.rowcount or 0

        except SQLAlchemyError:
            db.session.rollback()
            return 0
