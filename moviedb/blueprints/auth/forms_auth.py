from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms.fields.simple import BooleanField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from moviedb.forms.validators import CampoImutavel
from forms.validators import SenhaComplexa, UniqueEmail
from services.image_processing_service import ImageProcessingService


class RegistrationForm(FlaskForm):
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
    def __init__(self, user=None, **kwargs):
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
            validators=[FileAllowed(upload_set=list(ImageProcessingService.SUPPORTED_FORMATS),
                                    message=f"Apenas formatos {', '.join(ImageProcessingService.SUPPORTED_FORMATS)} "
                                            "são permitidos")])

    submit = SubmitField("Efetuar as mudanças...")
    remover_foto = SubmitField("e remover foto")


class Read2FACodeForm(FlaskForm):
    codigo = StringField(
            label="Código",
            validators=[
                InputRequired(message="Informe o código fornecido pelo aplicativo autenticador"),
                Length(min=6, max=8)],
            render_kw={'autocomplete': 'one-time-code',
                       'pattern'     : r'^[A-Za-z0-9]{8}$'})
    submit = SubmitField("Enviar código")
