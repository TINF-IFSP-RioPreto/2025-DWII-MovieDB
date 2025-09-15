# Contém a application factory
import json
import logging
import os
import sys

from flask import Flask

from moviedb.infra import app_logging
from moviedb.infra.modulos import bootstrap, db, login_manager, migrate


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

    app.logger.debug("Configurando a aplicação a partir do arquivo '%s'" % (config_filename,))
    try:
        app.config.from_file(config_filename,
                             load=json.load)
    except FileNotFoundError:
        app.logger.fatal("O arquivo de configuração '%s' não existe" % (config_filename,))
        sys.exit(1)

    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.logger.fatal("A chave 'SQLALCHEMY_DATABASE_URI' não está "
                         "presente no arquivo de configuração")
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
        app.logger.warning("A chave 'SECRET_KEY' não está presente no "
                           "arquivo de configuração")
        app.logger.warning("Gerando chave aleatória: '%s'" % (secret_key,))
        app.logger.warning("Para não invalidar os logins persistentes e os JWT "
                           "gerados efetuados nesta instância da aplicação, "
                           "adicione a chave acima ao arquivo de configuração")
        app.config["SECRET_KEY"] = secret_key

    app.logger.debug("Registrando modulos")
    bootstrap.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    login_manager.init_app(app)

    app.logger.debug("Registrando blueprints")
    from moviedb.blueprints.root import bp as root_bp
    from moviedb.blueprints.auth import bp as auth_bp
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

    app.logger.info("Aplicação configurada com sucesso")
    return app
