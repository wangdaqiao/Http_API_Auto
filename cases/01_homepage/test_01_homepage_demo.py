#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
@Project ：Http_API_Automation_PY3
@File    ：test_01_homepage.py
@Author  ：Daqiao Wang
@Date    ：2021/3/1
"""

import os
import sys
import time
import pytest
import json
from jsonpath import jsonpath
from loguru import logger
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(os.path.dirname(cur_dir))
sys.path.append(project_root_dir)
from bases.jsonschema_handle import schema_from_jsonfile, jsonschema_validate
from utils import csv_parse
from utils import common_funs
from utils import handle_request
from config import base_config


email = base_config.email
password = base_config.password

date_hour_minute_str = base_config.date_hour_minute_str
cur_filename, _ = os.path.splitext(os.path.basename(__file__))
logfile = os.path.join(base_config.logs_dir, f'API_{date_hour_minute_str}_{cur_filename}.log')
csv_lst = [x for x in os.listdir(cur_dir) if x.endswith('.csv')]
# csv_lst = ['01_homepage_demo.csv', ]
logger.debug(f'{csv_lst=}')
data_total = list()
for csv_file in csv_lst:
    case_lst = csv_parse.csv_to_cases(csvfile_input=os.path.join(cur_dir, csv_file), email=email)
    data_total.extend(case_lst)
logger.debug(f'case number: {len(data_total)}')
# logger.info(f'{data_total=}')
case_ids = common_funs.case_ids_define(data_total)
vars_dct = {}


def setup_module():
    vars_dct['t1'] = time.time()
    # logger.remove()
    logger.add(logfile, level="INFO", enqueue=True)
    logger.info('setup_module starts.')


def teardown_module():
    logger.info('teardown_module starts.')
    t2 = time.time()
    logger.info(f'spend time: {t2 - vars_dct.get("t1")} s')


# @pytest.mark.flaky(reruns=1, reruns_delay=3)
@pytest.mark.part1
@pytest.mark.parametrize('case_data', data_total, ids=case_ids)
class TestSuite_01_HomePage_APIs(object):
    @staticmethod
    @pytest.mark.runall
    @pytest.mark.m1
    def test_01_homepage_api(case_data):
        func_name = sys._getframe().f_code.co_name
        logger.info(f'{func_name} begin. {case_data=}')
        # step 1: send http request
        json_schema_file: str = case_data.get('json_schema_file')
        schema: dict = schema_from_jsonfile(json_schema_file)
        status_code_expect_lst = case_data.get('status_code')
        var_extract = case_data.get('var_extract')
        logger.debug(f'extract vars before {vars_dct=}')
        request_info = handle_request.preprocess_send_request(case_data, email=email, password=password, vars_dct=vars_dct)
        response_data: dict = request_info.get('response_data')
        status_code = request_info.get('status_code')
        # step 2: extract variables
        if var_extract:
            logger.info(f'before {vars_dct=}')
            vars_new = handle_request.extract_vars(response_data=response_data, var_extract=var_extract, vars_dct=vars_dct)
            logger.info(f'{vars_new=}')
            vars_dct.update(vars_new)
            # If you need any other special process
            logger.info(f'extract vars after: {vars_dct=}')
        # step 3: json schema validate
        schema_check_result = jsonschema_validate(response_data=response_data, schema=schema, request_info=request_info)
        # step 4: status code check
        assert status_code in status_code_expect_lst, f"status code is {status_code}, it should be {status_code_expect_lst}"
        assert schema_check_result
        # assert request_info.get('response_time') <= 10.0
        time.sleep(0.1)
        logger.debug('*' * 10)


if __name__ == '__main__':
    pytest.main(['-v', '-s', "--alluredir=demo_report/xml", "--clean-alluredir", __file__])
    os.system('allure serve demo_report/xml')
    pass
