# -*- coding: utf-8 -*-
'''
@Time    : 2024/01/11 14:46
@Author  : Daqiao Wang
@File    : handle_request_vars.py
'''

import os
import sys
import pytest
from string import Template
from loguru import logger
import json
from jsonpath import jsonpath
from ast import literal_eval
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
sys.path.append(project_root_dir)
from bases.app_apibase import AppApiBase


def request_url_var_to_str(request_url: str = '', vars_dct: dict = {}) -> str:
    """
    Replaces variables in the request URL with values from vars_dct.

    Args:
        request_url (str): The request URL.
        vars_dct (dict): A dictionary containing variable names as keys and their corresponding values.

    Returns:
        str: The request URL with variables replaced.
    """
    if '${' not in request_url:
        return request_url
    try:
        request_url = Template(request_url).substitute(vars_dct)
    except Exception as err:
        pytest.skip(f'KeyError {err} , because it was not extracted in the previous api\nThe {request_url=}\n{vars_dct=}')
    return request_url


def payload_vars_to_dct(payload_str: str = '', vars_dct: dict = {}) -> dict:
    """
    Replaces variables in a string with corresponding values from a dictionary.
    Args:
        payload_str (str): The string containing variables to be replaced.
        vars_dct (dict): The dictionary containing variable-value mappings.
    Returns:
        dict: The dictionary obtained after replacing variables in the string.
    """
    if not payload_str:
        return None
    if '${' not in payload_str:
        return json.loads(payload_str)
    try:
        string_text: str = Template(payload_str).substitute(vars_dct)
    except Exception as err:
        logger.error(err)
        pytest.skip(f'KeyError {err} , because it was not extracted in the previous api\nThe payload is: {payload_str}\n{vars_dct=}')
        return
    try:
        payload_dict = json.loads(string_text)
    except json.decoder.JSONDecodeError as err:
        logger.error(err)
        logger.error(f'{payload_str=}')
        logger.error(f'{vars_dct=}')
        logger.error(f'{string_text=}')
        try:
            payload_dict = literal_eval(string_text)
        except Exception as err:
            payload_dict = string_text
            logger.error(err)
    finally:
        return payload_dict


def preprocess_send_request(case_data, email=None, password=None, vars_dct=None):
    """
    A function to preprocess the data & sending a HTTP request.
    """
    called_filename = sys._getframe().f_back.f_code.co_filename
    called_py, _ = os.path.splitext(os.path.basename(called_filename))
    called_py_dir = os.path.dirname(called_filename)
    # called_py='test_01_homepage_demo'
    logger.info(f'{called_filename=} {called_py_dir=} {called_py=}')
    # case data pre-process
    request_url = case_data.get('request_url')
    http_method = case_data.get('http_method')
    data_type = case_data.get('data_type')
    params_str = case_data.get('params')
    payload_str = case_data.get('payload')
    upload_file_name = case_data.get('upload_file', None)
    logger.debug(f'{request_url=}')
    logger.debug(f'{http_method=}')
    if upload_file_name:
        upload_file_path = os.path.join(called_py_dir, 'upload_files', upload_file_name)
        files = {'file': (os.path.basename(upload_file_path), open(upload_file_path, 'rb'))}
    else:
        files = None
    # logger.debug(f'{vars_dct=}')
    # request_url
    request_url = request_url_var_to_str(request_url=request_url, vars_dct=vars_dct)
    # params_dict
    params_dict = payload_vars_to_dct(payload_str=params_str, vars_dct=vars_dct)
    logger.debug(f'{params_dict=}')
    # payload_dict
    payload_dict = payload_vars_to_dct(payload_str=payload_str, vars_dct=vars_dct)
    logger.debug(f'{payload_dict=}')
    # http request
    obj = AppApiBase(url=request_url, http_method=http_method, data_type=data_type, params_dict=params_dict,
                     payload_dict=payload_dict, files=files, email=email, password=password)
    request_info: dict = obj.http_request(called_py=called_py)
    request_info.update({'params_dct': params_dict,
                         'payload_dct': payload_dict,
                         }
                        )
    '''
    request_info = {'request_url': '/post/form', 
                    'method': 'POST', 
                    'data_type': 'data', 
                    'params': '{"q": "hello"}',
                    'params_dct': {'q': 'hello'},
                    'payload': '{"name": "John", "age": 19}',
                    'payload_dct': {'name': 'John', 'age': 19},
                    'request_length': 38, 
                    'status_code': 200,
                    'response_data': {'name': 'Jane', 'age': '19', 'message': 'Welcome, you are beautiful.'}, 
                    'response_length': 130, 
                    'response_time': 0.030427,
                    'finish_time': '20240417-18:29:09'}
    '''
    return request_info


def extract_vars(response_data=None, var_extract: str = '', vars_dct: dict | None = None):
    var_extract_dct = json.loads(var_extract)
    for k, v in var_extract_dct.items():
        tmp_lst = jsonpath(response_data, v)
        logger.debug(f'jsonpath get: {tmp_lst=}')
        if tmp_lst:
            vars_dct[k] = tmp_lst[0]
    return vars_dct


class TestSuite:
    def test_01(self):
        reminder_id = [111, 333]
        timsstamp_10days_late = 222
        vars_dct = {'reminder_id': reminder_id, 'timsstamp_10days_late': timsstamp_10days_late}
        data_str = '{"reminderId":${reminder_id},"scheduleTimestamp":${timsstamp_10days_late},"note":"reminder note2"}'
        aa = payload_vars_to_dct(payload_str=data_str, vars_dct=vars_dct)
        logger.debug(f'return {aa}')
        logger.debug(type(aa))
        assert aa == {'reminderId': [111, 333], 'scheduleTimestamp': 222, 'note': 'reminder note2'}

    def test_02(self):
        data_str = '${user_email}'
        vars_dct = {'user_email': 'abcd@aa.info'}
        bb = payload_vars_to_dct(payload_str=data_str, vars_dct=vars_dct)
        # logger.debug(bb)
        logger.debug(f'return {bb}')
        logger.debug(type(bb))
        assert bb == 'abcd@aa.info'

    def test_03(self):
        payload_str = '{"recipients":[{"email":"${mail_receiver}","name":"testmail"}],"message":"somethingoptionalmessage","configuration":"{\\"currentStep\\":2,\\"userId\\":\\"${userId}\\",\\"singleCompany\\":true}}","company":"Microsoft","titles":"JavaDeveloper"}'
        vars_dct = {'userId': 'abcd1234', 'firstname': 'T', 'history_id': 422776, 'mail_receiver': 'cdccdd@ccc.inf'}
        cc = payload_vars_to_dct(payload_str=payload_str, vars_dct=vars_dct)
        # logger.debug(cc)
        logger.debug(f'return {cc}')
        logger.debug(type(cc))

    def test_04(self):
        payload_str = '[]'
        vars_dct = {}
        dd = payload_vars_to_dct(payload_str=payload_str, vars_dct=vars_dct)
        logger.debug(f'return {dd}')
        logger.debug(type(dd))
        assert dd == []

    def test_05(self):
        data_str = '${user_email}'
        vars_dct = {}
        ee = payload_vars_to_dct(payload_str=data_str, vars_dct=vars_dct)
        logger.debug(f'return {ee}')
        logger.debug(type(ee))
        assert ee is None

    def test_06(self):
        vars_dct = {'userId': 'abcd1234', 'firstname': 'T', 'history_id': 422777, 'mail_receiver': 'cdccdd@ccc.inf'}
        url = request_url_var_to_str(request_url='/v1/${history_id}/history', vars_dct=vars_dct)
        logger.debug(f'{url=}')
        assert url == '/v1/422777/history'


if __name__ == '__main__':
    pytest.main(['-s', '-v'])
