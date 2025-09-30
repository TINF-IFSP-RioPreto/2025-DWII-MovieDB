from flask import Blueprint, render_template

root_bp = Blueprint('root',
                    __name__,
                    url_prefix='/',
                    template_folder='templates',
                    )


@root_bp.route("/")
def index():
    # @formatter:off
    """
    Render the main index page.

    Returns:
        str: Rendered HTML template for the main page.
    """
    # @formatter:on
    return render_template("root/index.jinja2",
                           title="Página principal")
