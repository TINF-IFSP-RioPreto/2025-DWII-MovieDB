import io
import secrets
import uuid
from base64 import b64decode, b64encode
from datetime import datetime
from io import BytesIO
from typing import Optional

import pyotp
from flask import current_app
from flask_login import UserMixin
from PIL import Image
from qrcode.main import QRCode
from sqlalchemy import DateTime, ForeignKey, select, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from moviedb import db
from .custom_types import EncryptedType
from .enumeracoes import Autenticacao2FA
from .mixins import BasicRepositoryMixin, AuditMixin


def normalizar_email(email: str) -> Optional[str]:
    """
    Normaliza um endereço de e-mail utilizando a biblioteca email_validator.

    Args:
        email (str): Endereço de e-mail a ser normalizado.

    Returns:
        str: E-mail normalizado em letras minúsculas, ou None se o email for inválido.
    """
    from email_validator import validate_email
    from email_validator.exceptions import EmailNotValidError, EmailSyntaxError
    try:
        return validate_email(email, check_deliverability=False).normalized.lower()
    except (EmailNotValidError, EmailSyntaxError, TypeError):
        return None
    except Exception as e:
        current_app.logger.error("Erro inesperado ao validar email '%s': %s" % (email, str(e),))
        return None


class User(db.Model, BasicRepositoryMixin, UserMixin, AuditMixin):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(60))
    email_normalizado: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    ativo: Mapped[bool] = mapped_column(default=False, server_default='false')

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

    # Relação ORM que representa os códigos de backup 2FA associados ao usuário.
    # - `back_populates='usuario'`: sincroniza a relação bidirecional com Backup2FA.
    # - `lazy='select'`: carrega os códigos de backup ao buscar o usuário.
    # - `cascade='all, delete-orphan'`: remove os códigos de backup ao excluir o usuário.
    # - `passive_deletes=True`: permite que o banco de dados gerencie a exclusão em cascata.
    lista_2fa_backup: Mapped[list['Backup2FA']] = relationship(back_populates='usuario',
                                                               lazy='select',
                                                               cascade='all, delete-orphan',
                                                               passive_deletes=True)

    @property
    def email(self):
        """Retorna o e-mail normalizado do usuário."""
        return self.email_normalizado

    @email.setter
    def email(self, value):
        """Define e normaliza o e-mail do usuário."""
        normalizado = normalizar_email(value)
        if normalizado is None:
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
        return check_password_hash(self.password_hash, password)

    @property
    def foto(self) -> (bytes, str):
        """Retorna a foto original do usuário em bytes e o tipo MIME."""
        if self.com_foto:
            data = b64decode(self.foto_base64)
            mime_type = self.foto_mime
        else:
            data = None
            mime_type = None
        return data, mime_type

    @property
    def avatar(self) -> (bytes, str):
        """Retorna o avatar do usuário em bytes e o tipo MIME."""
        if self.com_foto:
            data = b64decode(self.avatar_base64)
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
        if value is None:
            self._clear_photo_data()
            return

        try:
            foto_data = value.read()
            if not foto_data:
                raise ValueError("Arquivo de imagem vazio")

            # Valida e processa a imagem
            with Image.open(io.BytesIO(foto_data)) as imagem:
                # Validações básicas
                if not hasattr(imagem, 'format') or imagem.format is None:
                    raise ValueError("Formato de imagem não reconhecido")

                # Armazena dados da imagem original (sem conversão)
                self.foto_base64 = b64encode(foto_data).decode('utf-8')
                self.foto_mime = value.mimetype
                self.com_foto = True

                # Gera avatar redimensionado no formato original
                self._generate_avatar(imagem)

        except (AttributeError, OSError, ValueError) as e:
            self._clear_photo_data()
            error_msg = f"Erro ao processar foto do usuário: {str(e)}"
            current_app.logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _clear_photo_data(self):
        """Limpa todos os dados relacionados à foto."""
        self.com_foto = False
        self.foto_base64 = None
        self.avatar_base64 = None

    def _generate_avatar(self, imagem):
        """
        Gera o avatar redimensionado a partir da imagem fornecida, preservando o formato original.

        Args:
            imagem: objeto PIL Image já aberto e validado.
        """
        size = current_app.config.get('AVATAR_SIZE', 32)
        largura, altura = imagem.size
        formato_original = imagem.format

        # Otimização: pula redimensionamento se já está no tamanho adequado
        if max(largura, altura) <= size:
            buffer_avatar = io.BytesIO()
            imagem.save(buffer_avatar, format=formato_original, optimize=True)
        else:
            # Calcula novo tamanho mantendo proporção
            fator_escala = min(size / largura, size / altura)
            novo_tamanho = (
                int(largura * fator_escala),
                int(altura * fator_escala)
            )

            # Redimensiona usando o metodo thumbnail (modifica in-place)
            imagem.thumbnail(novo_tamanho, Image.Resampling.LANCZOS)

            buffer_avatar = io.BytesIO()
            imagem.save(buffer_avatar, format=formato_original, optimize=True)

        self.avatar_base64 = b64encode(buffer_avatar.getvalue()).decode('utf-8')

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
        if current_app.config.get('SEND_EMAIL', False):
            from postmarker.core import PostmarkClient
            postmark = PostmarkClient(server_token=current_app.config['SERVER_TOKEN'])
            conteudo = postmark.emails.Email(
                    From=current_app.config['EMAIL_SENDER'],
                    To=self.email,
                    Subject=subject,
                    TextBody=body
            )
            response = conteudo.send()
            current_app.logger.debug("Email enviado para %s" % (self.email,))
            current_app.logger.debug("Resposta do Postmark: %s" % (response,))
            if response['ErrorCode'] != 0:
                current_app.logger.error("Erro ao enviar email para %s: %s" %
                                         (self.email, response['Message'],))
                return False
        else:
            current_app.logger.debug("Mensagem que SERIA enviada")
            current_app.logger.debug("From: %s" % (current_app.config['EMAIL_SENDER'],))
            current_app.logger.debug("To: %s" % (self.email,))
            current_app.logger.debug("Subject: %s" % (subject,))
            current_app.logger.debug("", )
            current_app.logger.debug("%s" % (body,))
        return True

    @property
    def otp_secret_formatted(self) -> str:
        """
        Retorna o segredo OTP do usuário em grupos de 4 caracteres

        Returns:
            str: segredo OTP formatado (XXXX ... XXXX)
        """
        return " ".join(self.otp_secret[i:i + 4] for i in range(0, len(self.otp_secret), 4))

    @property
    def b64encoded_qr_totp_uri(self) -> str:
        """
        Retorna imagem em base64 com o qr_code para a string de configuração do aplicativo de 2FA

        Returns
            str: representação da imagem do qr-code
        """
        qr = QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.totp_uri, optimize=0)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer)
        return b64encode(buffer.getvalue()).decode('UTF-8')

    @property
    def totp_uri(self) -> str:
        """
        Retorna a string de configuração do aplicativo de 2FA

        Returns:
            str: string de configuração do aplicativo de 2FA no formato
            otpauth://TYPE/LABEL?PARAMETERS
        """
        otp = pyotp.totp.TOTP(self.otp_secret)
        return otp.provisioning_uri(name=self.email,
                                    issuer_name=current_app.config.get('APP_NAME'))

    @property
    def otp_secret(self):
        return self._otp_secret

    @otp_secret.setter
    def otp_secret(self, value: Optional[str] = None):
        if value is None:
            value = pyotp.random_base32()
        self._otp_secret = value

    def verify_totp(self, token) -> bool:
        """
        DESCONTINUADO: Este metodo será removido em versões futuras.

        Use verify_2fa_code() no lugar.
        """
        import warnings
        warnings.warn("verify_totp está descontinuado e será removido em versões futuras. "
                      "Use verify_2fa_code() para verificação unificada de códigos 2FA",
                      DeprecationWarning, stacklevel=2)
        return self._verify_totp(token)

    def _verify_totp(self, token: str) -> bool:
        """Metodo interno para verificar o código TOTP."""
        totp = pyotp.TOTP(self.otp_secret)
        return totp.verify(token, valid_window=1)

    def verify_totp_backup(self, token) -> bool:
        """
        DESCONTINUADO: Este metodo será removido em versões futuras.

        Use verify_2fa_code() no lugar.
        """
        import warnings
        warnings.warn("verify_totp_backup está descontinuado e será removido em versões futuras. "
                      "Use verify_2fa_code() para verificação unificada de códigos 2FA",
                      DeprecationWarning, stacklevel=2)
        return self._verify_totp(token)

    def _verify_totp_backup(self, token) -> bool:
        """Metodo interno para verificar o código de backup 2FA."""
        from werkzeug.security import check_password_hash
        for codigo in self.lista_2fa_backup:
            if check_password_hash(codigo.hash_codigo, token):
                db.session.delete(codigo)
                db.session.commit()
                return True
        return False

    def verify_2fa_code(self, token, totp_only: bool = False) -> tuple[bool, Autenticacao2FA]:
        """
        Verifica código 2FA e retorna resultado com tipo de autenticação usado.

        Se for usado um código reserva, ele é removido da lista de códigos válidos.

        Args:
            token (str): Código 2FA a ser verificado.
            totp_only (bool): Se True, não tenta verificar códigos reserva. Padrão: False.

        Returns:
            tuple[bool, Autenticacao2FA]: (success, auth_method) onde auth_method é o tipo de 2FA
            usado.
        """
        # Verifica se o código é o mesmo usado por último (não é válido)
        if token == self.ultimo_otp:
            return False, Autenticacao2FA.REUSED

        # Tenta TOTP primeiro
        if self._verify_totp(token):
            return True, Autenticacao2FA.TOTP

        # Se totp_only=True, não verifica códigos reserva (usado durante ativação)
        if totp_only:
            return False, Autenticacao2FA.WRONG

        # Tenta códigos de backup
        if self.usa_2fa and self._verify_totp_backup(token):
            return True, Autenticacao2FA.BACKUP

        return False, Autenticacao2FA.WRONG

    def generate_2fa_backup(self, quantos: int = 5) -> list[str]:
        """
        Gera códigos de backup para autenticação 2FA do usuário.

        Remove todos os códigos de backup anteriores e cria novos códigos aleatórios,
        armazenando-os de forma segura no banco de dados.

        Args:
            quantos (int): Quantidade de códigos de backup a serem gerados. Padrão: 5.

        Returns:
            list[str]: lista dos códigos de backup gerados.
        """
        from werkzeug.security import generate_password_hash
        # Remove os códigos anteriores
        for codigo in self.lista_2fa_backup:
            db.session.delete(codigo)
        # Gera novos códigos
        codigos = []
        for _ in range(quantos):
            codigo = "".join(
                    secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789') for _
                    in range(6))
            codigos.append(codigo)
            backup2fa = Backup2FA()
            backup2fa.hash_codigo = generate_password_hash(codigo)
            self.lista_2fa_backup.append(backup2fa)
        db.session.commit()
        return codigos

    def enable_2fa(self, otp_secret: str = None,
                   ultimo_otp: str = "",
                   generate_backup: bool = False,
                   back_codes: int = 0) -> Optional[list[str]]:
        """
        Ativa o 2FA para o usuário, configurando o segredo OTP, o último OTP e, opcionalmente,
        gerando códigos de backup.

        Args:
            otp_secret (str): segredo OTP para ativação do 2FA. Obrigatório.
            ultimo_otp (str): último código OTP utilizado.
            generate_backup (bool): se True, gera códigos de backup.
            back_codes (int): quantidade de códigos de backup a serem gerados.

        Returns:
            Optional[list[str]]: lista de códigos de backup gerados, se solicitado.

        Raises
            ValueError: Se o otp_secret não for fornecido.
        """
        if otp_secret is None:
            raise ValueError("Obrigatório informar o OTP Secret para ativar o 2FA")
        self.otp_secret = otp_secret
        self.usa_2fa = True
        self.ultimo_otp = ultimo_otp if ultimo_otp is not None else pyotp.TOTP(otp_secret).now()
        if generate_backup and back_codes > 0:
            return self.generate_2fa_backup(back_codes)
        else:
            db.session.commit()
            return None

    def disable_2fa(self) -> bool:
        """
        Desativa o 2FA para o usuário

        Remove o segredo OTP, o último OTP e todos os códigos de backup.
        Realiza a exclusão dos códigos de backup associados ao usuário e atualiza o banco de dados.

        Returns:
            bool: True se a operação foi concluída com sucesso.
        """
        self.usa_2fa = False
        self._otp_secret = None
        self.ultimo_otp = None
        for codigo in self.lista_2fa_backup:
            db.session.delete(codigo)
        db.session.commit()
        return True


class Backup2FA(db.Model, AuditMixin):
    __tablename__ = 'backup2fa'

    # TODO: implementar mecanimso de marcação dos códigos de backup que foram usados ao invés
    #   de exclusão, para manter histórico. Quando usado, acrescentar informações sobre o uso
    #   e a data para remoção física (ex: após 30 dias) e implementar uma tarefa em Celery para
    #   remoção periódica.

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hash_codigo: Mapped[str] = mapped_column(String(256))
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey('usuarios.id'),
                                                  index=True)

    # Relação ORM para acessar o usuário associado a este código de backup 2FA.
    # `back_populates` garante sincronização bidirecional com User.lista_2fa_backup.
    usuario: Mapped['User'] = relationship(back_populates='lista_2fa_backup')
