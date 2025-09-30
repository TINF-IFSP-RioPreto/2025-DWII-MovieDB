from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms.fields.simple import BooleanField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from moviedb.forms.validators import CampoImutavel, SenhaComplexa, UniqueEmail
from moviedb.services.image_processing_service import ImageProcessingService


class RegistrationForm(FlaskForm):
    """
    Form for user registration with email validation.

    Validates user name, email uniqueness, and password complexity.
    """
    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome para cadastro"),
                        Length(max=60, message="O nome pode ter até 60 caracteres")])
    email = StringField(
            label="Email",
            validators=[InputRequired(message="É obrigatório informar um email para cadastro"),
                        Email(message="Informe um email válido"),
                        Length(max=180, message="O email pode ter até 180 caracteres"),
                        UniqueEmail(message="Este email já está cadastrado no sistema")])
    password = PasswordField(
            label="Senha",
            validators=[InputRequired(message="É necessário escolher uma senha"),
                        SenhaComplexa()])
    password2 = PasswordField(
            label="Confirme a senha",
            validators=[InputRequired(message="É necessário repetir a senha"),
                        EqualTo('password', message="As senhas não são iguais")])
    submit = SubmitField("Criar uma conta no sistema")


class LoginForm(FlaskForm):
    """
    Form for user login with email and password.

    Includes optional remember me functionality.
    """
    email = StringField(
            label="Email",
            validators=[InputRequired(message="É obrigatório informar um email para login"),
                        Email(message="Informe um email válido"),
                        Length(max=180, message="O email pode ter até 180 caracteres")])
    password = PasswordField(
            label="Senha",
            validators=[InputRequired(message="É necessário informar a senha")])
    remember_me = BooleanField(
            label="Permanecer conectado?",
            default=True)
    submit = SubmitField("Entrar")


class SetNewPasswordForm(FlaskForm):
    # @formatter:off
    """
    Form for setting a new password.

    Validates password complexity and confirmation match.
    """
    # @formatter:on
    password = PasswordField(
            label="Nova senha",
            validators=[InputRequired(message="É necessário escolher uma senha"),
                        SenhaComplexa()])
    password2 = PasswordField(
            label="Confirme a nova senha",
            validators=[InputRequired(message="É necessário repetir a nova senha"),
                        EqualTo(fieldname='password',
                                message="As senhão não são iguais")])
    submit = SubmitField("Cadastrar a nova senha")


class AskToResetPasswordForm(FlaskForm):
    # @formatter:off
    """
    Form for requesting a password reset.

    Validates email format before sending password reset link.
    """
    # @formatter:on
    email = StringField(
            label="Email",
            validators=[
                InputRequired(message="É obrigatório informar o email para o qual se deseja "
                                      "definir nova senha"),
                Email(message="Informe um email válido"),
                Length(max=180, message="O email pode ter até 180 caracteres")
            ])
    submit = SubmitField("Redefinir a senha")


class ProfileForm(FlaskForm):
    """
    Form for updating user profile information.

    Allows modification of name, 2FA settings, and profile photo.
    Email is immutable once set.
    """
    def __init__(self, user=None, **kwargs):
        """
        Initialize profile form with reference user.

        Args:
            user: moviedb.models.user.User | None: User object to validate against, defaults to current_user.
            **kwargs: dict: Additional keyword arguments passed to FlaskForm.
        """
        super().__init__(**kwargs)
        self.reference_obj = user or current_user

    id = HiddenField(validators=[CampoImutavel('id')])

    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome para cadastro"),
                        Length(max=60,
                               message="O nome pode ter até 60 caracteres")])
    email = StringField(
            label="Email",
            validators=[CampoImutavel('email', message="O email não pode ser alterado.")])

    usa_2fa = BooleanField(
            label="Ativar o segundo fator de autenticação")

    foto_raw = FileField(
            label="Foto de perfil",
            validators=[FileAllowed(
                    upload_set=ImageProcessingService.ALLOWED_EXTENSIONS,
                    message=f"Apenas formatos PNG, JPEG e WEBP são permitidos"
            )]
    )

    submit = SubmitField("Efetuar as mudanças...")
    remover_foto = SubmitField("e remover foto")


class Read2FACodeForm(FlaskForm):
    """
    Form for reading and validating 2FA codes.

    Accepts either 6-character TOTP codes or 8-character backup codes.
    """
    codigo = StringField(
            label="Código",
            validators=[
                InputRequired(
                    message="Informe o código fornecido pelo aplicativo autenticador ou um código "
                            "de reserva"),
                Length(min=6, max=8)],
            render_kw={'autocomplete': 'one-time-code',
                       'pattern'     : r'^([A-Za-z0-9]{6}|[A-Za-z0-9]{8})$'})  # 6 ou 8
    # caracteres alfanuméricos
    submit = SubmitField("Enviar código")
