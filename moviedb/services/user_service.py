from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from flask import current_app, render_template, url_for
from flask_login import login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from moviedb import db
from moviedb.models.autenticacao import User
from .email_service import EmailValidationService
from .token_service import JWTService, JWT_action


class UserOperationStatus(Enum):
    """Status das operações de usuário."""
    SUCCESS = 0
    USER_NOT_FOUND = 1
    USER_ALREADY_ACTIVE = 2
    USER_INACTIVE = 3
    INVALID_TOKEN = 4
    TOKEN_EXPIRED = 5
    INVALID_UUID = 6
    EMAIL_SEND_ERROR = 7
    DATABASE_ERROR = 8
    INVALID_CREDENTIALS = 9
    UNKNOWN = 99


@dataclass
class UserRegistrationResult:
    """Resultado da operação de registro de usuário."""
    status: UserOperationStatus
    user: Optional[User] = None
    token: Optional[str] = None
    email_sent: bool = False
    error_message: Optional[str] = None


@dataclass
class EmailValidationResult:
    """Resultado da operação de validação de email."""
    status: UserOperationStatus
    user: Optional[User] = None
    token: Optional[str] = None
    email_sent: bool = False
    error_message: Optional[str] = None


@dataclass
class PasswordResetResult:
    """Resultado da operação de reset de senha."""
    status: UserOperationStatus
    user: Optional[User] = None
    error_message: Optional[str] = None


class UserService:
    """Serviço responsável por operações de negócio relacionadas aos usuários."""

    @staticmethod
    def _enviar_email_confirmacao(usuario: User, email_service) -> tuple[str, bool]:
        """
        Método auxiliar privado para enviar email de confirmação.

        Args:
            usuario: Instância do usuário
            email_service: Instância do serviço de email

        Returns:
            tuple[str, bool]: (token gerado, sucesso no envio)
        """
        token = JWTService.create(action=JWT_action.VALIDAR_EMAIL, sub=usuario.email)
        current_app.logger.debug("Token de validação de email: %s" % (token,))

        body = render_template('auth/email/email_confirmation.jinja2',
                             nome=usuario.nome,
                             url=url_for('auth.valida_email', token=token, _external=True))
        result = email_service.send_email(to=usuario.email,
                                         subject="Confirme o seu email",
                                         text_body=body)

        email_sent = result.success
        if not email_sent:
            current_app.logger.error(
                "Erro no envio do email de confirmação para %s" % (usuario.email,))

        return token, email_sent

    @staticmethod
    def confirmar_email(usuario: User) -> bool:
        """
        Confirma o email do usuário, ativando sua conta.

        Args:
            usuario: Instância do usuário

        Returns:
            bool: True se a operação foi bem-sucedida

        Raises:
            SQLAlchemyError: Em caso de erro na transação
        """

        try:
            if usuario.ativo:
                current_app.logger.warning(
                    "Tentativa de confirmar email já confirmado: %s" % (usuario.email,))
                return True  # Já está confirmado, não é erro

            usuario.ativo = True
            usuario.dta_validacao_email = datetime.now()

            db.session.commit()

            current_app.logger.info("Email confirmado para usuário: %s" % (usuario.email,))
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(
                "Erro ao confirmar email do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @staticmethod
    def desconfirmar_email(usuario: User) -> bool:
        """
        Desconfirma o email do usuário, desativando sua conta.

        Args:
            usuario: Instância do usuário

        Returns:
            bool: True se a operação foi bem-sucedida

        Raises:
            SQLAlchemyError: Em caso de erro na transação
        """

        try:
            if not usuario.ativo:
                current_app.logger.warning(
                    "Tentativa de desconfirmar email ainda não confirmado: %s" % (usuario.email,))
                return True  # Já está confirmado, não é erro

            usuario.ativo = False
            usuario.dta_validacao_email = None

            db.session.commit()

            current_app.logger.info("Email desconfirmado para usuário: %s" % (usuario.email,))
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(
                "Erro ao desconfirmar email do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @staticmethod
    def pode_logar(usuario: User) -> bool:
        """
        Verifica se o usuário está ativo e pode efetuar login.

        Args:
            usuario: Instância do usuário

        Returns:
            bool: True se o usuário pode logar, False caso contrário
        """
        if not usuario.ativo:
            current_app.logger.warning("Usuário inativo tentou logar: %s" % (usuario.email,))
            return False
        return True

    @staticmethod
    def efetuar_login(usuario: User, remember_me: bool = False) -> bool:
        """
        Efetua o login do usuário no sistema.

        Args:
            usuario: Instância do usuário
            remember_me: Se True, mantém o usuário logado por mais tempo

        Returns:
            bool: True se o login foi bem-sucedido

        Raises:
            ValueError: Se o usuário não estiver ativo
            SQLAlchemyError: Em caso de erro na transação
        """
        try:
            if not UserService.pode_logar(usuario):
                raise ValueError(f"Usuário {usuario.email} não está ativo")

            # Efetua login usando Flask-Login
            login_user(usuario, remember=remember_me)

            # Atualiza timestamp de último login
            usuario.ultimo_login = db.func.now()

            db.session.commit()

            current_app.logger.info("Login efetuado para usuário: %s" % (usuario.email,))
            return True

        except ValueError:
            raise  # Re-propaga erro de validação
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error("Erro ao efetuar login do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @staticmethod
    def set_pending_2fa_token_data(usuario: User, remember_me: bool = False, next_page: str = None) -> str:
        """
        Cria um token para iniciar o fluxo de autenticação de dois fatores (2FA).

        Args:
            usuario: Instância do usuário
            remember_me: Se True, mantém o usuário logado por mais tempo
            next_page: Página para redirecionamento após 2FA

        Returns:
            str: Token gerado para 2FA
        """
        return JWTService.create(action=JWT_action.PENDING_2FA,
                              sub=usuario.id,
                              expires_in=current_app.config.get('2FA_SESSION_TIMEOUT', 90),
                              extra_data={
                                  'remember_me': remember_me,
                                  'next'       : next_page
                              })

    @staticmethod
    def get_pending_2fa_token_data(token: str) -> dict:
        """
        Decodifica o token de 2FA e retorna os dados contidos nele.

        Args:
            token: Token JWT de 2FA

        Returns:
            dict: Dados extraídos do token
        """

        dados_token = JWTService.verify(token)
        if not dados_token.get('valid', False) or \
                dados_token.get('action') != JWT_action.PENDING_2FA or \
                not dados_token.get('extra_data', False):
            dados_token['valid'] = False
        return dados_token

    @staticmethod
    def efetuar_logout(usuario: User) -> bool:
        """
        Efetua o logout do usuário do sistema.

        Args:
            usuario: Instância do usuário

        Returns:
            bool: True se o logout foi bem-sucedido
        """
        try:
            user_email = usuario.email  # Captura antes do logout
            logout_user()

            current_app.logger.info("Logout efetuado para usuário: %s" % (user_email, ))
            return True

        except Exception as e:
            current_app.logger.error("Erro ao efetuar logout: %s" % (str(e), ))
            return False

    @staticmethod
    def e_primeira_sessao(usuario: User) -> bool:
        """
        Verifica se esta é a primeira vez que o usuário faz login.

        Args:
            usuario: Instância do usuário

        Returns:
            bool: True se é o primeiro login
        """
        return usuario.ultimo_login is None

    @staticmethod
    def registrar_usuario(nome: str, email: str, password: str,
                         email_service) -> UserRegistrationResult:
        """
        Registra um novo usuário no sistema e envia email de confirmação.

        Args:
            nome: Nome completo do usuário
            email: Email do usuário (será normalizado)
            password: Senha em texto plano (será hasheada)
            email_service: Instância do serviço de email

        Returns:
            UserRegistrationResult: Resultado da operação com usuário e token
        """
        try:
            # Cria o usuário
            usuario = User()
            usuario.nome = nome
            usuario.email = email  # Será normalizado pelo setter
            usuario.ativo = False
            usuario.password = password  # Será hasheado pelo setter

            db.session.add(usuario)
            db.session.flush()
            db.session.refresh(usuario)

            # Gera token e envia email de confirmação
            token, email_sent = UserService._enviar_email_confirmacao(usuario, email_service)

            db.session.commit()
            current_app.logger.info("Usuário registrado: %s" % (usuario.email,))

            return UserRegistrationResult(
                status=UserOperationStatus.SUCCESS,
                user=usuario,
                token=token,
                email_sent=email_sent
            )

        except ValueError as e:
            db.session.rollback()
            current_app.logger.error("Erro de validação ao registrar usuário: %s" % (str(e),))
            return UserRegistrationResult(
                status=UserOperationStatus.UNKNOWN,
                error_message=str(e)
            )
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error("Erro de banco de dados ao registrar usuário: %s" % (str(e),))
            return UserRegistrationResult(
                status=UserOperationStatus.DATABASE_ERROR,
                error_message=str(e)
            )

    @staticmethod
    def reenviar_email_validacao(user_id: UUID, email_service) -> EmailValidationResult:
        """
        Reenvia o email de validação para um usuário inativo.

        Args:
            user_id: UUID do usuário
            email_service: Instância do serviço de email

        Returns:
            EmailValidationResult: Resultado da operação
        """
        try:
            uuid_obj = UUID(str(user_id))
        except (ValueError, TypeError):
            current_app.logger.warning("UUID inválido fornecido: %s" % (user_id,))
            return EmailValidationResult(
                status=UserOperationStatus.INVALID_UUID,
                error_message="ID de usuário inválido"
            )

        usuario = User.get_by_id(uuid_obj)
        if usuario is None:
            current_app.logger.warning("Tentativa de reenvio de email para usuário inexistente: %s" % (user_id,))
            return EmailValidationResult(
                status=UserOperationStatus.USER_NOT_FOUND,
                error_message="Usuário inexistente"
            )

        if usuario.ativo:
            current_app.logger.info("Usuário %s já está ativo" % (usuario.email,))
            return EmailValidationResult(
                status=UserOperationStatus.USER_ALREADY_ACTIVE,
                user=usuario,
                error_message="Usuário já está ativo"
            )

        # Gera token e envia email de confirmação
        token, email_sent = UserService._enviar_email_confirmacao(usuario, email_service)

        if not email_sent:
            return EmailValidationResult(
                status=UserOperationStatus.EMAIL_SEND_ERROR,
                user=usuario,
                token=token,
                email_sent=False,
                error_message="Erro no envio do email"
            )

        current_app.logger.info("Email de revalidação enviado para %s" % (usuario.email,))
        return EmailValidationResult(
            status=UserOperationStatus.SUCCESS,
            user=usuario,
            token=token,
            email_sent=True
        )

    @staticmethod
    def validar_email_por_token(token: str) -> EmailValidationResult:
        """
        Valida o email de um usuário através de um token JWT.

        Args:
            token: Token JWT de validação de email

        Returns:
            EmailValidationResult: Resultado da validação
        """
        claims = JWTService.verify(token)

        if not (claims.get('valid', False) and {'sub', 'action'}.issubset(claims)):
            current_app.logger.error("Token incorreto ou incompleto: %s" % (claims,))
            return EmailValidationResult(
                status=UserOperationStatus.INVALID_TOKEN,
                error_message="Token incorreto ou incompleto"
            )

        if claims.get('action') != JWT_action.VALIDAR_EMAIL:
            current_app.logger.error("Ação de token inválida: %s" % (claims.get('action'),))
            return EmailValidationResult(
                status=UserOperationStatus.INVALID_TOKEN,
                error_message="Token inválido"
            )

        usuario = User.get_by_email(claims.get('sub'))
        if usuario is None:
            current_app.logger.warning("Tentativa de validação de email para usuário inexistente")
            return EmailValidationResult(
                status=UserOperationStatus.USER_NOT_FOUND,
                error_message="Usuário não encontrado"
            )

        if usuario.ativo:
            current_app.logger.info("Usuário %s já estava ativo" % (usuario.email,))
            return EmailValidationResult(
                status=UserOperationStatus.USER_ALREADY_ACTIVE,
                user=usuario,
                error_message="Usuário já está ativo"
            )

        # Confirma o email
        UserService.confirmar_email(usuario)
        current_app.logger.info("Email validado com sucesso para %s" % (usuario.email,))

        return EmailValidationResult(
            status=UserOperationStatus.SUCCESS,
            user=usuario
        )

    @staticmethod
    def solicitar_reset_senha(email: str, email_service) -> PasswordResetResult:
        """
        Solicita reset de senha, gerando token e enviando email.

        Args:
            email: Email do usuário (será normalizado)
            email_service: Instância do serviço de email

        Returns:
            PasswordResetResult: Resultado da operação
        """
        try:
            email_normalizado = EmailValidationService.normalize(email)
        except ValueError:
            current_app.logger.warning("Email inválido fornecido: %s" % (email,))
            # Por segurança, retorna SUCCESS mesmo com email inválido
            return PasswordResetResult(status=UserOperationStatus.SUCCESS)

        usuario = User.get_by_email(email_normalizado)
        if usuario is None:
            current_app.logger.warning(
                "Pedido de reset de senha para usuário inexistente (%s)" % (email_normalizado,))
            # Por segurança, retorna SUCCESS mesmo se usuário não existir
            return PasswordResetResult(status=UserOperationStatus.SUCCESS)

        # Gera token e envia email
        token = JWTService.create(JWT_action.RESET_PASSWORD, sub=usuario.email)
        body = render_template('auth/email/email_new_password.jinja2',
                             nome=usuario.nome,
                             url=url_for('auth.reset_password', token=token, _external=True))
        result = email_service.send_email(to=usuario.email,
                                         subject="Altere a sua senha",
                                         text_body=body)

        if not result.success:
            current_app.logger.error("Erro ao enviar email de reset para %s" % (usuario.email,))
            return PasswordResetResult(
                status=UserOperationStatus.EMAIL_SEND_ERROR,
                user=usuario,
                error_message="Erro no envio do email"
            )

        current_app.logger.info("Email de reset de senha enviado para %s" % (usuario.email,))
        return PasswordResetResult(
            status=UserOperationStatus.SUCCESS,
            user=usuario
        )

    @staticmethod
    def redefinir_senha_por_token(token: str, nova_senha: str) -> PasswordResetResult:
        """
        Redefine a senha de um usuário através de um token JWT.

        Args:
            token: Token JWT de reset de senha
            nova_senha: Nova senha em texto plano

        Returns:
            PasswordResetResult: Resultado da operação
        """
        claims = JWTService.verify(token)

        if not (claims.get('valid', False) and {'sub', 'action'}.issubset(claims)):
            current_app.logger.warning("Token incorreto ou incompleto")
            return PasswordResetResult(
                status=UserOperationStatus.INVALID_TOKEN,
                error_message="Token incorreto ou incompleto"
            )

        if claims.get('action') != JWT_action.RESET_PASSWORD:
            current_app.logger.warning("Ação de token inválida: %s" % (claims.get('action'),))
            return PasswordResetResult(
                status=UserOperationStatus.INVALID_TOKEN,
                error_message="Token inválido"
            )

        usuario = User.get_by_email(claims.get('sub'))
        if usuario is None:
            current_app.logger.warning("Tentativa de reset de senha para usuário inexistente")
            return PasswordResetResult(
                status=UserOperationStatus.USER_NOT_FOUND,
                error_message="Usuário não encontrado"
            )

        try:
            usuario.password = nova_senha  # Será hasheado pelo setter
            db.session.commit()
            current_app.logger.info("Senha redefinida com sucesso para %s" % (usuario.email,))

            return PasswordResetResult(
                status=UserOperationStatus.SUCCESS,
                user=usuario
            )

        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error("Erro ao redefinir senha: %s" % (str(e),))
            return PasswordResetResult(
                status=UserOperationStatus.DATABASE_ERROR,
                error_message=str(e)
            )
