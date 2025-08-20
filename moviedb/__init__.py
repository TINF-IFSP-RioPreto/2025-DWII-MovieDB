# Contém a application factory
import json
import logging
import os
import sys

from flask import Flask

from moviedb.infra import app_logging
from moviedb.infra.modulos import bootstrap


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

    app.logger.debug("Configurando a aplicação a partir do arquivo '%s'" % (config_filename))
    try:
        app.config.from_file(config_filename,
                             load=json.load)
    except FileNotFoundError:
        app.logger.fatal("O arquivo de configuração '%s' não existe" % (config_filename))
        sys.exit(1)

    app.logger.debug("Registrando modulos")
    bootstrap.init_app(app)

    app.logger.debug("Registrando blueprints")
    from moviedb.blueprints.root import bp as root_bp
    app.register_blueprint(root_bp)

    app.logger.debug("Definindo processadores de contexto")
    @app.context_processor
    def inject_globals():
        return dict(app_config=app.config)

    return app
