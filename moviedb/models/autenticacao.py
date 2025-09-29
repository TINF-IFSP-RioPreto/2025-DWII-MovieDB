import uuid
from base64 import b64decode
from datetime import datetime
from typing import Optional

from flask import current_app
from flask_login import UserMixin
from sqlalchemy import DateTime, ForeignKey, select, String, Text, Uuid
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from moviedb import db
from moviedb.services.email_service import EmailValidationService
from moviedb.services.image_processing_service import ImageProcessingError, ImageProcessingService
from .custom_types import EncryptedType
from .mixins import AuditMixin, BasicRepositoryMixin


class User(db.Model, BasicRepositoryMixin, UserMixin, AuditMixin):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(60))
    email_normalizado: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))

    ativo: Mapped[bool] = mapped_column(default=False, server_default='false')
    dta_validacao_email: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                    default=None)

    com_foto: Mapped[bool] = mapped_column(default=False, server_default='false')
    foto_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    avatar_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    foto_mime: Mapped[Optional[str]] = mapped_column(String(32), default=None)

    usa_2fa: Mapped[bool] = mapped_column(default=False, server_default='false')
    _otp_secret: Mapped[Optional[str]] = mapped_column(
            EncryptedType(length=500,
                          encryption_key="DATABASE_ENCRYPTION_KEY",
                          salt_key="DATABASE_ENCRYPTION_SALT"), default=None)
    ultimo_otp: Mapped[Optional[str]] = mapped_column(String(6), default=None)

    ultimo_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                             default=None)

    @property
    def email(self):
        """Retorna o e-mail normalizado do usuário."""
        return self.email_normalizado

    @email.setter
    def email(self, value):
        """Define e normaliza o e-mail do usuário."""
        try:
            normalizado = EmailValidationService.normalize(value)
        except ValueError:
            raise ValueError(f"E-mail inválido: {value}")
        self.email_normalizado = normalizado

    @property
    def is_active(self):
        """Indica se o usuário está ativo."""
        return self.ativo

    def get_id(self):  # https://flask-login.readthedocs.io/en/latest/#alternative-tokens
        return f"{str(self.id)}|{self.password[-15:]}"

    @property
    def password(self):
        """Retorna o hash da senha do usuário."""
        return self.password_hash

    @password.setter
    def password(self, value):
        """Armazena o has da senha do usuário."""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(value)

    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """
        Retorna o usuário com o e-mail especificado, ou None se não encontrado

        Args:
            email (str): email previamente normalizado que será buscado

        Returns:
            O usuário encontrado, ou None
        """
        return db.session.scalar(select(cls).where(User.email_normalizado.is_(email)))

    def check_password(self, password) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(str(self.password_hash), password)

    @property
    def foto(self) -> tuple[bytes | None, str | None]:
        """Retorna a foto original do usuário em bytes e o tipo MIME."""
        if self.com_foto:
            data = b64decode(str(self.foto_base64))
            mime_type = self.foto_mime
        else:
            data = None
            mime_type = None
        return data, mime_type

    @property
    def avatar(self) -> tuple[bytes | None, str | None]:
        """Retorna o avatar do usuário em bytes e o tipo MIME."""
        if self.com_foto:
            data = b64decode(str(self.avatar_base64))
            mime_type = self.foto_mime
        else:
            data = None
            mime_type = None
        return data, mime_type

    @foto.setter
    def foto(self, value):
        """
        Setter para a foto/avatar do usuário.

        Atualiza os campos relacionados à foto do usuário. Se o valor for None,
        remove a foto e limpa os campos associados. Caso contrário, tenta armazenar
        a foto em base64 e o tipo MIME. Lida com o caso em que value não possui os
        métodos/atributos esperados, registrando o erro.

        Args:
            value: um objeto com métodos `read()` e atributo `mimetype`, ou None.
        """

        try:
            if value is None:
                self.com_foto = False
                self.foto_base64 = None
                self.avatar_base64 = None
                self.foto_mime = None
            else:
                resultado = ImageProcessingService.processar_upload_foto(value)
                self.foto_base64 = resultado.foto_base64
                self.avatar_base64 = resultado.avatar_base64
                self.foto_mime = resultado.mime_type
                self.com_foto = True

                db.session.commit()

                current_app.logger.info(
                        "Foto processada para usuário %s: %s %s -> %s (avatar)" % (
                            self.email,
                            resultado['formato_original'],
                            resultado['dimensoes_originais'],
                            resultado['dimensoes_avatar']
                        )
                )

        except (ImageProcessingError, ValueError) as e:
            db.session.rollback()
            current_app.logger.error(
                "Erro ao processar foto do usuário %s: %s" % (self.email, str(e)))
            raise e
        except SQLAlchemyError as e:
            db.session.rollback()
            raise SQLAlchemyError(
                "Erro de banco de dados ao processar foto do usuário: %s" % (str(e))) from e

    @property
    def otp_secret(self):
        return self._otp_secret

    @otp_secret.setter
    def otp_secret(self, value: Optional[str] = None):
        self._otp_secret = value


class Backup2FA(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'backup2fa'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hash_codigo: Mapped[str] = mapped_column(String(256))
    usuario_id: Mapped[uuid.UUID] = mapped_column(
            Uuid(as_uuid=True),
            ForeignKey('usuarios.id', ondelete='CASCADE'),  # Explicit CASCADE
            index=True
    )
    utilizado: Mapped[bool] = mapped_column(default=False, server_default='false')
    dta_uso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dta_para_remocao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                 nullable=True)

    # Relação ORM para acessar o usuário associado a este código de backup 2FA.
    usuario: Mapped['User'] = relationship('User', foreign_keys=[usuario_id])
