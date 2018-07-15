"""
    cloudalbum.application.py
    ~~~~~~~~~~~~~~~~~~~~~~~
    CloudAlbum is a sample application for TechSummit 2018 workshop.

    :copyright: © 2018 by Sungshik Jou.
    :license: BSD, see LICENSE for more details.
"""

from cloudalbum.config import options
from cloudalbum import login
from cloudalbum.controlloer.errors import errorHandler
from cloudalbum.controlloer.user import userView
from cloudalbum.controlloer.site import siteView
from cloudalbum.controlloer.photo import photoView
from cloudalbum.model import models
from logging.handlers import RotatingFileHandler
from logging import Formatter
from flask import redirect, url_for, current_app, request
from flask_wtf.csrf import CSRFProtect
from cloudalbum import util
import os
import logging


def init_app(app):
    """
    CloudAlbum application initializer
    :param app: Flask.app
    :return: initialized application
    """
    csrf = CSRFProtect()
    csrf.init_app(app)

    # Regist error handler
    app.register_error_handler(404, errorHandler.not_found)
    app.register_error_handler(405, errorHandler.server_error)
    app.register_error_handler(500, errorHandler.server_error)
    app.register_error_handler(400, errorHandler.csrf_error)

    # CSRF setup for Flask Blueprint module
    userView.blueprint.before_request(csrf.protect)
    siteView.blueprint.before_request(csrf.protect)

    # Regist Flask Blueprint module
    app.register_blueprint(siteView.blueprint, url_prefix='/')
    app.register_blueprint(userView.blueprint, url_prefix='/users')
    app.register_blueprint(photoView.blueprint, url_prefix='/photos')

    # Setup application configuration
    app.secret_key = options['FLASK_SECRET']
    app.config['SQLALCHEMY_DATABASE_URI'] = options['DB_URL']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = options['SQLALCHEMY_TRACK_MODIFICATIONS']
    app.config['SQLALCHEMY_ECHO'] = options['DB_ECHO_FLAG']

    # SQLITE doesn't support DB connection pool
    if 'sqlite' not in options['DB_URL'].lower():
        app.config['SQLALCHEMY_POOL_SIZE'] = options['DB_POOL_SIZE']
        app.config['SQLALCHEMY_MAX_OVERFLOW'] = options['DB_MAX_OVERFLOW']
        app.config['SQLALCHEMY_POOL_TIMEOUT'] = options['DB_SQLALCHEMY_POOL_TIMEOUT']
        app.config['SQLALCHEMY_POOL_RECYCLE'] = options['DB_SQLALCHEMY_POOL_RECYCLE']


    app.jinja_env.globals['url_for_other_page'] = url_for_other_page

    # Logger setup
    app.config['LOGGING_LEVEL'] = get_log_level()
    app.config['LOGGING_FORMAT'] = options['LOGGING_FORMAT']
    app.config['LOGGING_LOCATION'] = options['LOG_FILE_PATH']
    app.config['LOGGING_FILENAME'] = os.path.join(options['LOG_FILE_PATH'], options['LOG_FILE_NAME'])
    app.config['LOGGING_MAX_BYTES'] = options['LOGGING_MAX_BYTES']
    app.config['LOGGING_BACKUP_COUNT'] = options['LOGGING_BACKUP_COUNT']

    util.log_path_check(options['LOG_FILE_PATH'])
    file_handler = RotatingFileHandler(app.config['LOGGING_FILENAME'],
                                       maxBytes=app.config['LOGGING_MAX_BYTES'],
                                       backupCount=app.config['LOGGING_BACKUP_COUNT'])
    file_handler.setFormatter(Formatter(app.config['LOGGING_FORMAT']))
    file_handler.setLevel(app.config['LOGGING_LEVEL'])

    app.logger.addHandler(file_handler)
    app.logger.setLevel(app.config['LOGGING_LEVEL'])
    app.logger.info("logging start")

    # Setup LoginManager
    login.init_app(app)
    login.login_view = 'userView.signin'

    # Setup models for DB operations
    with app.app_context():
        models.db.init_app(app)
        try:
            models.db.create_all()
        except Exception as e:
            app.logger.error(e)
            exit(-1)
    return app


def get_log_level():
    """
    Determine logging level option from config file
    :return: logging level
    """
    level = options['LOGGING_LEVEL']
    if level.lower() is 'info':
        return logging.INFO
    elif level.lower() is 'debug':
        return logging.DEBUG
    elif level.lower() is 'error':
        return logging.ERROR

    elif level.lower() is 'warn':
        return logging.WARN
    else :
        return logging.DEBUG


def url_for_other_page(page):
    """
    Function dor the page navigation.
    :param page: page number.
    :return: target page items.
    """
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


@login.unauthorized_handler
def unauthorized_handler():
    """
    If unauthorized requests are arrived then redirect sign-in URL.
    :return: Redirect sign-in in page
    """
    current_app.logger.info("Unauthorized user need to sign-in")
    return redirect(url_for('userView.signin'))
