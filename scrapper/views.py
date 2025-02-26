
import hashlib

from http import HTTPStatus as Status
from flask import request, render_template, send_file, send_from_directory
# noinspection PyPackageRequirements
from playwright.sync_api import Error as PlaywrightError

from scrapper import app
from scrapper.settings import USER_SCRIPTS, STATIC_DIR, SCREENSHOT_TYPE
from scrapper.cache import load_result, screenshot_location
from scrapper.util.argutil import default_args, validate_args, check_user_scrips
from scrapper.core import ParserError
from scrapper.core.article import scrape as scrape_article
from scrapper.core.links import scrape as scrape_links


def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PlaywrightError as err:
            message = err.message.splitlines()[0]
            return {'err': [f'Playwright: {message}']}, Status.INTERNAL_SERVER_ERROR
        except ParserError as err:
            return err.err, Status.INTERNAL_SERVER_ERROR
    wrapper.__name__ = func.__name__
    return wrapper


@app.route('/', methods=['GET'])
@app.route('/links', methods=['GET'])
def index():
    args = list(default_args())
    placeholder = '&#10;'.join((f'{x[0]}={x[1]}' for x in args[:10]))  # max 10 args
    placeholder = placeholder.replace('=True', '=yes').replace('=False', '=no')
    return render_template('index.html', context={'placeholder': placeholder, 'linksRoute': '/links' == request.path})


@app.route('/favicon.ico')
def favicon():
    # https://flask.palletsprojects.com/en/1.1.x/patterns/favicon/
    d = STATIC_DIR / 'icons'
    return send_from_directory(d, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/view/<string:id>', methods=['GET'])
def result_html(id):
    data = load_result(id)
    return render_template('view.html', data=data) if data else ('Not found', Status.NOT_FOUND)


@app.route('/result/<string:id>', methods=['GET'])
def result_json(id):
    data = load_result(id)
    return data if data else ('Not found', Status.NOT_FOUND)


@app.route('/screenshot/<string:id>', methods=['GET'])
def result_screenshot(id):
    path = screenshot_location(id)
    if not path.exists():
        return 'Not found', Status.NOT_FOUND
    return send_file(path, mimetype=f'image/{SCREENSHOT_TYPE}')


@app.route('/parse', methods=['GET'])   # DEPRECATED
@app.route('/api/article', methods=['GET'])
@exception_handler
def article():
    args, err = validate_args(args=request.args)
    check_user_scrips(args=args, user_scripts_dir=USER_SCRIPTS, err=err)
    if err:
        return {'err': err}, Status.BAD_REQUEST

    _id = hashlib.sha1(request.full_path.encode()).hexdigest()  # unique request id

    # get cache data if exists
    if args.cache is True:
        data = load_result(_id)
        if data:
            return data

    return scrape_article(request=request, args=args, _id=_id)


@app.route('/api/links', methods=['GET'])
@exception_handler
def links():
    args, err = validate_args(args=request.args)
    check_user_scrips(args=args, user_scripts_dir=USER_SCRIPTS, err=err)
    if err:
        return {'err': err}, Status.BAD_REQUEST

    _id = hashlib.sha1(request.full_path.encode()).hexdigest()  # unique request id

    # get cache data if exists
    if args.cache is True:
        data = load_result(_id)
        if data:
            return data

    return scrape_links(request=request, args=args, _id=_id)


def startup():
    pass
