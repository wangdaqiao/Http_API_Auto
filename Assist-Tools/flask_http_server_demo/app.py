# -*- coding: utf-8 -*-
'''
@Time    : 2023/8/3 12:55
@Author  : Daqiao Wang
@File    : app.py
'''

import time
import datetime
import os
import random
from flask import Flask, request, render_template, jsonify, flash, abort, make_response
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from loguru import logger

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'upload/'

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/get/json', methods=['GET'])
def get_json():
    name = request.args.get('name')
    age = request.args.get('age')
    if name or age :
        message = f"Welcome {name}, you are {age} years old."
        return jsonify({'message': message, 'path': request.path})
    else:
        return render_template("get_json.html")

@app.route('/get/form', methods=['GET'])
def get_form():
    name = request.args.get('name')
    age = request.args.get('age')
    if name:
        message = f"Welcome {name}, you are {age} years old."
        flash('Good job')
        dct = {"name": name, 'message': message, 'age': age,  "current_time": current_time(), 'path': request.path}
        try:
            dct['age'] = int(age)
        except Exception as err:
            logger.error(f'{err=}')
        return jsonify(dct)
    else:
        return render_template("get_form.html")

@app.route('/post/form', methods=['GET', 'POST'])
def post_form():
    if request.method == 'POST':
        logger.info(f'{request.form=}')
        name = request.form['name']
        age = request.form['age']
        message = f"Welcome {name}, you are {age} years old."
        dct = {"name": name, "age": age, "message": message, 'path': request.path}
        time.sleep(3)
        return jsonify(dct)
    return render_template('post_form.html')


@app.route('/post/json', methods=['GET', 'POST'])
def post_json():
    if request.method == 'POST':
        data = request.get_json()
        logger.info(f'{data=}')
        name = data.get('name')
        age = data.get('age')
        message = f"Welcome {name}, you are {age} old."
        return jsonify({'message': message, 'name': name, 'age': age, 'path': request.path})
    return render_template('post_json.html')

@app.route('/only')
def only():
    dct = {"only": "only you", 'path': request.path}
    return jsonify(dct)

@app.route('/login', methods=['POST',])
def login2():
    dct = {"data": "Ok, Let's do it", 'path': request.path}
    return jsonify(dct)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        logger.info(request.files)
        logger.info(f'{f=}')
        # f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
        dct = {"msg": f'file {f.filename} uploaded successfully', 'path': request.path}
        return jsonify(dct)
    else:
        return render_template('upload.html')

@app.route('/hello/<name>')
def hello_name(name):
    dct = {"name": name, "current_time": current_time(), 'path': request.path}
    return jsonify(dct)

@app.route('/put/user', methods=['GET', 'PUT'])
def update_user():
    if request.method == 'PUT':
        data = request.get_json()
        name = data.get('name')
        age = data.get('age')
        dct = {'name': name,
               'age': age,
               'path': request.path,
               'message': f'User {name} age {age} updated successfully.'}
        time.sleep(3)
        try:
            dct['age'] = int(age)
        except Exception as err:
            logger.error(f'{err=}')
        return jsonify(dct)
    else:
        return render_template('put_user.html')


@app.route('/post/err502', methods=['GET', 'POST'])
def err_502():
    if request.method == 'POST':
        # 返回 502 错误
        # return abort(502)
        return jsonify({'error': 'Internal Server Error 502'}), 502
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

def current_time():
    cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return cur_time

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    