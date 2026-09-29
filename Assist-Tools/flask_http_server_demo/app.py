# -*- coding: utf-8 -*-
"""
@Time    : 2023/8/3 12:55
@Author  : Daqiao Wang
@File    : app.py
"""

import time
import datetime
import os
import secrets
from flask import Flask, request, render_template, jsonify, make_response, session
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from loguru import logger

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.json.ensure_ascii = False

app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)

# Add, remove, or update users here for this demo application.
LEGAL_USERS = {
    'admin': 'admin123',
    'tester': 'tester123',
}

# Use absolute path for upload folder
upload_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'upload')
app.config['UPLOAD_FOLDER'] = upload_dir
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)

@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/v1/get/json', methods=['GET'])
@app.route('/get/json', methods=['GET'])
def get_json():
    if 'name' in request.args or 'age' in request.args:
        name = request.args.get('name', '')
        age = request.args.get('age', '')
        message = f"Welcome {name}, you are {age} years old."
        return jsonify({'message': message, 'path': request.path, "current_time": current_time()})
    elif request.path.startswith('/v1/'):
        return jsonify({'message': 'Welcome, you are unknown years old.', 'path': request.path, "current_time": current_time()})
    else:
        return render_template("get_json.html")

@app.route('/v1/get/form', methods=['GET'])
@app.route('/get/form', methods=['GET'])
def get_form():
    if 'name' in request.args or 'age' in request.args:
        name = request.args.get('name', '')
        age = request.args.get('age', '')
        message = f"Welcome {name}, you are {age} years old."
        dct = {"name": name,
               'message': message,
               'age': age,
               "current_time": current_time(),
               'path': request.path}
        if age:
            try:
                dct['age'] = int(age)
            except (ValueError, TypeError):
                return jsonify({'error': 'Age must be an integer',
                                'path': request.path,
                                "current_time": current_time()}
                               ), 400
        return jsonify(dct)
    elif request.path.startswith('/v1/'):
        return jsonify({"name": "", 'message': "Welcome", 'age': None, "current_time": current_time(), 'path': request.path})
    else:
        return render_template("get_form.html")

@app.route('/v1/post/form', methods=['GET', 'POST'])
@app.route('/post/form', methods=['GET'])
def post_form():
    if request.method == 'POST':
        logger.info(f'{request.form=}')
        name = request.form.get('name')
        age = request.form.get('age')
        message = f'Welcome {name}, you are {age} years old.'
        dct = {"name": name, "age": age, "message": message, "current_time": current_time(), 'path': request.path}
        time.sleep(0.2)
        return jsonify(dct)
    return render_template('post_form.html')

@app.route('/v1/post/json', methods=['GET', 'POST'])
@app.route('/post/json', methods=['GET'])
def post_json():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid JSON payload, object expected'}), 400
        logger.info(f'{data=}')
        name = data.get('name')
        age = data.get('age')
        message = f'Welcome {name}, you are {age} years old.'
        time.sleep(0.2)
        return jsonify({'message': message, 'name': name, 'age': age, 'path': request.path, "current_time": current_time()})
    return render_template('post_json.html')

@app.route('/v1/only', methods=['GET'])
def only():
    dct = {
        "only": "only you",
        'path': request.path,
        "current_time": current_time(),
        "params": request.args.to_dict(),
    }
    return jsonify(dct)

@app.route('/v1/users/login', methods=['GET', 'POST'])
@app.route('/users/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'GET':
        return render_template(
            'login.html',
            username=session.get('username'),
            csrf_token=session.get('csrf-token'),
        )

    data = request.get_json(silent=True) if request.is_json else request.form
    if not isinstance(data, dict) and not hasattr(data, 'get'):
        data = {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({
            'error': 'Username and password are required',
            'path': request.path,
            "current_time": current_time(),
        }), 400
    if LEGAL_USERS.get(username) != password:
        return jsonify({
            'error': 'Invalid username or password',
            'path': request.path,
            "current_time": current_time(),
        }), 401

    csrf_token = secrets.token_urlsafe(32)
    session.permanent = True
    session['username'] = username
    session['csrf-token'] = csrf_token
    response = jsonify({
        'data': f"Welcome {username}, Let's do it",
        'username': username,
        'csrf-token': csrf_token,
        "current_time": current_time(),
        'path': request.path,
    })
    response.headers['csrf-token'] = csrf_token
    return response

@app.route('/v1/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully', 'path': request.path, "current_time": current_time()})

@app.route('/v1/userInfo', methods=['GET'])
def user_info():
    username = session.get('username')
    if not username:
        return jsonify({
            'logged_in': False,
            'message': 'User is not logged in',
            'path': request.path,
            "current_time": current_time()
        }), 401

    return jsonify({
        'logged_in': True,
        'username': username,
        'message': f'Welcome {username}',
        'path': request.path,
        "current_time": current_time()
    })

@app.route('/v1/upload', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        f = request.files['file']
        if f.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        logger.info(request.files)
        logger.info(f'{f=}')
        # Save the file
        filename = secure_filename(f.filename)
        # f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        dct = {"msg": f'file {filename} uploaded successfully', 'path': request.path, "current_time": current_time(),}
        return jsonify(dct)
    else:
        return render_template('upload_file.html')

@app.route('/v1/hello/<name>')
def hello_name(name):
    dct = {"name": name, "current_time": current_time(), 'path': request.path}
    return jsonify(dct)

@app.route('/v1/put/user', methods=['GET', 'PUT'])
@app.route('/put/user', methods=['GET'])
def update_user():
    if request.method == 'PUT':
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid JSON payload, object expected'}), 400
        name = data.get('name')
        age = data.get('age')
        dct = {'name': name,
               'age': age,
               'path': request.path,
               "current_time": current_time(),
               'message': f'User {name} age {age} updated successfully.'}
        time.sleep(0.2)
        if age is not None and age != '':
            try:
                dct['age'] = int(age)
            except (ValueError, TypeError):
                return jsonify({'error': 'Age must be an integer', 'path': request.path, "current_time": current_time()}), 400
        return jsonify(dct)
    else:
        return render_template('put_user.html')

@app.route('/v1/post/err502', methods=['GET', 'POST'])
@app.route('/post/err502', methods=['GET'])
def err_502():
    if request.method == 'POST':
        # 返回 502 错误
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid JSON payload, object expected'}), 400
        name = data.get('name')
        return jsonify({'name': name,
                        'error': 'Internal Server Error 502',
                        "current_time": current_time(),
                        }), 502
    else:
        # 返回一个简单的表单页面
        return render_template('post_json_502.html')


@app.route("/v1/cookie", methods=["GET", "POST"])
@app.route("/cookie", methods=["GET", "POST"])
def cookie_api():
    """
    - POST：写入一个 Cookie，返回 JSON；
      支持 application/json、application/x-www-form-urlencoded、multipart/form-data
      三种请求体格式（JSON 用 key/value 字段，表单用同名字段）；
    - GET：浏览器直接访问（Accept 含 text/html）返回演示页面；
           携带 Accept: application/json（或未声明 text/html）时返回 JSON 列表。
    说明：不会额外写入 app_keys 之类的元 Cookie，浏览器后续请求的
    Cookie 头中只包含演示写入的 key=value。
    """
    if request.method == "POST":
        if request.is_json:
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                payload = {}
            raw_key = payload.get("key")
            raw_value = payload.get("value")
            key = str(raw_key).strip() if raw_key is not None else ""
            value = str(raw_value).strip() if raw_value is not None else ""
        else:
            raw_key = request.form.get("key")
            raw_value = request.form.get("value")
            key = str(raw_key).strip() if raw_key is not None else ""
            value = str(raw_value).strip() if raw_value is not None else ""

        if not key:
            return jsonify({"ok": False, "message": "key 不能为空", "operation": "add",
                            "cookies": dict(request.cookies),
                            "count": len(request.cookies),
                            "current_time": current_time(),}), 400

        cookies = dict(request.cookies)
        cookies[key] = value

        resp = make_response(jsonify({
            "ok": True,
            "message": f"Cookie 写入成功: {key}={value}",
            "operation": "add",
            "key": key,
            "value": value,
            "cookies": cookies,
            "count": len(cookies),
            "current_time": current_time(),
        }))
        resp.set_cookie(key, value, max_age=60 * 60 * 24 * 7)
        return resp

    # GET：浏览器直接访问 -> 演示页面；API 请求 -> JSON
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        return render_template("cookie.html")

    cookies = dict(request.cookies)
    return jsonify({"ok": True,
                    "operation": "list",
                    "message": f"当前共 {len(cookies)} 个 Cookie" if cookies else "暂无 Cookie",
                    "cookies": cookies,
                    "count": len(cookies),
                    "current_time": current_time()})


@app.route("/v1/clear_cookie", methods=["POST"])
def clear_cookie():
    """清除浏览器当前携带的全部 Cookie（保留 session 避免误退出），返回 JSON"""
    session_cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
    keys = [k for k in request.cookies.keys() if k != session_cookie_name]
    resp = make_response(jsonify({
        "ok": True,
        "operation": "clear",
        "message": "已清除本站点全部 Cookie" if keys else "当前没有需要清除的 Cookie",
        "cookies": {session_cookie_name: request.cookies.get(session_cookie_name)} if session_cookie_name in request.cookies else {},
        "count": 0,
        "current_time": current_time(),
    }))
    for k in keys:
        resp.delete_cookie(k)
    return resp



@app.errorhandler(404)
def handle_404(error):
    """未注册的路由统一返回 404"""
    logger.warning(f'404 Not Found: {request.method} {request.path}')
    return jsonify({
        'error': 'Not Found',
        'code': 404,
        'path': request.path,
        'method': request.method,
        'current_time': current_time(),
        'message': f'Route "{request.path}" is not registered.',
    }), 404


@app.errorhandler(405)
def handle_405(error):
    """请求方法不被该路由允许时统一返回 JSON（含允许的方法列表）"""
    allowed = sorted(getattr(error, 'valid_methods', None) or [])
    logger.warning(f'405 Method Not Allowed: {request.method} {request.path} -> {allowed}')
    return jsonify({
        'error': 'Method Not Allowed',
        'code': 405,
        'path': request.path,
        'method': request.method,
        'allowed_methods': allowed,
        'current_time': current_time(),
        'message': f'Method "{request.method}" is not allowed for route "{request.path}".',
    }), 405


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    """其余 HTTP 异常（400/415/500 等）统一返回 JSON，避免 API 客户端收到 HTML 错误页"""
    code = error.code or 500
    logger.warning(f'{code} {error.name}: {request.method} {request.path}')
    return jsonify({
        'error': error.name,
        'code': code,
        'path': request.path,
        'method': request.method,
        'current_time': current_time(),
        'message': error.description or f'{error.name} occurred.',
    }), code


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """未捕获异常统一返回 JSON 500，不向调用方泄露堆栈细节"""
    logger.exception(f'Unhandled error: {request.method} {request.path}')
    return jsonify({
        'error': 'Internal Server Error',
        'code': 500,
        'path': request.path,
        'method': request.method,
        'current_time': current_time(),
        'message': 'An unexpected error occurred.',
    }), 500


def current_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
