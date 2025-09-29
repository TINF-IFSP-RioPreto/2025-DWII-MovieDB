import io
from base64 import b64encode
from dataclasses import dataclass
from typing import Optional, Tuple

from flask import current_app
from PIL import Image


class ImageProcessingError(Exception):
    """Exceção customizada para erros de processamento de imagem."""
    pass


@dataclass
class ImageProcessingResult:
    foto_base64: str  # Foto original em base64
    avatar_base64: str  # Avatar redimensionado em base64
    mime_type: str  # Tipo MIME da imagem
    formato_original: str  # Formato original (JPEG, PNG, etc)
    dimensoes_originais: Tuple[int, int]  # (largura, altura) original
    dimensoes_avatar: Tuple[int, int]  # (largura, altura) do avatar
    tamanho_arquivo: int  # Tamanho do arquivo original em bytes


class ImageProcessingService:
    """Serviço responsável por processamento e manipulação de imagens."""

    # Formatos suportados
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP'}

    # Extensões permitidas (para validação de upload)
    ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp']

    # Tamanhos padrão
    DEFAULT_AVATAR_SIZE = 32
    DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_MAX_DIMENSIONS = (2048, 2048)

    # Qualidade de compressão
    JPEG_QUALITY = 85
    PNG_OPTIMIZE = True

    @staticmethod
    def processar_upload_foto(arquivo_upload,
                              avatar_size: Optional[int] = None,
                              max_file_size: Optional[int] = None,
                              max_dimensions: Optional[
                                  Tuple[int, int]] = None) -> ImageProcessingResult:
        """
        Processa um arquivo de imagem enviado via upload, gerando foto original e avatar.

        Args:
            arquivo_upload: Objeto de arquivo (FileStorage do Flask)
            avatar_size: Tamanho do avatar em pixels (padrão: configuração da app ou 32)
            max_file_size: Tamanho máximo do arquivo em bytes (padrão: configuração da app ou 5MiB)
            max_dimensions: Dimensões máximas permitidas (largura, altura) (padrão: configuração
            da app ou (2048, 2048))

        Returns:
            ImageProcessingResult: Resultado do processamento da imagem

        Raises:
            ImageProcessingError: Em caso de erro no processamento
            ValueError: Para arquivos inválidos ou muito grandes
        """
        if arquivo_upload is None:
            raise ValueError("Nenhum arquivo fornecido")

        # Configurações com fallbacks
        avatar_size = avatar_size or current_app.config.get('AVATAR_SIZE',
                                                            ImageProcessingService.DEFAULT_AVATAR_SIZE)
        max_file_size = max_file_size or current_app.config.get('MAX_IMAGE_SIZE',
                                                                ImageProcessingService.DEFAULT_MAX_FILE_SIZE)
        max_dimensions = max_dimensions or current_app.config.get('MAX_IMAGE_DIMENSIONS',
                                                                  ImageProcessingService.DEFAULT_MAX_DIMENSIONS)

        try:
            # Lê os dados do arquivo
            arquivo_upload.seek(0)  # Garante que está no início
            foto_data = arquivo_upload.read()

            if not foto_data:
                raise ValueError("Arquivo de imagem vazio")

            # Validação de tamanho
            if len(foto_data) > max_file_size:
                raise ValueError(
                        f"Arquivo muito grande. Máximo permitido: "
                        f"{max_file_size / (1024 * 1024):.1f}MB")

            # Processa a imagem
            return ImageProcessingService._processar_imagem_bytes(
                    foto_data,
                    arquivo_upload.mimetype,
                    avatar_size,
                    max_dimensions
            )

        except (AttributeError, OSError) as e:
            raise ImageProcessingError(f"Erro ao processar arquivo de imagem: {str(e)}") from e

    @staticmethod
    def _processar_imagem_bytes(foto_data: bytes,
                                mime_type: str,
                                avatar_size: int,
                                max_dimensions: Tuple[int, int]) -> ImageProcessingResult:
        """
        Processa dados de imagem em bytes.

        Args:
            foto_data: Dados da imagem em bytes
            mime_type: Tipo MIME fornecido pelo upload
            avatar_size: Tamanho do avatar
            max_dimensions: Dimensões máximas

        Returns:
            dict: Resultado do processamento
        """
        try:
            with Image.open(io.BytesIO(foto_data)) as imagem:
                # Validações básicas
                if not hasattr(imagem, 'format') or imagem.format is None:
                    raise ImageProcessingError("Formato de imagem não reconhecido")

                if imagem.format not in ImageProcessingService.SUPPORTED_FORMATS:
                    raise ImageProcessingError(f"Formato {imagem.format} não suportado. "
                                               f"Formatos aceitos: "
                                               f"{', '.join(ImageProcessingService.SUPPORTED_FORMATS)}")

                largura_orig, altura_orig = imagem.size

                # Validação de dimensões
                if largura_orig > max_dimensions[0] or altura_orig > max_dimensions[1]:
                    raise ValueError(
                            f"Imagem muito grande. Máximo: {max_dimensions[0]}x{max_dimensions[
                                1]} pixels")

                # Otimiza a imagem original se necessário
                foto_otimizada = ImageProcessingService._otimizar_imagem_original(imagem)

                # Gera avatar
                avatar_data, avatar_dims = ImageProcessingService._gerar_avatar(imagem, avatar_size)

                return ImageProcessingResult(
                        foto_base64=b64encode(foto_otimizada).decode('utf-8'),
                        avatar_base64=b64encode(avatar_data).decode('utf-8'),
                        mime_type=mime_type,
                        formato_original=imagem.format,
                        dimensoes_originais=(largura_orig, altura_orig),
                        dimensoes_avatar=avatar_dims,
                        tamanho_arquivo=len(foto_data))

        except Exception as e:
            if isinstance(e, (ImageProcessingError, ValueError)):
                raise
            raise ImageProcessingError(f"Erro no processamento da imagem: {str(e)}") from e

    @staticmethod
    def _otimizar_imagem_original(imagem: Image.Image) -> bytes:
        """
        Otimiza a imagem original mantendo qualidade mas reduzindo tamanho do arquivo.

        Args:
            imagem: Objeto PIL Image

        Returns:
            bytes: Dados da imagem otimizada
        """
        buffer = io.BytesIO()
        formato = imagem.format

        # Parâmetros de otimização por formato
        save_kwargs = {'format': formato}

        if formato == 'JPEG':
            save_kwargs['quality'] = ImageProcessingService.JPEG_QUALITY
            save_kwargs['optimize'] = True
            save_kwargs['progressive'] = True
        elif formato == 'PNG':
            save_kwargs['optimize'] = ImageProcessingService.PNG_OPTIMIZE
            save_kwargs['compress_level'] = 6  # Balanço entre velocidade e compressão
        elif formato == 'WEBP':
            save_kwargs['quality'] = ImageProcessingService.JPEG_QUALITY
            save_kwargs['method'] = 6  # Melhor compressão

        imagem.save(buffer, **save_kwargs)
        return buffer.getvalue()

    @staticmethod
    def _gerar_avatar(imagem: Image.Image, avatar_size: int) -> Tuple[bytes, Tuple[int, int]]:
        """
        Gera avatar redimensionado a partir da imagem.

        Args:
            imagem: Objeto PIL Image
            avatar_size: Tamanho desejado do avatar

        Returns:
            tuple: (dados_avatar, dimensoes_finais)
        """
        largura, altura = imagem.size
        formato_original = imagem.format

        imagem_avatar = imagem.copy()
        # Otimização: pula redimensionamento se já está no tamanho adequado
        if max(largura, altura) > avatar_size:
            # Calcula novo tamanho mantendo proporção
            fator_escala = min(avatar_size / largura, avatar_size / altura)
            novo_tamanho = (
                int(largura * fator_escala),
                int(altura * fator_escala)
            )
            imagem_avatar = imagem.copy()
            imagem_avatar.thumbnail(novo_tamanho, Image.Resampling.LANCZOS)
        buffer_avatar = io.BytesIO()
        imagem_avatar.save(buffer_avatar, format=formato_original, optimize=True)
        return buffer_avatar.getvalue(), imagem_avatar.size
