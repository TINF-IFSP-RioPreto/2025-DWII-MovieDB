import argparse
from moviedb import create_app

parser = argparse.ArgumentParser(description='Run the myMovieDB application')
parser.add_argument('--config', dest='config_filename',
                    default='config.dev.json',
                    help='Configuration file name (default: config.dev.json)')
args = parser.parse_args()

app = create_app(config_filename=args.config_filename)

if __name__ == "__main__":
    app.run(
        host=app.config['APP_HOST'],
        port=app.config['APP_PORT']
    )