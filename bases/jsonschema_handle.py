#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
from pprint import pprint
import os
import time
from jsonschema import validate, SchemaError, ValidationError
from loguru import logger
from urllib import parse
import json
import allure

cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
json_schema_files_dir = os.path.join(project_root_dir, 'cases', 'jsonfiles')


# logger.debug(f'{json_schema_files_dir=}')


def file_from_dir(root_dir=cur_dir, filename='') -> str | None:
    """
    Given a root directory and a filename, searches for the file in the specified directory and its subdirectories.

    Args:
        root_dir (str): The root directory to start the search from. Defaults to the current working directory.
        filename (str): The name of the file to search for.

    Returns:
        str: The absolute path of the file if found.
        None: If the root directory is not a directory.
    """
    if os.path.isdir(root_dir):
        for root, dirs, files in os.walk(root_dir, topdown=True):
            for name in files:
                if name == filename:
                    return os.path.join(root, name)
    else:
        logger.warning(f'{root_dir} is not a directory.')
        return


def schema_from_jsonfile(json_schema_file_name) -> dict:
    """
    Retrieve the schema from a JSON file.

    Args:
        json_schema_file_name (str): The name of the JSON schema file.

    Returns:
        dict: The loaded schema if the file exists and can be loaded, None otherwise.
    """
    json_schema_file_fullpath = file_from_dir(json_schema_files_dir, json_schema_file_name)
    logger.debug(f'{json_schema_file_fullpath=}')
    if not json_schema_file_fullpath:
        logger.error(f'{json_schema_file_name} file is not exists')
        return {}
    try:
        with open(json_schema_file_fullpath, encoding='utf-8') as fr:
            schema = json.load(fr)
    except Exception as err:
        logger.error(err)
        schema = {}
    finally:
        return schema


def jsonschema_validate(response_data=None, schema: dict = None, request_info: dict = None) -> bool:
    check_result = False
    if request_info:
        params_dict: dict = request_info.get('params_dct')
        payload_dict: dict = request_info.get('payload_dct')
        payload_str: str = request_info.get('payload')
    else:
        params_dict = None
        payload_dict = None
        payload_str = None
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except Exception as err:
            logger.error(err)
    msg = ''
    try:
        validate(response_data, schema)
    except SchemaError as err:
        msg += "schema error：\n：Error Location: {}\n".format(" --> ".join(str(x) for x in err.path))
        msg += "prompt msg：{}".format(err.message)
    except ValidationError as err:
        msg += "json data schema validation failure：\n"
        msg += "Error Fields：{}\n".format(" --> ".join(str(x) for x in err.path))
        msg += "prompt msg：{}".format(err.message)
    else:
        msg += 'Success!'
        check_result = True
    finally:
        if request_info:
            # allure.attach(f'{request_info.get("request_url")} {request_info.get("method")}', "request url & method")
            msg += f'\n---------------\nrequest_url: {request_info.get("request_url")}'
            msg += f'\n---------------\nmethod: {request_info.get("method")}'
            msg += f'\n---------------\ndata_type: {request_info.get("data_type")}'
            msg += f'\n---------------\nstatus_code: {request_info.get("status_code")}'
        msg += f'\n---------------\nparams_dict: {params_dict}'
        if params_dict:
            params_urlencode = parse.urlencode(params_dict, doseq=True)
            msg += f'\n---------------\nparams_urlencode: ?{params_urlencode}'
        msg += f'\n---------------\npayload_dict: {payload_dict}'
        if payload_str:
            msg += f'\n---------------\npayload_str: {payload_str}'
        if request_info and 'error_request' in request_info:
            msg += f'\n---------------\nerror_request: {request_info.get("error_request")}'
        else:
            msg += f'\n---------------\nresponse_data: {response_data}'
        msg += f'\n---------------\njson_schema: {schema}'
        if request_info:
            msg += f'\n---------------\nresponse_time: {request_info.get("response_time")}'
            msg += f'\n---------------\nfinish_time: {request_info.get("finish_time")}'
        # logger.debug(f'{msg=}')
        if check_result:
            allure.attach(f"{msg}", "jsonschema validate success msg")
        else:
            allure.attach(f"{msg}", "jsonschema validate failure msg")
        return check_result


if __name__ == '__main__':
    # schema: dict = schema_from_jsonfile('_get_form_GET_200.json')
    # pprint(schema)
    data_main = {}
    schema = {}
    result = jsonschema_validate(response_data=data_main, schema=schema)
    logger.debug(result)
