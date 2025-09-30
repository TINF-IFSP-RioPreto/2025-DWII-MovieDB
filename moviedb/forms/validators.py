from typing import Any, Callable, Optional

from flask import current_app
from wtforms.validators import ValidationError


class CampoImutavel:
    """
    Validador WTForms genérico para garantir que um campo não seja modificado pelo usuário no lado do cliente.

    Usa introspecção para acessar o objeto de referência através do formulário.

    Examples:
        class ProfileForm(FlaskForm):
            def __init__(self, obj=None, **kwargs):
                super().__init__(**kwargs)
                self.reference_obj = obj or current_user

            id = HiddenField(validators=[CampoImutavel('id')])
            email = StringField(validators=[CampoImutavel('email')])
    """

    def __init__(self,
                 field_name: str,
                 attr_name: Optional[str] = None,
                 message: Optional[str] = None,
                 converter: Optional[Callable[[Any], Any]] = None) -> None:
        # @formatter:off
        """
        Inicializa o validador de campos imutáveis genérico.

        Args:
            field_name (str): Nome do campo no formulário.
            attr_name (Optional[str]): Nome do atributo no objeto de referência (padrão: mesmo que field_name).
            message (Optional[str]): Mensagem de erro personalizada.
            converter (Optional[Callable[[Any], Any]]): Função para converter o valor de referência.

        Returns:
            None
        """
        # @formatter:on
        self.field_name = field_name
        self.attr_name = attr_name or field_name
        self.converter = converter or (str if field_name == 'id' else lambda x: x)
        self.message = message or f"Tentativa de modificação não autorizada do campo {field_name}"

    def __call__(self, form, field) -> None:
        # @formatter:off
        """
        Executa a validação do campo imutável usando introspecção no formulário.

        Args:
            form: O formulário WTForms sendo validado.
            field: O campo a ser verificado.

        Returns:
            None

        Raises:
            ValidationError: Se o valor do campo for diferente do valor esperado.
        """
        # @formatter:on
        # Verifica se o formulário tem um objeto de referência
        if not hasattr(form, 'reference_obj'):
            raise ValidationError("Formulário deve ter atributo 'reference_obj'")

        reference_obj = form.reference_obj
        if reference_obj is None:
            raise ValidationError("Objeto de referência não pode ser None")

        try:
            expected_value = getattr(reference_obj, self.attr_name)
            expected_value = self.converter(expected_value)
        except AttributeError:
            current_app.logger.error("Atributo '%s' não encontrado no objeto %s" %
                                     (self.attr_name, type(reference_obj).__name__,))
            raise ValidationError("Erro interno na validação")
        except Exception as e:
            current_app.logger.error("Erro ao processar valor de referência para %s: %s" %
                                     (self.field_name, str(e),))
            raise ValidationError("Erro interno na validação")

        if field.data != expected_value:
            current_app.logger.warning(
                    "Violação da integridade: campo %s alterado de '%s' para '%s'" %
                    (self.field_name, expected_value, field.data,))
            raise ValidationError(self.message)


class UniqueEmail(object):
    """
    Validador WTForms para garantir que o email informado não está cadastrado no sistema.

    Args:
        message (Optional[str]): Mensagem de erro personalizada.
    """

    def __init__(self, message=None):
        if not message:
            message = "Já existe um usuário com este email"
        self.message = message

    def __call__(self, form, field):
        # @formatter:off
        """
        Verifica se um email já está cadastrado.

        Args:
            form: O formulário sendo validado.
            field: O campo de email a ser verificado.

        Raises:
            ValidationError: Se o email já estiver cadastrado.
        """
        # @formatter:on
        from moviedb.models.autenticacao import User
        if User.get_by_email(field.data):
            raise ValidationError(self.message)


class SenhaComplexa(object):
    """
    Validador WTForms para garantir que a senha informada atende aos requisitos de complexidade definidos.

    Os requisitos são definidos pelas seguintes chaves inteiras e booleanas no dicionário de configuração da aplicação:

    - PASSWORD_MIN: 8
    - PASSWORD_MINUSCULA: false
    - PASSWORD_NUMERO: false
    - PASSWORD_SIMBOLO: false
    - PASSWORD_MAIUSCULA: false
    """

    def __init__(self):
        pass

    def __call__(self, form, field):
        # @formatter:off
        """
        Realiza a validação da senha conforme os requisitos definidos.

        Args:
            form: O formulário sendo validado.
            field: O campo de senha a ser verificado.

        Raises:
            ValidationError: Se a senha não atender aos requisitos de complexidade.
        """
        # @formatter:on
        from flask import current_app
        import re
        from collections import namedtuple

        Teste = namedtuple('Teste', ['config', 'mensagem', 're'])

        lista_de_testes = [
            Teste('PASSWORD_MAIUSCULA', "letras maiúsculas", r'[A-Z]'),
            Teste('PASSWORD_MINUSCULA', "letras minúsculas", r'[a-z]'),
            Teste('PASSWORD_NUMERO', "números", r'\d'),
            Teste('PASSWORD_SIMBOLO', "símbolos especiais", r'\W')
        ]

        min_caracteres = current_app.config.get('PASSWORD_MIN', 0)
        senha_valida = (len(field.data) >= min_caracteres)
        mensagens = [f"pelo menos {min_caracteres} caracteres"]

        for teste in lista_de_testes:
            if current_app.config.get(teste.config, False):
                senha_valida = senha_valida and (re.search(teste.re, field.data) is not None)
                mensagens.append(teste.mensagem)

        mensagem = "A sua senha precisa conter "
        if len(mensagens) > 1:
            mensagem = mensagem + " e ".join([", ".join(mensagens[:-1]), mensagens[-1]])
        else:
            mensagem = mensagem + mensagens[0]
        mensagem = mensagem + "."

        if not senha_valida:
            raise ValidationError(mensagem)

        return
