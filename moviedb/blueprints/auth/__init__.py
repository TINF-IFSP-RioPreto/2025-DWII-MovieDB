from urllib.parse import urlsplit
from uuid import UUID

from flask import Blueprint, current_app, flash, redirect, render_template, request, Response, \
    session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from markupsafe import Markup

from moviedb import anonymous_required, db
from moviedb.forms.auth import AskToResetPasswordForm, LoginForm, ProfileForm, Read2FACodeForm, \
    RegistrationForm, \
    SetNewPasswordForm
from moviedb.infra.tokens import create_jwt_token, verify_jwt_token
from moviedb.models.autenticacao import normalizar_email, User
from moviedb.models.enumeracoes import Autenticacao2FA, JWT_action

auth_bp = Blueprint(name='auth',
                    import_name=__name__,
                    url_prefix='/auth',
                    template_folder="templates", )


@auth_bp.route('/register', methods=['GET', 'POST'])
@anonymous_required
def register():
    """
    Exibe o formulário de registro de usuário e processa o cadastro.

    - Usuários já autenticados não podem acessar esta rota.
    - Se o formulário for enviado e validado, cria um novo usuário,
      salva no banco de dados, envia um email de confirmação e
      redireciona para a página inicial.
    - O usuário deve confirmar o email antes de conseguir logar.
    - Caso contrário, renderiza o template de registro.

    Returns:
        Response: Redireciona ou renderiza o template de registro.
    """

    form = RegistrationForm()
    if form.validate_on_submit():
        usuario = User()
        usuario.nome = form.nome.data
        usuario.email = form.email.data
        usuario.ativo = False
        usuario.password = form.password.data
        db.session.add(usuario)
        # Realiza o flush para garantir que o usuário tenha um ID gerado antes do commit.
        db.session.flush()
        # Atualiza o objeto usuário com os dados mais recentes do banco de dados.
        db.session.refresh(usuario)
        token = create_jwt_token(action=JWT_action.VALIDAR_EMAIL, sub=usuario.email)
        current_app.logger.debug("Token de validação de email: %s" % (token,))
        body = render_template('auth/email/email_confirmation.jinja2',
                               nome=usuario.nome,
                               url=url_for('auth.valida_email', token=token))
        if not usuario.send_email(subject="Confirme o seu email", body=body):
            flash("Erro no envio do email de confirmação da conta", category="danger")
        db.session.commit()
        flash("Cadastro efetuado com sucesso. Confirme o seu email antes de logar "
              "no sistema", category='success')
        return redirect(url_for('root.index'))

    return render_template('auth/web/register.jinja2',
                           title="Cadastrar um novo usuário",
                           form=form)


@auth_bp.route('/revalida_email/<uuid:user_id>')
@anonymous_required
def revalida_email(user_id):
    """
    Reenvia o email de validação para o usuário com o ID fornecido.

    - Usuários autenticados não podem acessar esta rota.
    - Verifica se o usuário existe e se não está ativo.
    - Gera um novo token de validação e envia um email com o link de confirmação.
    - Exibe mensagens de sucesso ou erro conforme o caso.

    Args:
        user_id (UUID): Identificador único do usuário.

    Returns:
        Response: Redireciona para a página de login.
    """

    try:
        uuid_obj = UUID(str(user_id))
    except ValueError:
        flash("ID de usuário inválido", category='warning')
        return redirect(url_for('root.index'))

    usuario = User.get_by_id(uuid_obj)
    if usuario is None:
        flash("Usuário inexistente", category='warning')
        return redirect(url_for('root.index'))
    if usuario.ativo:
        flash("Usuário já está ativo. Faça login no sistema", category='info')
        return redirect(url_for('auth.login'))

    token = create_jwt_token(action=JWT_action.VALIDAR_EMAIL, sub=usuario.email)
    current_app.logger.debug("Token de validação de email: %s" % (token,))
    body = render_template('auth/email/email_confirmation.jinja2',
                           nome=usuario.nome,
                           url=url_for('auth.valida_email', token=token))
    if not usuario.send_email(subject="Confirme o seu email", body=body):
        flash("Erro no envio do email de confirmação da conta", category="danger")
    else:
        flash(f"Um novo email de confirmação foi enviado para {usuario.email}. "
              f"Confirme o seu email antes de logar no sistema", category='success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    """
    Exibe o formulário de login e processa a autenticação do usuário.

    - Usuários já autenticados não podem acessar esta rota.
    - Se o formulário for enviado e validado, verifica as credenciais do usuário.
    - Se o usuário existir, estiver ativo e a senha estiver correta, ou encaminha
      para a página de 2FA, ou realiza o login conforme o caso.
    - Se efetuar o login sem 2FA, redireciona para a página desejada ou para a página inicial.
    - Caso contrário, exibe mensagens de erro e permanece na página de login.

    Returns:
        Response: Redireciona ou renderiza o template de login.
    """

    form = LoginForm()

    if form.validate_on_submit():
        usuario = User.get_by_email(form.email.data)

        if usuario is None or not usuario.check_password(form.password.data):
            flash("Email ou senha incorretos", category='warning')
            return redirect(url_for('auth.login'))
        if not usuario.ativo:

            flash(Markup(f"Usuário está impedido de acessar o sistema. Precisa de um <a href=\""
                         f"{url_for('auth.revalida_email', user_id=usuario.id)}\""
                         f">novo email de confirmacao</a>?"), category='warning')
            return redirect(url_for('auth.login'))
        if usuario.usa_2fa:
            # CRITICO: Token indicando que a verificação da senha está feita, mas o 2FA
            #  ainda não. Necessário para proteger a rota /get2fa.
            session['pending_2fa_token'] = (
                create_jwt_token(action=JWT_action.PENDING_2FA,
                                 sub=usuario.id,
                                 expires_in=current_app.config.get('2FA_SESSION_TIMEOUT', 90),
                                 extra_data={
                                     'remember_me': bool(form.remember_me.data),
                                     'next'       : request.args.get('next')
                                 })
            )
            current_app.logger.debug("pending_2fa_token: %s" % (session['pending_2fa_token'],))
            flash("Conclua o login digitando o código do segundo fator de autenticação",
                  category='info')
            return redirect(url_for('auth.get2fa'))

        login_user(usuario, remember=form.remember_me.data)
        db.session.commit()
        flash(f"Usuario {usuario.email} logado", category='success')
        current_app.logger.debug("Usuário %s logado" % (usuario.email,))

        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('root.index')
        return redirect(next_page)

    return render_template('auth/web/login.jinja2',
                           title="Login",
                           form=form)


@auth_bp.route('/get2fa', methods=['GET', 'POST'])
@anonymous_required
def get2fa():
    """
    Exibe e processa o formulário de segundo fator de autenticação (2FA).

    - Usuários já autenticados não podem acessar esta rota.
    - Verifica se a sessão contém informações de usuário pendente de 2FA.
    - Implementa expiração da sessão de 2FA baseada em tempo (opcional).
    - Valida o código 2FA informado pelo usuário (TOTP ou código reserva).
    - Finaliza o login se o código estiver correto, ou exibe mensagem de erro.
    - Limpa variáveis de sessão após sucesso ou falha.

    Returns:
        Response: Redireciona para a página desejada após login ou renderiza o formulário de 2FA.
    """

    # CRITICO: Verifica se a variável de sessão que indica que a senha foi validada
    #  está presente. Se não estiver, redireciona para a página de login.
    pending_2fa_token = session.get('pending_2fa_token')
    if not pending_2fa_token:
        current_app.logger.warning(
                "Tentativa de acesso 2FA não autorizado a partir do IP %s" % (request.remote_addr,))
        flash("Acesso negado. Reinicie o processo de login.", category='error')
        return redirect(url_for('auth.login'))

    dados_token = verify_jwt_token(pending_2fa_token)
    if not dados_token.get('valid', False) or \
            dados_token.get('action') != JWT_action.PENDING_2FA or \
            not dados_token.get('extra_data', False):
        session.pop('pending_2fa_token', None)
        current_app.logger.warning(
                "Tentativa de acesso 2FA com token inválido ou expirado a partir do IP %s" %
                (request.remote_addr,))
        flash("Sessão de autenticação inválida ou expirada. Refaça o login.", category='warning')
        return redirect(url_for('auth.login'))

    user_id = dados_token.get('sub')
    remember_me = dados_token.get('extra_data').get('remember_me', False)
    next_page = dados_token.get('extra_data').get('next', None)

    form = Read2FACodeForm()
    if form.validate_on_submit():
        usuario = User.get_by_id(user_id)
        if usuario is None or not usuario.usa_2fa:
            # Limpa variáveis de sessão e volta para o login
            session.pop('pending_2fa_token', None)
            return redirect(url_for('auth.login'))

        token = str(form.codigo.data)
        resultado, metodo = usuario.verify_2fa_code(token)
        if resultado:
            # Limpa variáveis de sessão e finaliza login
            session.pop('pending_2fa_token', None)
            login_user(usuario, remember=remember_me)
            usuario.ultimo_otp = token
            db.session.commit()

            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('root.index')

            flash(f"Usuario {usuario.email} logado", category='success')
            if metodo == Autenticacao2FA.BACKUP:
                flash(Markup("Você usou um código reserva para autenticação. "
                             "Considere gerar novos códigos reserva na sua página de perfil."),
                      category='warning')
            return redirect(next_page)

        # Código errado. Registra tentativa falha e permanece na página de 2FA
        current_app.logger.warning("Código 2FA inválido para usuario %s a partir do IP %s" % (
            usuario.id, request.remote_addr,))
        flash("Código incorreto. Tente novamente", category='warning')

    return render_template('auth/web/2fa.jinja2',
                           title="Login",
                           title_card="Segundo fator de autenticação",
                           subtitle_card="Digite o código do segundo fator de autenticação que "
                                         "aparece no seu aplicativo autenticador, ou um dos seus "
                                         "códigos reserva",
                           form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Realiza o logout do usuário autenticado.

    - Encerra a sessão do usuário.
    - Exibe uma mensagem de sucesso.
    - Redireciona para a página inicial.

    Returns:
        Response: Redireciona para a página inicial após logout.
    """
    logout_user()
    flash("Logout efetuado com sucesso!", category='success')
    return redirect(url_for('root.index'))


@auth_bp.route('/valida_email/<token>')
@anonymous_required
def valida_email(token):
    """
    Valida o email do usuário a partir de um token JWT enviado na URL.

    - Usuários autenticados não podem acessar esta rota.
    - O token JWT é verificado e deve conter as claims 'sub' (email) e 'action' igual a
    VALIDAR_EMAIL.
    - Se o usuário existir, não estiver ativo e o token for válido, ativa o usuário.
    - Exibe mensagens de sucesso ou erro conforme o caso.

    Args:
        token (str): Token JWT enviado na URL para validação do email.

    Returns:
        Response: Redireciona para a página de login ou inicial, conforme o caso.
    """

    claims = verify_jwt_token(token)
    if not (claims.get('valid', False) and {'sub', 'action'}.issubset(claims)):
        flash("Token incorreto ou incompleto", category='warning')
        return redirect(url_for('root.index'))

    usuario = User.get_by_email(claims.get('sub'))
    if (usuario is not None and
            not usuario.ativo and
            claims.get('action') == JWT_action.VALIDAR_EMAIL):
        usuario.ativo = True
        flash(f"Email {usuario.email} validado!", category='success')
        db.session.commit()
        return redirect(url_for('auth.login'))
    flash("Token inválido", category='warning')
    return redirect(url_for('auth.login'))


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
@anonymous_required
def reset_password(token):
    """
    Exibe o formulário para redefinição de senha e processa a troca de senha do usuário.

    - Usuários autenticados não podem acessar esta rota.
    - O token JWT é verificado e deve conter as claims 'sub' (email) e 'action' igual a
    RESET_PASSWORD.
    - Se o usuário existir e o token for válido, permite a redefinição da senha.
    - Em caso de token inválido ou usuário inexistente, exibe mensagem de erro.

    Args:
        token (str): Token JWT enviado na URL para redefinição de senha.

    Returns:
        Response: Redireciona para a página de login ou inicial, conforme o caso.
    """

    claims = verify_jwt_token(token)
    if not (claims.get('valid', False) and {'sub', 'action'}.issubset(claims)):
        flash("Token incorreto ou incompleto", category='warning')
        return redirect(url_for('root.index'))

    usuario = User.get_by_email(claims.get('sub'))
    if usuario is not None and claims.get('action') == JWT_action.RESET_PASSWORD:
        form = SetNewPasswordForm()
        if form.validate_on_submit():
            usuario.password = form.password.data
            db.session.commit()
            flash("Sua senha foi redefinida com sucesso", category='success')
            return redirect(url_for('auth.login'))
        return render_template('auth/web/simple_form.jinja2',
                               title_card="Escolha uma nova senha",
                               form=form)
    # token não é de reset_password ou é para um usuário inexistente
    flash("Token inválido", category='warning')
    return redirect(url_for('root.index'))


@auth_bp.route('/new_password', methods=['GET', 'POST'])
@anonymous_required
def new_password():
    """
    Exibe o formulário para solicitar redefinição de senha.

    - Usuários autenticados não podem acessar esta rota.
    - Se o formulário for enviado e validado, normaliza o email e verifica se existe
      um usuário cadastrado com esse email.
    - Sempre exibe uma mensagem informando que, se houver uma conta, um email será enviado.
    - Se o usuário existir, gera um token JWT para redefinição de senha e envia um email
      com instruções.
    - Se o usuário não existir, registra um aviso no log.
    - Renderiza o formulário caso não seja enviado ou validado.

    Returns:
        Response: Redireciona para a página de login ou renderiza o formulário.
    """

    form = AskToResetPasswordForm()
    if form.validate_on_submit():
        email = normalizar_email(form.email.data)
        usuario = User.get_by_email(email)
        flash(f"Se houver uma conta com o email {email}, uma mensagem será enviada com as "
              f"instruções para a troca da senha", category='info')
        if usuario is not None:
            token = create_jwt_token(JWT_action.RESET_PASSWORD,
                                     sub=usuario.email)
            body = render_template('auth/email/email_new_password.jinja2',
                                   nome=usuario.nome,
                                   url=url_for('auth.reset_password', token=token))
            usuario.send_email(subject="Altere a sua senha", body=body)
            return redirect(url_for('auth.login'))
        current_app.logger.warning(
                "Pedido de reset de senha para usuário inexistente (%s)" % (email,))
        return redirect(url_for('auth.login'))
    return render_template('auth/web/simple_form.jinja2',
                           title="Esqueci minha senha",
                           title_card="Esqueci minha senha",
                           subtitle_card="Digite o seu email cadastrado no sistema para "
                                         "solicitar uma nova senha",
                           form=form)


@auth_bp.route('/<uuid:id_usuario>/imagem/<size>', methods=['GET'])
@login_required
def imagem(id_usuario, size):
    """
    Retorna a imagem ou avatar do usuário autenticado, conforme o parâmetro size.

    - Apenas o próprio usuário pode acessar sua imagem.
    - Retorna 404 se o usuário não for o dono, não existir ou não possuir foto.
    - Utiliza o tipo MIME correto para a resposta.

    Args:
        id_usuario (UUID): Identificador único do usuário.
        size (str): 'full' para foto completa, 'avatar' para avatar.

    Returns:
        Response: Imagem do usuário ou status 404 se não encontrada.
    """
    if str(current_user.id) != str(id_usuario):
        return Response(status=404)
    usuario = User.get_by_id(id_usuario)
    if usuario is None or not usuario.com_foto:
        return Response(status=404)
    if size == "full":
        imagem_content, imagem_type = usuario.foto
    elif size == "avatar":
        imagem_content, imagem_type = usuario.avatar
    else:
        return Response(status=404)
    return Response(imagem_content, mimetype=imagem_type)


@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Exibe e processa o formulário de edição do perfil do usuário autenticado.

    - Permite ao usuário alterar nome, email e foto.
    - Apenas o próprio usuário pode acessar e modificar seus dados.
    - Remove o botão de remover foto se o usuário não possui foto.
    - Valida e processa o envio de nova foto ou remoção da existente.
    - Ativa ou desativa o 2FA conforme a escolha do usuário.
    - Salva alterações no banco de dados e exibe mensagens de sucesso ou erro.

    Returns:
        Response: Redireciona para a página inicial após alterações ou
        renderiza o formulário de perfil.
    """
    form = ProfileForm()
    # TODO: quando submete uma foto, ao recarregar o formulário ele não acrescenta o botão de
    #  remover a foto que outrora fora retirado
    if not current_user.com_foto:
        del form.remover_foto

    if request.method == 'GET':
        form.id.data = str(current_user.id)
        form.nome.data = current_user.nome
        form.email.data = current_user.email
        form.usa_2fa.data = current_user.usa_2fa

    if form.validate_on_submit():
        current_user.nome = form.nome.data
        if 'remover_foto' in form and form.remover_foto.data:
            current_user.foto = None
        elif form.foto_raw.data:
            foto = request.files[form.foto_raw.name]
            if foto:
                current_user.foto = foto
            else:
                current_user.foto = None
                flash("Problemas no envio da imagem", category='warning')
        if form.usa_2fa.data:
            if not current_user.usa_2fa:
                current_user.otp_secret = None  # Garante que um novo segredo será gerado
                db.session.commit()
                flash("Alterações efetuadas. Conclua a ativação do segundo fator de "
                      "autenticação", category='info')
                return redirect(url_for('auth.enable_2fa'))
        else:
            if current_user.usa_2fa:
                if current_user.disable_2fa():
                    flash("Segundo fator de autenticação desativado", category='success')
        db.session.commit()
        flash("Alterações efetuadas", category='success')
        return redirect(url_for("root.index"))

    return render_template(
            'auth/web/profile.jinja2',
            title="Perfil do usuário",
            title_card="Alterando os seus dados pessoais",
            form=form)


@auth_bp.route('enable_2fa', methods=['GET', 'POST'])
@login_required
def enable_2fa():
    """
    Ativa o segundo fator de autenticação (2FA) para o usuário autenticado.

    - Se o usuário já possui 2FA ativado, exibe mensagem informativa e redireciona para o perfil.
    - Exibe o formulário para digitar o código TOTP gerado pelo autenticador.
    - Se o código for válido, ativa o 2FA, gera códigos de backup e exibe-os ao usuário.
    - Se o código for inválido, exibe mensagem de erro e redireciona para a página de ativação.
    - Renderiza o formulário de ativação do 2FA caso não seja enviado ou validado.

    Returns:
        Response: Renderiza o formulário de ativação do 2FA ou exibe os códigos de backup.
    """
    if current_user.usa_2fa:
        flash("Configuração já efetuada. Para alterar, desative e reative o uso do "
              "segundo fator de autenticação", category='info')
        return redirect(url_for('auth.profile'))

    form = Read2FACodeForm()
    if request.method == 'POST' and form.validate():
        resultado, metodo = current_user.verify_2fa_code(form.codigo.data, totp_only=True)
        if resultado:
            codigos = current_user.enable_2fa(otp_secret=current_user.otp_secret,
                                              ultimo_otp=form.codigo.data,
                                              generate_backup=True,
                                              back_codes=10)
            db.session.commit()
            flash("Segundo fator de autenticação ativado", category='success')
            subtitle_card = ("<p>Guarde com cuidado os códigos abaixo. Eles podem ser usados "
                             "para confirmação da autenticação de dois fatores quando você não "
                             "tiver o seu autenticador disponível.</p>"
                             "<p><strong>Eles serão mostrados apenas esta vez!</strong></p>")

            return render_template('auth/web/show_2fa_backup.jinja2',
                                   codigos=codigos,
                                   title="Códigos reserva",
                                   title_card="Códigos reserva para segundo fator de autenticação",
                                   subtitle_card=Markup(subtitle_card))
        # Código errado
        if metodo == Autenticacao2FA.REUSED:
            flash("O código informado foi usado recentemente. Se você está vendo esta mensagem "
                  "repetidamente, desative e reative o 2FA.", category='warning')
            current_app.logger.error(
                "Usuário %s reutilizou um código TOTP na ativação do 2FA" % (current_user.email,))
        else:
            flash("O código informado está incorreto. Tente novamente.", category='warning')
        return redirect(url_for('auth.enable_2fa'))

    return render_template('auth/web/enable_2fa.jinja2',
                           title="Ativação do 2FA",
                           title_card="Ativação do segundo fator de autenticação",
                           form=form,
                           imagem=current_user.b64encoded_qr_totp_uri,
                           token=current_user.otp_secret_formatted)
