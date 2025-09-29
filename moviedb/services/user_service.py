from datetime import datetime

from flask import current_app
from flask_login import login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from moviedb import db
from moviedb.models.autenticacao import User


class UserService:
    """Serviço responsável por operações de negócio relacionadas aos usuários."""

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
            if not usuario.ativo:
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
