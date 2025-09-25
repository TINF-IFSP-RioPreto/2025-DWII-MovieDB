import logging


def configure_logging(logging_level: int = logging.DEBUG,
                      enable_http_log: bool = False) -> None:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_level)
    console_handler.setFormatter(MainConsoleFormatter())

    # Desativar as mensagens do servidor HTTP
    # https://stackoverflow.com/a/18379764
    if enable_http_log:
        logging.getLogger('werkzeug').setLevel(logging.INFO)
    else:
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

    logging.basicConfig(handlers=[console_handler], level=logging_level)


class MainConsoleFormatter(logging.Formatter):
    GREY = "\x1b[90m"  # Bright black (dark gray)
    GREEN = "\x1b[32m"  # Green
    YELLOW = "\x1b[33m"  # Yellow
    RED = "\x1b[31m"  # Red
    RESET = "\x1b[0m"  # Reset
    # FORMAT = "%(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d - %(funcName)s() - %(message)s"
    # FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"

    FORMATS = {
        logging.DEBUG   : GREY + FORMAT + RESET,
        logging.INFO    : GREEN + FORMAT + RESET,
        logging.WARNING : YELLOW + FORMAT + RESET,
        logging.ERROR   : RED + FORMAT + RESET,
        logging.CRITICAL: RED + FORMAT + RESET,
    }

    def format(self, record):
        log_fmt = type(self).FORMATS.get(record.levelno,
                                         type(self).GREY + type(self).FORMAT + type(self).RESET)
        formatter = logging.Formatter(log_fmt)
        # noinspection StrFormat
        return formatter.format(record)
