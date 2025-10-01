# Contém a application factory
import base64
import hashlib
import json
import logging
import os
import sys
from functools import wraps

from flask import Flask

from moviedb.infra.celery import celery_init_app
from moviedb.infra import app_logging
from moviedb.infra.modulos import bootstrap, db, login_manager, migrate
from moviedb.services.email_service import EmailService


def anonymous_required(f):
    """Decorador para restringir acesso a rotas apenas para usuários anônimos.

    Se o usuário estiver autenticado, exibe uma mensagem de aviso e redireciona para a página inicial; caso contrário, permite o acesso à função decorada.

    Args:
        f (function): Função a ser decorada.

    Returns:
        function: Função decorada que verifica se o usuário não está autenticado.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from flask import redirect, url_for, flash
        if current_user.is_authenticated:
            flash("Acesso não autorizado para usuários logados no sistema", category='warning')
            return redirect(url_for('root.index'))
        return f(*args, **kwargs)

    return decorated_function


def create_app(config_filename: str = 'config.dev.json') -> Flask:
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates',
                )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app_logging.configure_logging(logging.DEBUG)

    app.logger.debug(
            "Lendo a configuração da aplicação a partir do arquivo '%s'" % (config_filename,))
    try:
        app.config.from_file(config_filename,
                             load=json.load)
    except FileNotFoundError:
        app.logger.fatal("O arquivo de configuração '%s' não existe" % (config_filename,))
        sys.exit(1)
    except json.JSONDecodeError as e:
        app.logger.fatal(
                "O arquivo de configuração '%s' não é um JSON válido: %s" % (config_filename,
                                                                             str(e),))
        sys.exit(1)
    except Exception as e:
        app.logger.fatal(
                "Erro ao carregar o arquivo de configuração '%s': %s" % (config_filename, str(e),))
        sys.exit(1)

    app.logger.debug("Aplicando configurações")
    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.logger.fatal("A chave 'SQLALCHEMY_DATABASE_URI' não está "
                         "presente no arquivo de configuração")
        sys.exit(1)

    if "DATABASE_ENCRYPTION_KEY" not in app.config or app.config.get(
            "DATABASE_ENCRYPTION_KEY") is None:
        app.logger.fatal(
                "A chave 'DATABASE_ENCRYPTION_KEY' não está presente no arquivo de configuração")
        sys.exit(1)

    if "APP_HOST" not in app.config:
        app.logger.warning("A chave 'APP_HOST' não está presente no "
                           "arquivo de configuração. Utilizando 0.0.0.0")
        app.config["APP_HOST"] = "0.0.0.0"

    if "APP_PORT" not in app.config:
        app.logger.warning("A chave 'APP_PORT' não está presente no "
                           "arquivo de configuração. Utilizando 5000")
        app.config["APP_PORT"] = 5000

    if "SECRET_KEY" not in app.config or app.config.get("SECRET_KEY") is None:
        secret_key = os.urandom(32).hex()
        app.logger.warning("A chave 'SECRET_KEY' não está presente no arquivo de configuração")
        app.logger.warning("Gerando chave aleatória: '%s'" % (secret_key,))
        app.logger.warning("Para não invalidar os tokens gerados nesta instância da aplicação, "
                           "adicione a chave acima ao arquivo de configuração")
        app.config["SECRET_KEY"] = secret_key

    if "DATABASE_ENCRYPTION_SALT" not in app.config or app.config.get(
            "DATABASE_ENCRYPTION_SALT") is None:
        app.logger.warning(
                "A chave 'DATABASE_ENCRYPTION_SALT' não está presente no arquivo de configuração")
        app.logger.warning(
                "Para não invalidar os dados criptografados armazenados no banco de dados, "
                "adicione a chave abaixo ao arquivo de configuração")

        hash_bytes = hashlib.sha256(f"{app.config.get("SECRET_KEY")}".encode()).digest()
        app.config["DATABASE_ENCRYPTION_SALT"] = base64.urlsafe_b64encode(hash_bytes).decode(
                'ascii').rstrip('=')[:20]
        app.logger.warning(
                "Gerando salt para a aplicação: '%s'" % (app.config["DATABASE_ENCRYPTION_SALT"],))

    app.logger.debug("Registrando modulos")
    bootstrap.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "É necessário estar logado para acessar esta funcionalidade"
    login_manager.login_message_category = 'warning'
    login_manager.refresh_view = 'auth.login'
    login_manager.needs_refresh_message = ("Para proteger a sua conta, é necessário "
                                           "logar novamente antes de acessar esta funcionalidade")
    login_manager.needs_refresh_message_category = "info"

    app.logger.debug("Registrando blueprints")
    from .blueprints.root import root_bp
    from .blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(root_bp)

    app.logger.debug("Definindo processadores de contexto")
    @app.context_processor
    def inject_globals():
        return dict(app_config=app.config)

    app.logger.debug("Registrando o callback do login manager")
    @login_manager.user_loader
    def load_user(user_id):  # https://flask-login.readthedocs.io/en/latest/#alternative-tokens
        import uuid
        from moviedb.models.autenticacao import User
        identifier, final_password = user_id.split('|', 1)
        try:
            auth_id = uuid.UUID(identifier)
        except ValueError:
            return None
        user = User.get_by_id(auth_id)
        return user if user and user.password.endswith(final_password) else None

    app.logger.debug("Configurando as extensões da aplicação")
    # Configura o serviço de email
    email_service = EmailService.create_from_config(app.config)
    app.extensions['email_service'] = email_service

    app.logger.debug("Registrando Celery")
    celery_init_app(app)

    app.logger.info("Aplicação configurada com sucesso")
    return app
