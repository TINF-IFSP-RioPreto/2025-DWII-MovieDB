import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class QRCodeConfig:
    """Configuração para geração de QR Codes."""
    box_size: int = 10
    border: int = 4
    fill_color: str = "black"
    back_color: str = "white"

    def __post_init__(self):
        if self.box_size < 1:
            raise ValueError("box_size deve ser maior que 1")
        if self.border < 0:
            raise ValueError("border não pode ser negativo")


class QRCodeGenerator(ABC):
    """Interface para geração de QR Codes."""
    @abstractmethod
    def generate(self, data: str, config: QRCodeConfig) -> bytes:
        """Gera um QR Code a partir dos dados fornecidos.

        Args:
            data (str): Dados a serem codificados no QR Code.
            config (QRCodeConfig): Configuração para geração do QR Code.

        Returns:
            bytes: Imagem do QR Code em formato PNG.

        Raises:
            QRCodeError: Em caso de falha na geração do QR Code.
        """
        pass

    @abstractmethod
    def get_generator_name(self) -> str:
        """Retorna o nome do gerador de QR Code.

        Returns:
            str: Nome do gerador.
        """
        pass


class QRCodePILGenerator(QRCodeGenerator):
    """Implementação do gerador de QR Codes usando a biblioteca qrcode e PIL."""
    def generate(self, data: str, config: QRCodeConfig) -> bytes:
        from qrcode.main import QRCode
        from qrcode.image.pil import PilImage
        from io import BytesIO

        qr = QRCode(version=None,
                    box_size=config.box_size,
                    border=config.border,
                    image_factory=PilImage)
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=config.fill_color, back_color=config.back_color)

        buffer = BytesIO()
        img.save(buffer)
        return buffer.getvalue()

    def get_generator_name(self) -> str:
        return "QRCodePILGenerator"


class QRCodeService:
    """Serviço para geração de QR Codes."""

    def __init__(self, generator: QRCodeGenerator):
        self.generator = generator

    @classmethod
    def create_default(cls) -> 'QRCodeService':
        """Cria uma instância do serviço com o gerador padrão.

        Returns:
            QRCodeService: Instância do serviço com QRCodePILGenerator.
        """
        return cls(generator=QRCodePILGenerator())

    def generate_qr_code(self,
                         data: str,
                         config: Optional[QRCodeConfig] = None) -> bytes:
        """Gera um QR Code a partir dos dados fornecidos.

        Args:
            data (str): Dados a serem codificados no QR Code.
            config (typing.Optional[QRCodeConfig]): Configuração para geração do QR Code.
                Se None, usa configuração padrão.

        Returns:
            bytes: Imagem do QR Code em formato PNG.

        Raises:
            ValueError: Em caso de falha na geração do QR Code.
        """
        if not data:
            raise ValueError("Os dados para o QR Code não podem ser vazios.")
        config = config or QRCodeConfig()

        return self.generator.generate(data, config)

    def generate_qr_code_base64(self,
                                data: str,
                                config: Optional[QRCodeConfig] = None) -> str:
        """Gera um QR Code a partir dos dados fornecidos em base64.

        Args:
            data (str): Dados a serem codificados no QR Code.
            config (typing.Optional[QRCodeConfig]): Configuração para geração do QR Code.
                Se None, usa configuração padrão.

        Returns:
            str: Imagem do QR Code como string base64.

        Raises:
            ValueError: Em caso de falha na geração do QR Code.
        """
        qr_bytes = self.generate_qr_code(data, config)
        return base64.b64encode(qr_bytes).decode('utf-8')

    def generate_totp_qrcode(self,
                             secret: str,
                             user: str,
                             issuer: str,
                             config: Optional[QRCodeConfig] = None) -> bytes:
        """Gera o QRCode para configuração de TOTP em apps autenticadores.

        Args:
            secret (str): Segredo TOTP em base32.
            user (str): Nome do usuário ou email.
            issuer (str): Nome do serviço ou aplicação.
            config (typing.Optional[QRCodeConfig]): Configuração para geração do QR Code.
                Se None, usa configuração padrão.

        Returns:
            bytes: Imagem do QR Code em bytes PNG.

        Raises:
            ValueError: Em caso de parâmetros inválidos.
        """
        if not all([secret, user, issuer]):
            raise ValueError("secret, user e issuer são obrigatórios.")

        from urllib.parse import quote
        config = config or QRCodeConfig()
        label = quote(f"{issuer}:{user}")
        params = f"secret={secret}&issuer={quote(issuer)}"
        totp_uri = f"otpauth://totp/{label}?{params}"

        return self.generate_qr_code(totp_uri, config)

    def generate_totp_qrcode_base64(self,
                                    secret: str,
                                    user: str,
                                    issuer: str,
                                    config: Optional[QRCodeConfig] = None) -> str:
        """Gera o QRCode para configuração de TOTP em apps autenticadores.

        Args:
            secret (str): Segredo TOTP em base32.
            user (str): Nome do usuário ou email.
            issuer (str): Nome do serviço ou aplicação.
            config (typing.Optional[QRCodeConfig]): Configuração para geração do QR Code.
                Se None, usa configuração padrão.

        Returns:
            str: String base64 da imagem do QR Code em bytes PNG.

        Raises:
            ValueError: Em caso de parâmetros inválidos.
        """
        qr_bytes = self.generate_totp_qrcode(secret, user, issuer, config)
        return base64.b64encode(qr_bytes).decode('utf-8')
