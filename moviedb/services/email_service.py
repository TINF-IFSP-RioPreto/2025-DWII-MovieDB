from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from flask import current_app


@dataclass
class EmailMessage:
    to: str
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    cc: Optional[list[str]] = None
    bcc: Optional[list[str]] = None

    def __post_init__(self):
        if not self.text_body and not self.html_body:
            raise ValueError("Email tem que ter text_body ou html_body.")


class EmailValidationService:
    """Serviço responsável pela validação de um endereco de email."""

    @staticmethod
    def is_valid(email: str) -> bool:
        """
        Valida o formato do endereço de email.

        Args:
            email (str): Endereço de email a ser validado.

        Returns:
            bool: True se o formato do email for válido, False caso contrário.
        """
        from email_validator import validate_email
        from email_validator.exceptions import EmailNotValidError, EmailSyntaxError
        try:
            validado = validate_email(email, check_deliverability=False)
            return validado is not None
        except (EmailNotValidError, EmailSyntaxError, TypeError):
            return False

    @staticmethod
    def normalize(email: str) -> str:
        """
        Normaliza o endereço de email.

        Args:
            email (str): Endereço de email a ser normalizado.

        Returns:
            str: Endereço de email normalizado.

        Raises:
            ValueError: Se o email for inválido.
        """
        from email_validator import validate_email
        from email_validator.exceptions import EmailNotValidError, EmailSyntaxError
        try:
            validado = validate_email(email, check_deliverability=False)
            return validado.normalized.lower()
        except (EmailNotValidError, EmailSyntaxError, TypeError) as e:
            raise ValueError("Endereço de email inválido.") from e


class EmailProviderError(Exception):
    """Exceção base para erros de provedores de email."""
    pass


class EmailProvider(ABC):
    """Interface abstrata para provedores de email."""

    @abstractmethod
    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Envia um email usando o provedor.

        Args:
            message: Mensagem a ser enviada

        Returns:
            dict: Resultado do envio com informações do provedor

        Raises:
            EmailProviderError: Em caso de erro no envio
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna o nome do provedor."""
        pass


class PostmarkProvider(EmailProvider):
    """Provedor de email usando o Postmark."""

    def __init__(self, api_key: str):
        """
        Inicializa o provedor Postmark.

        Args:
            api_key (str): Chave da API do Postmark.
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("A chave da API do Postmark é obrigatória e deve ser uma string.")
        self._api_key = api_key

    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Envia um email usando o Postmark.

        Args:
            message: Mensagem a ser enviada

        Returns:
            dict: Resultado do envio com informações do Postmark

        Raises:
            EmailProviderError: Em caso de erro no envio
        """
        try:
            from postmarker.core import PostmarkClient

            client = PostmarkClient(server_token=self._api_key)

            # Monta o email para Postmark
            email_data = {
                'From'      : message.from_email,
                'To'        : message.to,
                'Subject'   : message.subject,
            }

            # Adiciona corpo do email
            if message.text_body:
                email_data['TextBody'] = message.text_body
            if message.html_body:
                email_data['HtmlBody'] = message.html_body

            # Campos opcionais
            if message.reply_to:
                email_data['ReplyTo'] = message.reply_to
            if message.cc:
                email_data['Cc'] = ', '.join(message.cc)
            if message.bcc:
                email_data['Bcc'] = ', '.join(message.bcc)

            email_obj = client.emails.Email(**email_data)
            response = email_obj.send()

            if response.get('ErrorCode', 0) != 0:
                raise EmailProviderError(
                    f"Erro Postmark: {response.get('Message', 'Erro desconhecido')}")

            return {
                'success'     : True,
                'provider'    : 'postmark',
                'message_id'  : response.get('MessageID'),
                'submitted_at': response.get('SubmittedAt'),
                'to'          : response.get('To'),
                'error_code'  : response.get('ErrorCode', 0),
                'raw_response': response
            }

        except ImportError:
            raise EmailProviderError("Biblioteca postmarker não instalada")
        except Exception as e:
            raise EmailProviderError(f"Erro ao enviar via Postmark: {str(e)}") from e

    def get_provider_name(self) -> str:
        return "Postmark"


class SMTPProvider(EmailProvider):
    """Provedor de email usando SMTP padrão."""

    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str,
                 use_tls: bool = True):
        self._smtp_server = smtp_server
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._use_tls = use_tls

    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """Envia email via SMTP."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders
            import uuid

            # Cria a mensagem
            if message.html_body and message.text_body:
                msg = MIMEMultipart('alternative')
            else:
                msg = MIMEMultipart()

            msg['From'] = message.from_email
            msg['To'] = message.to
            msg['Subject'] = message.subject

            if message.reply_to:
                msg['Reply-To'] = message.reply_to
            if message.cc:
                msg['Cc'] = ', '.join(message.cc)

            # Adiciona corpos
            if message.text_body:
                msg.attach(MIMEText(message.text_body, 'plain', 'utf-8'))
            if message.html_body:
                msg.attach(MIMEText(message.html_body, 'html', 'utf-8'))


            # Conecta ao servidor SMTP
            server = smtplib.SMTP(self._smtp_server, self._smtp_port)

            if self._use_tls:
                server.starttls()

            server.login(self._username, self._password)

            # Lista de destinatários
            recipients = [message.to]
            if message.cc:
                recipients.extend(message.cc)
            if message.bcc:
                recipients.extend(message.bcc)

            # Envia
            result = server.send_message(msg, to_addrs=recipients)
            server.quit()

            message_id = str(uuid.uuid4())

            return {
                'success'     : True,
                'provider'    : 'smtp',
                'message_id'  : message_id,
                'to'          : message.to,
                'refused'     : result,  # Lista de emails rejeitados
                'raw_response': result
            }

        except Exception as e:
            raise EmailProviderError(f"Erro ao enviar via SMTP: {str(e)}") from e

    def get_provider_name(self) -> str:
        return f"SMTP ({self._smtp_server})"


class MockProvider(EmailProvider):
    """Provedor mock para desenvolvimento/testes."""

    def __init__(self, log_emails: bool = True):
        self.log_emails = log_emails
        self.sent_emails = []  # Para testes

    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """Simula envio de email."""
        import uuid
        from datetime import datetime

        message_id = str(uuid.uuid4())

        email_info = {
            'message_id': message_id,
            'from'      : message.from_email,
            'to'        : message.to,
            'subject'   : message.subject,
            'text_body' : message.text_body,
            'html_body' : message.html_body,
            'sent_at'   : datetime.now().isoformat(),
        }

        self.sent_emails.append(email_info)

        if self.log_emails:
            current_app.logger.debug("=== EMAIL SIMULADO ===")
            current_app.logger.debug(f"From: {message.from_email}")
            current_app.logger.debug(f"To: {message.to}")
            current_app.logger.debug(f"Subject: {message.subject}")
            current_app.logger.debug("--- Text Body ---")
            current_app.logger.debug(message.text_body or "(vazio)")
            if message.html_body:
                current_app.logger.debug("--- HTML Body ---")
                current_app.logger.debug(message.html_body)
            current_app.logger.debug("===================")

        return {
            'success'   : True,
            'provider'  : 'mock',
            'message_id': message_id,
            'to'        : message.to,
            'sent_at'   : email_info['sent_at']
        }

    def get_provider_name(self) -> str:
        return "Mock (Development)"

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Retorna lista de emails enviados (para testes)."""
        return self.sent_emails.copy()

    def clear_sent_emails(self):
        """Limpa lista de emails enviados."""
        self.sent_emails.clear()


class EmailService:
    """Serviço principal para envio de emails."""

    def __init__(self,
                 provider: EmailProvider,
                 default_from_email: str,
                 default_from_name: str = None):
        self.provider = provider
        self.default_from_email = default_from_email
        self.default_from_name = default_from_name

    @classmethod
    def create_from_config(cls, app_config: Dict[str, Any]) -> 'EmailService':
        """
        Cria instância do EmailService a partir da configuração da aplicação.

        Args:
            app_config: Dicionário de configuração da app

        Returns:
            EmailService: Instância configurada
        """
        send_email = app_config.get('SEND_EMAIL', False)

        if not send_email:
            # Modo desenvolvimento/teste
            provider = MockProvider(log_emails=True)
        else:
            # Configuração de produção
            email_provider = app_config.get('EMAIL_PROVIDER', 'postmark').lower()

            if email_provider == 'postmark':
                server_token = app_config.get('POSTMARK_SERVER_TOKEN')
                if not server_token:
                    raise ValueError(
                        "POSTMARK_SERVER_TOKEN é obrigatório quando EMAIL_PROVIDER=postmark")
                provider = PostmarkProvider(server_token)

            elif email_provider == 'smtp':
                smtp_config = {
                    'smtp_server': app_config.get('SMTP_SERVER'),
                    'smtp_port'  : app_config.get('SMTP_PORT', 587),
                    'username'   : app_config.get('SMTP_USERNAME'),
                    'password'   : app_config.get('SMTP_PASSWORD'),
                    'use_tls'    : app_config.get('SMTP_USE_TLS', True)
                }

                required_fields = ['smtp_server', 'username', 'password']
                missing_fields = [field for field in required_fields if not smtp_config.get(field)]

                if missing_fields:
                    raise ValueError(f"Campos obrigatórios para SMTP: {', '.join(missing_fields)}")

                provider = SMTPProvider(**smtp_config)
            else:
                raise ValueError(f"Provedor de email não suportado: {email_provider}")

        default_from_email = app_config.get('EMAIL_SENDER')
        default_from_name = app_config.get('EMAIL_SENDER_NAME', app_config.get('APP_NAME'))

        if not default_from_email:
            raise ValueError("EMAIL_SENDER é obrigatório")

        return cls(provider, default_from_email, default_from_name)

    def send_email(self,
                   to: str,
                   subject: str,
                   text_body: Optional[str] = None,
                   html_body: Optional[str] = None,
                   from_email: Optional[str] = None,
                   from_name: Optional[str] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Envia um email.

        Args:
            to: Email do destinatário
            subject: Assunto do email
            text_body: Corpo em texto plano
            html_body: Corpo em HTML
            from_email: Email do remetente (usa padrão se não fornecido)
            from_name: Nome do remetente
            **kwargs: Argumentos adicionais para EmailMessage

        Returns:
            dict: Resultado do envio

        Raises:
            EmailProviderError: Em caso de erro no envio
            ValueError: Para dados inválidos
        """
        try:
            # Usa valores padrão se não fornecidos
            from_email = from_email or self.default_from_email
            from_name = from_name or self.default_from_name

            # Formata o From com nome se fornecido
            if from_name:
                from_email = f"{from_name} <{from_email}>"

            message = EmailMessage(
                    to=to,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                    from_email=from_email,
                    from_name=from_name,
                    **kwargs
            )

            result = self.provider.send(message)

            current_app.logger.info(f"Email enviado via {self.provider.get_provider_name()}: "
                                    f"{to} - {subject} (ID: {result.get('message_id', 'N/A')})")

            return result

        except Exception as e:
            current_app.logger.error(f"Erro ao enviar email para {to}: {str(e)}")
            raise

    def get_provider_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o provedor atual."""

        return {
            'provider_name'    : self.provider.get_provider_name(),
            'default_from'     : self.default_from_email,
            'default_from_name': self.default_from_name
        }
