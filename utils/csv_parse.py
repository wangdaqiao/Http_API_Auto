#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
@Project ：Http_API_Automation_PY3
@File    ：csv_parse.py
@Author  ：Daqiao Wang
@Date    ：2021/3/5
"""

import os
import sys
import json
import pandas as pd
from loguru import logger
from ast import literal_eval
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
sys.path.append(project_root_dir)
from config import base_config



def csv_to_cases(csvfile_input, email=None) -> list:
    """
    Convert a CSV file into a list of dictionary objects representing test cases.

    Args:
        csvfile_input (str): The path to the input CSV file.
        email (str): The test account name.

    Returns:
        list: A list of dictionary objects representing test cases. Each dictionary contains the following keys:
            - 'request_url' (str): The URL for the test case.
            - 'http_method' (str): The HTTP method for the test case.
            - 'data_type' (str): The type of data for the test case.
            - 'priority' (str): The priority of the test case.
            - 'status_code' (list): The expected status code(s) for the test case.
            ......
    """
    df = pd.read_csv(csvfile_input, index_col=False, keep_default_na=False, on_bad_lines='skip', encoding='utf-8')
    # df.drop_duplicates(subset=['request_url', 'payload'], inplace=True)
    if 'page_url' in df.columns:
        df.drop(['page_url', ], axis=1, inplace=True)
    df.reset_index(drop=True, inplace=True)
    priorities = base_config.priorities
    data_total = list()
    for index, row in df.iterrows():
        request_url = row['request_url']
        if request_url.startswith('#'):
            continue
        http_method = row['method'].lower()
        row['http_method'] = http_method
        # filter priority case
        priority_str = row.get('priority', 'p1')
        if priority_str not in priorities:
            # logger.debug(f'only run priority: {priorities}. Current case priority is:{priority_str}')
            continue
        # filter run_env
        run_env_from_sys_argv = os.environ.get('run_env')
        run_env_from_csv = row.get('run_env', 'all')
        if run_env_from_csv.lower() != 'all' and run_env_from_sys_argv != run_env_from_csv:
            logger.debug(f'{run_env_from_csv=}, {run_env_from_sys_argv=}')
            continue
        # filter test_account
        test_account = row.get('test_account', 'all')
        if test_account.lower() != 'all' and test_account != email:
            logger.debug(f'{test_account=}, {email=}')
            continue
        status_code = row.get('status_code')
        # logger.debug(f'{status_code=} {type(status_code)}')
        if not status_code:
            row['status_code'] = [200, ]
        else:
            if isinstance(status_code, int):
                row['status_code'] = [status_code, ]
            elif isinstance(status_code, str):
                tmp = literal_eval(status_code)
                if isinstance(tmp, int):
                    row['status_code'] = [tmp,]
                elif isinstance(tmp, list):
                    row['status_code'] = tmp
            else:
                logger.error(f'unknown status code, please check again. {status_code=}')
        # logger.debug(f'{row["status_code"]}=')
        data_type = row.get('data_type')
        if not data_type:
            if http_method in ('get', 'delete'):
                row['data_type'] = 'params'
            elif http_method in ('post', 'put', 'patch'):
                row['data_type'] = 'json'
            else:
                row['data_type'] = 'data'
        skip_urls = ['/users/updateBasicInfo', ]
        if any(x in request_url for x in skip_urls):
            continue
        row.drop('method', inplace=True)
        # logger.debug(f'{row=}')
        data_total.append(dict(row))
    return data_total


def cases_from_csv_dir(csv_dir=None, email=None):
    csv_lst = [os.path.join(csv_dir, x) for x in os.listdir(csv_dir) if x.endswith('.csv')]
    logger.debug(f'{csv_lst=}')
    data_total = list()
    for csv_file in csv_lst:
        case_lst = csv_to_cases(csvfile_input=csv_file, email=email)
        data_total.extend(case_lst)
    return data_total


if __name__ == '__main__':
    case_data_lst = csv_to_cases(csvfile_input='demo_cases.csv')
    logger.debug(f'{case_data_lst=}')
    logger.debug(f'{len(case_data_lst)=}')
