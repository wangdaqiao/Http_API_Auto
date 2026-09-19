# -*- coding: utf-8 -*-
"""
@Time    : 2023/8/3 12:55
@Author  : Daqiao Wang
@File    : app.py
"""

import time
import datetime
import os
from flask import Flask, request, render_template, jsonify, flash, make_response
from werkzeug.utils import secure_filename
from loguru import logger

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Use absolute path for upload folder
upload_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'upload')
app.config['UPLOAD_FOLDER'] = upload_dir
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/v1/get/json', methods=['GET'])
def get_json():
    name = request.args.get('name')
    age = request.args.get('age')
    if name or age:
        message = f"Welcome {name}, you are {age} years old."
        return jsonify({'message': message, 'path': request.path})
    else:
        return render_template("get_json.html")

@app.route('/v1/get/form', methods=['GET'])
def get_form():
    name = request.args.get('name')
    age = request.args.get('age')
    if name:
        message = f"Welcome {name}, you are {age} years old."
        flash('Good job')
        dct = {"name": name, 'message': message, 'age': age,  "current_time": current_time(), 'path': request.path}
        try:
            dct['age'] = int(age)
        except (ValueError, TypeError) as err:
            logger.error(f'{err=}')
        return jsonify(dct)
    else:
        return render_template("get_form.html")

@app.route('/v1/post/form', methods=['GET', 'POST'])
def post_form():
    if request.method == 'POST':
        logger.info(f'{request.form=}')
        name = request.form.get('name')
        age = request.form.get('age')
        message = f'Welcome {name}, you are {age} old, path="{request.path}"'
        dct = {"name": name, "age": age, "message": message, 'path': request.path}
        time.sleep(1)
        return jsonify(dct)
    return render_template('post_form.html')

@app.route('/v1/post/json', methods=['GET', 'POST'])
def post_json():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        logger.info(f'{data=}')
        name = data.get('name')
        age = data.get('age')
        message = f'Welcome {name}, you are {age} old, path="{request.path}"'
        time.sleep(1)
        return jsonify({'message': message, 'name': name, 'age': age, 'path': request.path})
    return render_template('post_json.html')

@app.route('/v1/only')
def only():
    dct = {"only": "only you", 'path': request.path}
    return jsonify(dct)

@app.route('/v1/login', methods=['POST',])
def login2():
    dct = {"data": "Ok, Let's do it", 'path': request.path}
    return jsonify(dct)

@app.route('/v1/upload', methods=['GET', 'POST'])
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
        dct = {"msg": f'file {filename} uploaded successfully', 'path': request.path}
        return jsonify(dct)
    else:
        return render_template('upload.html')

@app.route('/v1/hello/<name>')
def hello_name(name):
    dct = {"name": name, "current_time": current_time(), 'path': request.path}
    return jsonify(dct)

@app.route('/v1/put/user', methods=['GET', 'PUT'])
def update_user():
    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        name = data.get('name')
        age = data.get('age')
        dct = {'name': name,
               'age': age,
               'path': request.path,
               'message': f'User {name} age {age} updated successfully.'}
        time.sleep(1)
        try:
            dct['age'] = int(age)
        except (ValueError, TypeError) as err:
            logger.error(f'{err=}')
        return jsonify(dct)
    else:
        return render_template('put_user.html')

@app.route('/v1/post/err502', methods=['GET', 'POST'])
def err_502():
    if request.method == 'POST':
        # 返回 502 错误
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        name = data.get('name')
        return jsonify({'name': name, 'error': f'Internal Server Error 502'}), 502
    else:
        # 返回一个简单的表单页面
        return render_template('post_json_502.html')


@app.route('/v1/users/login', methods=['POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        logger.info(f'{data=}')
        email = data.get('email')
        dct = {'message': f"Welcome {email}", 'email': email, 'path': request.path}
        if 'admin' in email:
            dct['role'] = 'admin'
        else:
            dct['role'] = 'user'
        rsp = make_response(dct)
        rsp.headers['Authorization'] = 'your test token'
        rsp.set_cookie('csrf-token', f'{email}_csrf_token')
        return rsp
    else:
        return render_template('index.html')

@app.route("/v1/cookie", methods=["GET", "POST"])
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
            payload = request.get_json(silent=True) or {}
            key = str(payload.get("key", "")).strip()
            value = str(payload.get("value", "")).strip()
        else:
            key = request.form.get("key", "").strip()
            value = request.form.get("value", "").strip()

        if not key:
            return jsonify({"ok": False, "message": "key 不能为空", "operation": "add",
                            "cookies": dict(request.cookies),
                            "count": len(request.cookies)}), 400

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
                    "count": len(cookies)})


@app.route("/v1/clear_cookie", methods=["POST"])
def clear_cookie():
    """清除浏览器当前携带的全部 Cookie（对每个 Cookie 下发过期），返回 JSON"""
    keys = list(request.cookies.keys())
    resp = make_response(jsonify({
        "ok": True,
        "operation": "clear",
        "message": "已清除本站点全部 Cookie" if keys else "当前没有需要清除的 Cookie",
        "cookies": {},
        "count": 0,
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


def current_time():
    cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return cur_time

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
