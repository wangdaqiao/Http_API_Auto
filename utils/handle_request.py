# -*- coding: utf-8 -*-
'''
@Time    : 2024/01/11 14:46
@Author  : Daqiao Wang
@File    : handle_request.py
'''

import os
import sys
import pytest
from string import Template
from typing import Any
from loguru import logger
import json
from jsonpath import jsonpath
from ast import literal_eval
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
sys.path.append(project_root_dir)
from bases.app_apibase import AppApiBase


# 日志里打印外部数据时的最大长度，避免把长响应体/大变量字典整段刷进日志文件
LOG_PREVIEW_LIMIT = 300


def _preview(obj) -> str:
    """Return a truncated string of obj for logging."""
    text = str(obj)
    return text if len(text) <= LOG_PREVIEW_LIMIT else text[:LOG_PREVIEW_LIMIT] + '...(truncated)'


class UnresolvedVariableError(KeyError):
    """${var} 占位符在 vars_dct 中找不到对应值时抛出（即上游接口没有提取到该变量）。"""

    def __str__(self):
        return ', '.join(str(x) for x in self.args)


def _substitute(text: str, vars_dct: dict) -> str:
    """
    Substitute ${var} placeholders in text with the values from vars_dct.

    Raises:
        UnresolvedVariableError: any placeholder has no matching key in vars_dct,
            or the placeholder itself is malformed (e.g. '${}').
    """
    try:
        return Template(text).substitute(vars_dct)
    except (KeyError, ValueError) as err:
        # 只包装"变量缺失 / 占位符非法"这两类预期错误。
        # 其它异常（例如 vars_dct 误传成 None 的 TypeError）应原样抛出，
        # 不能被伪装成"变量缺失"后 skip 掉，否则排查方向会被带偏。
        raise UnresolvedVariableError(str(err)) from err


def request_url_var_to_str(request_url: str = '', vars_dct: dict | None = None) -> str:
    """
    Replaces variables(${var}) in the request URL with values from vars_dct.

    Args:
        request_url (str): The request URL, may contain ${var} placeholders.
        vars_dct (dict): A dictionary containing variable names as keys and their corresponding values.

    Returns:
        str: The request URL with variables replaced.

    Raises:
        pytest.skip.Exception: skipped when any ${var} was not extracted by a previous api.
    """
    # 不要用可变对象 {} 做默认参数；vars_dct 为 None 时兜底，
    # 否则 Template.substitute(None) 抛 TypeError，会被误报成"缺少变量"。
    vars_dct = vars_dct or {}
    if not request_url or '${' not in request_url:
        return request_url
    try:
        return _substitute(request_url, vars_dct)
    except UnresolvedVariableError as err:
        # 只打印变量名，不打印 vars_dct 内容（可能含 token/密码等敏感信息）
        pytest.skip(f'{err} , because it was not extracted in the previous api\n'
                    f'The request_url is: {request_url}\n available var names: {list(vars_dct)}')


def str_vars_to_obj(text: str = '', vars_dct: dict | None = None) -> Any:
    """
    Replaces ${var} variables in a string with values from vars_dct, then parses it into a python object.
    params 与 payload 在 csv 里都是字符串，两者共用这个函数。

    Args:
        text (str): The string containing ${var} placeholders (json/list/scalar literal, or plain text).
        vars_dct (dict): The dictionary containing variable-value mappings.

    Returns:
        Any: 解析结果，取决于 text 的内容，可能是 dict / list / str / int 等；
             text 为空时返回 None；两种解析都失败时原样返回替换后的字符串。

    Raises:
        pytest.skip.Exception: skipped when any ${var} was not extracted by a previous api.
    """
    if not text:
        return None
    vars_dct = vars_dct or {}
    if '${' in text:
        try:
            string_text: str = _substitute(text, vars_dct)
        except UnresolvedVariableError as err:
            logger.error(err)
            pytest.skip(f'{err} , because it was not extracted in the previous api\n'
                        f'The string is: {text}\n available var names: {list(vars_dct)}')
    else:
        string_text = text
    try:
        return json.loads(string_text)
    except json.decoder.JSONDecodeError as err:
        # json.loads 失败不代表数据有误（可能是 Python 字面量如单引号 dict），降级继续尝试。
        logger.error(f'json.loads failed: {err}, try literal_eval instead. {text=} {string_text=}')
    try:
        return literal_eval(string_text)
    except (ValueError, SyntaxError, TypeError) as err:
        logger.error(f'literal_eval failed too: {err}, return the raw string.')
        return string_text


def preprocess_send_request(case_data, email=None, password=None, vars_dct=None,
                            caller_file: str | None = None) -> dict:
    """
    Preprocess a case(dict built from csv): substitute ${var}, parse params/payload, then send the HTTP request.

    Args:
        case_data (dict): one case dict, see utils/csv_parse.csv_to_cases.
        email/password: override the account from config/config.yaml.
        vars_dct (dict): variables extracted by previous apis, used for ${var} substitution.
        caller_file: 调用方文件名，用于定位 upload_files 目录和命名录制 csv。
            默认为 None 时从调用栈取；若调用链被装饰器/中间层包了一层就容易取错，
            这种情况下请显式传入 __file__。

    Returns:
        dict: request_info from AppApiBase.http_request(), merged with 'params_dct' & 'payload_dct'.
    """
    if caller_file:
        called_filename = caller_file
    else:
        # 依赖调用方栈帧：这是 CPython 私有 API 且对调用层级敏感，必要时用 caller_file 兜底
        called_filename = sys._getframe().f_back.f_code.co_filename
    called_py, _ = os.path.splitext(os.path.basename(called_filename))
    called_py_dir = os.path.dirname(called_filename)
    # called_py='test_01_homepage_demo'
    logger.info(f'{called_filename=} {called_py_dir=} {called_py=}')
    # vars_dct 允许缺省，Nones 兜底避免 Template.substitute(None) 抛 TypeError 再被误报成"缺少变量"
    vars_dct = vars_dct or {}
    # case data pre-process
    request_url = case_data.get('request_url')
    http_method = case_data.get('http_method')
    data_type = case_data.get('data_type')
    params_str = case_data.get('params')
    payload_str = case_data.get('payload')
    upload_file_name = case_data.get('upload_file', None)
    logger.debug(f'{request_url=}')
    logger.debug(f'{http_method=}')
    upload_file_path = None
    if upload_file_name:
        upload_file_path = os.path.join(called_py_dir, 'upload_files', upload_file_name)
        if not os.path.isfile(upload_file_path):
            # 提前给出明确结论，避免最后抛出无上下文的 FileNotFoundError
            pytest.fail(f'upload file does not exist: {upload_file_path}, '
                        f'case request_url: {request_url}, please check the upload_file column.')
    # request_url
    request_url = request_url_var_to_str(request_url=request_url, vars_dct=vars_dct)
    # params_dict
    params_dict = str_vars_to_obj(text=params_str, vars_dct=vars_dct)
    logger.debug(f'{params_dict=}')
    # payload_dict
    payload_dict = str_vars_to_obj(text=payload_str, vars_dct=vars_dct)
    logger.debug(f'{payload_dict=}')
    # http request
    # open the upload file right before sending, and make sure it is always closed after the
    # request, so no file handle is leaked.
    upload_file_handler = None
    try:
        files = None
        if upload_file_path:
            upload_file_handler = open(upload_file_path, 'rb')
            files = {'file': (os.path.basename(upload_file_path), upload_file_handler)}
        obj = AppApiBase(url=request_url, http_method=http_method, data_type=data_type, params_dict=params_dict,
                         payload_dict=payload_dict, files=files, email=email, password=password)
        request_info: dict = obj.http_request(called_py=called_py)
    finally:
        if upload_file_handler:
            upload_file_handler.close()
    request_info.update({'params_dct': params_dict,
                         'payload_dct': payload_dict,
                         }
                        )
    # request_info 结构示例：
    # {'request_url': '/v1/post/form', 'method': 'POST', 'data_type': 'data',
    #  'params': '{"q": "hello"}', 'params_dct': {'q': 'hello'},
    #  'payload': '{"name": "John", "age": 19}', 'payload_dct': {'name': 'John', 'age': 19},
    #  'request_length': 38, 'status_code': 200,
    #  'response_data': {'name': 'Jane', 'age': '19', 'message': 'Welcome, you are beautiful.'},
    #  'response_length': 130, 'response_time': 0.030427, 'finish_time': '20240417-18:29:09'}
    return request_info


def extract_vars(response_data=None, var_extract: str = '', vars_dct: dict | None = None) -> dict:
    """
    Extract variables from response_data with jsonpath expressions, and merge them into vars_dct.

    Args:
        response_data: the response json object to extract from.
        var_extract (str): json string like '{"name": "$..name"}', key is the variable name,
            value is the jsonpath expression.
        vars_dct (dict): variables dict to merge into; 缺省时新建, 该函数同时会把它返回回去
            (注意是原地修改，调用方不需要再 update 一次)。

    Returns:
        dict: vars_dct itself, updated with the extracted variables.
    """
    vars_dct = {} if vars_dct is None else vars_dct
    if not var_extract:
        return vars_dct
    try:
        var_extract_dct = json.loads(var_extract)
    except json.JSONDecodeError as err:
        # var_extract 是 csv 里手写的，写错要让用例明确失败并保留上下文，而不是抛裸异常
        pytest.fail(f'invalid var_extract: {var_extract}, json.loads failed: {err}')
        return vars_dct
    for k, v in var_extract_dct.items():
        # jsonpath 在无匹配 / response_data 为 None / 表达式非法时都返回 False，不会抛异常
        tmp_lst = jsonpath(response_data, v)
        if not tmp_lst:
            # 之前是静默跳过，导致下游用例以"变量未提取"被 skip 而无法定位是哪一步没提取到
            logger.warning(f'jsonpath {v!r} matched nothing, variable {k!r} not extracted. '
                           f'response_data: {_preview(response_data)}')
            continue
        logger.debug(f'jsonpath get: {k}={tmp_lst[0]}')
        vars_dct[k] = tmp_lst[0]
    return vars_dct


class TestSuite:
    def test_01(self):
        reminder_id = [111, 333]
        timsstamp_10days_late = 222
        vars_dct = {'reminder_id': reminder_id, 'timsstamp_10days_late': timsstamp_10days_late}
        data_str = '{"reminderId":${reminder_id},"scheduleTimestamp":${timsstamp_10days_late},"note":"reminder note2"}'
        aa = str_vars_to_obj(text=data_str, vars_dct=vars_dct)
        logger.debug(f'return {aa}')
        logger.debug(type(aa))
        assert aa == {'reminderId': [111, 333], 'scheduleTimestamp': 222, 'note': 'reminder note2'}

    def test_02(self):
        data_str = '${user_email}'
        vars_dct = {'user_email': 'abcd@aa.info'}
        bb = str_vars_to_obj(text=data_str, vars_dct=vars_dct)
        # logger.debug(bb)
        logger.debug(f'return {bb}')
        logger.debug(type(bb))
        assert bb == 'abcd@aa.info'

    def test_03(self):
        payload_str = '{"recipients":[{"email":"${mail_receiver}","name":"testmail"}],"message":"somethingoptionalmessage","configuration":"{\\"currentStep\\":2,\\"userId\\":\\"${userId}\\",\\"singleCompany\\":true}}","company":"Microsoft","titles":"JavaDeveloper"}'
        vars_dct = {'userId': 'abcd1234', 'firstname': 'T', 'history_id': 422776, 'mail_receiver': 'cdccdd@ccc.inf'}
        cc = str_vars_to_obj(text=payload_str, vars_dct=vars_dct)
        # logger.debug(cc)
        logger.debug(f'return {cc}')
        logger.debug(type(cc))

    def test_04(self):
        payload_str = '[]'
        vars_dct = {}
        dd = str_vars_to_obj(text=payload_str, vars_dct=vars_dct)
        logger.debug(f'return {dd}')
        logger.debug(type(dd))
        assert dd == []

    def test_05(self):
        data_str = '${not_exist_email}'
        vars_dct = {}
        ee = str_vars_to_obj(text=data_str, vars_dct=vars_dct)
        logger.debug(f'return {ee}')
        logger.debug(type(ee))
        assert ee is None

    def test_06(self):
        vars_dct = {'userId': 'abcd1234', 'firstname': 'T', 'history_id': 422777, 'mail_receiver': 'cdccdd@ccc.inf'}
        url = request_url_var_to_str(request_url='/v1/${history_id}/history', vars_dct=vars_dct)
        logger.debug(f'{url=}')
        assert url == '/v1/422777/history'


if __name__ == '__main__':
    pytest.main(['-s', '-v', __file__])
