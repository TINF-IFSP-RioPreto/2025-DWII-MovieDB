from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

import pyotp
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from .backup2fa_service import Backup2FAService
from .qrcode_service import QRCodeConfig, QRCodeService
from .. import db
from ..models.autenticacao import User


class Autenticacao2FA(Enum):
    """ Enumeração que define os resultados possíveis da autenticação de dois fatores."""
    INVALID_CODE = 0
    TOTP = 1
    BACKUP = 2
    REUSED = 3
    NOT_ENABLED = 4
    ENABLING = 5
    ALREADY_ENABLED = 6
    ENABLED = 7
    DISABLED = 8


@dataclass
class TwoFASetupResult:
    """Dados da configuração do 2FA."""
    status: Autenticacao2FA
    secret: str | None = None
    qr_code_base64: str | None = None
    backup_codes: list[str] | None = None


@dataclass
class TwoFAValidationResult:
    """Resultado da validação de código 2FA."""
    success: bool
    method_used: Optional[Autenticacao2FA]
    error_message: Optional[str]
    remaining_backup_codes: Optional[int]
    security_warnings: List[str]


@dataclass
class TwoFAStatus:
    """Status do 2FA para um usuário."""
    is_enabled: bool
    has_backup_codes: bool
    remaining_backup_codes: Optional[int]
    last_used_otp: Optional[str]
    last_login: Optional[datetime]


class User2FAError(Exception):
    pass


class User2FAService:
    """Serviço principal para gestão completa de 2FA de usuários."""

    @staticmethod
    def iniciar_ativacao_2fa(usuario: User) -> Optional[TwoFASetupResult]:
        """
        Inicia o processo de configuração do 2FA para um usuário.

        Args:
            usuario: Instância do usuário

        Returns:
            TwoFASetupResult: Dados necessários para completar a configuração

        Raises:
            User2FAError: Em caso de erro na configuração
            ValueError: Para parâmetros inválidos
        """

        if usuario.usa_2fa:
            return TwoFASetupResult(status=Autenticacao2FA.ALREADY_ENABLED)

        # Gera novo segredo TOTP
        secret = pyotp.random_base32()

        # Gera QRCode em base64
        qr_service = QRCodeService.create_default()
        app_name = current_app.config.get('APP_NAME', 'Sistema')
        qr_config = QRCodeConfig()
        qr_code_base64 = qr_service.generate_totp_qrcode_base64(secret=secret,
                                                                user=usuario.email,
                                                                issuer=app_name,
                                                                config=qr_config)

        return TwoFASetupResult(
                status=Autenticacao2FA.ENABLING,
                secret=secret,
                qr_code_base64=qr_code_base64)

    @staticmethod
    def confirmar_ativacao_2fa(usuario: User,
                               secret: str,
                               codigo_confirmacao: str,
                               gerar_backup_codes: bool = True,
                               quantidade_backup: int = 10) -> TwoFASetupResult:
        """
        Confirma a ativação do 2FA para o usuário, validando o código TOTP.

        Args:
            usuario: Instância do usuário
            secret: Segredo TOTP gerado
            codigo_confirmacao: Código TOTP fornecido pelo usuário
            gerar_backup_codes: Se deve gerar códigos de backup
            quantidade_backup: Quantidade de códigos de backup

        Returns:
            TwoFASetupResult: Resultado da ativação, incluindo códigos de backup se gerados
        """
        try:
            if usuario.usa_2fa:
                return TwoFASetupResult(status=Autenticacao2FA.ALREADY_ENABLED)

            totp = pyotp.TOTP(secret)
            if not totp.verify(codigo_confirmacao, valid_window=1):
                return TwoFASetupResult(status=Autenticacao2FA.INVALID_CODE)

            # Código válido, ativa 2FA
            usuario.usa_2fa = True
            usuario.otp_secret = secret
            usuario.ultimo_otp = codigo_confirmacao

            backup_codes = None
            if gerar_backup_codes:
                quantidade_backup = max(0, min(quantidade_backup, 20))
                backup_codes = Backup2FAService.gerar_novos_codigos(usuario, quantidade_backup)

            db.session.commit()

            return TwoFASetupResult(status=Autenticacao2FA.ENABLED, backup_codes=backup_codes)
        except SQLAlchemyError as e:
            db.session.rollback()
            raise User2FAError(f"Erro de banco de dados ao ativar 2FA: {str(e)}") from e
        except Exception as e:
            db.session.rollback()
            raise User2FAError(f"Erro ao ativar 2FA: {str(e)}") from e

    @staticmethod
    def desativar_2fa(usuario: User) -> TwoFASetupResult:
        """
        Desativa o 2FA para o usuário, removendo segredos e códigos de backup.

        Args:
            usuario: Instância do usuário

        Returns:
            TwoFASetupResult: Resultado da desativação
        """
        try:
            if not usuario.usa_2fa:
                return TwoFASetupResult(status=Autenticacao2FA.NOT_ENABLED)

            # Desativa 2FA
            usuario.usa_2fa = False
            usuario.otp_secret = None
            usuario.ultimo_otp = None
            db.session.commit()

            codigos_invalidados = Backup2FAService.invalidar_codigos(usuario)
            current_app.logger.warning("Desativado 2FA para usuário %s." % (usuario.email,))
            current_app.logger.warning("Códigos de backup invalidados: %d" % (codigos_invalidados,))
            return TwoFASetupResult(status=Autenticacao2FA.DISABLED)

        except SQLAlchemyError as e:
            db.session.rollback()
            raise User2FAError(f"Erro de banco de dados ao desativar 2FA: {str(e)}") from e
        except Exception as e:
            db.session.rollback()
            raise User2FAError(f"Erro ao desativar 2FA: {str(e)}") from e

    @staticmethod
    def validar_codigo_2fa(usuario: User, codigo: str) -> TwoFAValidationResult:
        """
        Valida um código 2FA (TOTP ou backup) para o usuário.

        Args:
            usuario: Instância do usuário
            codigo: Código 2FA fornecido

        Returns:
            TwoFAValidationResult: Resultado da validação, incluindo metodo usado e mensagens de
            erro
        """
        warnings = []

        try:
            # Confirma se 2FA está habilitado
            if not usuario.usa_2fa or not usuario.otp_secret:
                return TwoFAValidationResult(
                        success=False,
                        method_used=Autenticacao2FA.NOT_ENABLED,
                        error_message="2FA não está habilitado para este usuário.",
                        remaining_backup_codes=None,
                        security_warnings=warnings)

            # Verifica se o código já foi usado recentemente
            if codigo == usuario.ultimo_otp:
                warnings.append("Atenção: Este código já foi utilizado recentemente.")
                return TwoFAValidationResult(
                        success=False,
                        method_used=Autenticacao2FA.REUSED,
                        error_message="Código 2FA já foi utilizado recentemente.",
                        remaining_backup_codes=None,
                        security_warnings=warnings)

            # Tenta TOTP primeiro
            totp = pyotp.TOTP(usuario.otp_secret)
            if totp.verify(codigo, valid_window=1):
                usuario.ultimo_otp = codigo
                db.session.commit()

                # Verifica status dos códigos de backup
                backup_count = Backup2FAService.contar_tokens_disponiveis(usuario)
                if backup_count <= 2:
                    warnings.append(f"Poucos códigos de backup restantes: {backup_count}")

                return TwoFAValidationResult(
                        success=True,
                        method_used=Autenticacao2FA.TOTP,
                        error_message=None,
                        remaining_backup_codes=backup_count,
                        security_warnings=warnings
                )

            # Tenta código de backup
            if Backup2FAService.consumir_token(usuario, codigo):
                backup_count = Backup2FAService.contar_tokens_disponiveis(usuario)
                warnings.append("Código de backup utilizado")
                if backup_count == 0:
                    warnings.append("CRÍTICO: Nenhum código de backup restante")
                elif backup_count <= 2:
                    warnings.append(
                            f"ATENÇÃO: Apenas {backup_count} código(s) de backup restante(s)")

                return TwoFAValidationResult(
                        success=True,
                        method_used=Autenticacao2FA.BACKUP,
                        error_message=None,
                        remaining_backup_codes=backup_count,
                        security_warnings=warnings
                )

            # Codigo inválido
            return TwoFAValidationResult(
                    success=False,
                    method_used=Autenticacao2FA.INVALID_CODE,
                    error_message="Código 2FA inválido.",
                    remaining_backup_codes=None,
                    security_warnings=warnings)
        except Exception as e:
            current_app.logger.error("Erro na validação 2FA para %s: %s" % (usuario.email, str(e),))

            return TwoFAValidationResult(
                    success=False,
                    method_used=None,
                    error_message=f"Erro ao validar código 2FA: {str(e)}",
                    remaining_backup_codes=None,
                    security_warnings=warnings)

    @staticmethod
    def obter_status_2fa(usuario: User) -> TwoFAStatus:
        """
        Obtém o status atual do 2FA para o usuário.

        Args:
            usuario: Instância do usuário

        Returns:
            TwoFAStatus: Status do 2FA, incluindo se está habilitado, códigos de backup e último
            login
        """
        try:
            is_enabled = usuario.usa_2fa and bool(usuario.otp_secret)
            has_backup_codes = False
            remaining_backup_codes = None

            if is_enabled:
                remaining_backup_codes = Backup2FAService.contar_tokens_disponiveis(usuario)
                has_backup_codes = remaining_backup_codes > 0

            return TwoFAStatus(
                    is_enabled=is_enabled,
                    has_backup_codes=has_backup_codes,
                    remaining_backup_codes=remaining_backup_codes,
                    last_used_otp=usuario.ultimo_otp,
                    last_login=usuario.ultimo_login)
        except Exception as e:
            current_app.logger.error(
                "Erro ao obter status 2FA para %s: %s" % (usuario.email, str(e),))
            raise User2FAError(f"Erro ao obter status 2FA: {str(e)}") from e

    @staticmethod
    def otp_secret_formatted(usuario: User) -> Optional[str]:
        """
        Obtém o segredo OTP formatado para exibição.

        Args:
            usuario: Instância do usuário

        Returns:
            str | None: Segredo OTP formatado ou None se não disponível
        """
        if not usuario.otp_secret:
            return None
        # Formata em grupos de 4 caracteres
        return ' '.join(usuario.otp_secret[i:i + 4] for i in range(0, len(usuario.otp_secret), 4))

    @staticmethod
    def validar_tentative_otp_secret(tentative_secret: str,
                                     codigo: str) -> bool:
        totp = pyotp.TOTP(tentative_secret)
        return totp.verify(codigo, valid_window=1)
