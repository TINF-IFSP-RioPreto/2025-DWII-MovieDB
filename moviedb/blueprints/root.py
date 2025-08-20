from flask import Blueprint, render_template

bp = Blueprint('root',
               __name__,
               url_prefix='/',
               )


@bp.route("/")
def index():
    return render_template("root/index.jinja2",
                           title="Página principal")
