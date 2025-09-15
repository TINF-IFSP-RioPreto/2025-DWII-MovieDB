import uuid

from flask import current_app
from flask_login import UserMixin
from sqlalchemy import Boolean, Column, select, String, Uuid

from moviedb import db
from moviedb.models.mixins import BasicRepositoryMixin


def normalizar_email(email: str) -> str:
    """
    Normaliza um endereço de e-mail utilizando a biblioteca email_validator.

    Args:
        email (str): Endereço de e-mail a ser normalizado.

    Returns:
        str: E-mail normalizado em letras minúsculas.

    Raises:
        EmailNotValidError: Se o e-mail fornecido não for válido.
    """
    from email_validator import validate_email
    from email_validator.exceptions import EmailNotValidError
    try:
        return validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise


class User(db.Model, BasicRepositoryMixin, UserMixin):
    __tablename__ = "usuarios"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(60), nullable=False)
    email_normalizado = Column(String(180), nullable=False, unique=True, index=True)
    password_hash = Column(String(256), nullable=False)
    ativo = Column(Boolean, nullable=False, default=False)

    @property
    def email(self):
        return self.email_normalizado

    @email.setter
    def email(self, value):
        self.email_normalizado = normalizar_email(value)

    @property
    def is_active(self):
        return self.ativo

    def get_id(self):  # https://flask-login.readthedocs.io/en/latest/#alternative-tokens
        return f"{str(self.id)}|{self.password[-15:]}"

    @property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, value):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(value)

    @classmethod
    def get_by_email(cls, email: str):
        return db.session.execute(
                select(cls).
                where(User.email_normalizado == normalizar_email(email))
        ).scalar_one_or_none()

    def check_password(self, password) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def send_email(self, subject: str,
                   body: str) -> bool:
        """
        Envia um e-mail para o usuário utilizando o serviço Postmark.

        Args:
            subject (str): Assunto do e-mail.
            body (str): Corpo do e-mail em texto simples.

        Returns:
            True se conseguir enviar o e-mail, False caso contrário.
        """
        from postmarker.core import PostmarkClient
        postmark = PostmarkClient(server_token=current_app.config['SERVER_TOKEN'])
        conteudo = postmark.emails.Email(
                From=current_app.config['EMAIL_SENDER'],
                To=self.email,
                Subject=subject,
                TextBody=body
        )
        response = conteudo.send()
        current_app.logger.debug("Email enviado para %s", self.email)
        current_app.logger.debug("Resposta do Postmark: %s", response)
        if response['ErrorCode'] != 0:
            current_app.logger.error("Erro ao enviar email para %s: %s",
                                     self.email, response['Message'])
            return False
        return True
