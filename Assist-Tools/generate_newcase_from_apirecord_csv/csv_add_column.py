#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
'''
@Project ：Http_API_Automation_PY3
@File    ：csv_convert.py
@Author  ：Daqiao Wang
@Date    ：2022/1/14
'''

import os
import sys
from loguru import logger
from shutil import copyfile
import pandas as pd

cur_dir = os.path.dirname(__file__)
parent_pwd = os.path.dirname(cur_dir)
grandparent_dir = os.path.dirname(os.path.dirname(cur_dir))


def filelist_dir(root_dir=None):
    if os.path.isdir(root_dir):
        for root, dirs, files in os.walk(root_dir, topdown=True):
            for name in files:
                if name.endswith('.csv'):
                   yield os.path.join(root, name)
    else:
        logger.warning(f'{root_dir} is not a dir.')
        return


def csv_to_cases(csvfile_input=None):
    df = pd.read_csv(csvfile_input, index_col=False, keep_default_na=False, on_bad_lines='skip', encoding='utf-8')
    # df.drop_duplicates(subset=['request_url', 'payload'], inplace=True)
    # logger.debug(df)
    df.reset_index(drop=True, inplace=True)
    data_total = list()
    df_final_all = list()
    for index, row in df.iterrows():
        request_url = row['request_url']
        http_method = row['method'].lower()
        payload_str = row['payload']
        data_type = row.get('data_type')
        json_schema_file = row.get('json_schema_file')
        # logger.info(f'{json_schema_file=}')
        if not json_schema_file:
            if '/' in request_url:
                json_schema_file = request_url.replace('/', '_')
                json_schema_file = f'{json_schema_file}_{http_method.upper()}.json'
            else:
                json_schema_file = ''
            row['json_schema_file'] = json_schema_file
        if request_url.startswith('#'):
            pass
        skip_urls = ['/users/updateBasicInfo', ]
        if any(x in request_url for x in skip_urls):
            continue

        page_url = uri_page_dct.get(request_url)
        if not row.get('page_url'):
            row['page_url'] = page_url
        if not row.get('remark'):
            row['remark'] = ''
        if not row.get('status_code'):
            row['status_code'] = 200
        if not row.get('run_env'):
            row['run_env'] = 'all'
        if not row.get('test_account'):
            row['test_account'] = 'all'
        if not row.get('priority'):
            row['priority'] = 'p1'
        if not row.get('upload_file'):
            row['upload_file'] = None
        # print(row)
        df_final_all.append(row)
        # data_total.append((request_url, http_method, data_type, row['params'], payload_str))
    df_final = pd.DataFrame(df_final_all, columns=['request_url', 'method', 'data_type', 'upload_file', 'params', 'json_schema_file', 'status_code', 'payload', 'run_env', 'test_account','priority', 'page_url', 'remark'])
    # df_final = pd.DataFrame(df_final_all)
    # logger.debug(df_final)
    df_final.to_csv(os.path.join(cur_dir, csvfile_input), index=None)
    return data_total



def csv_to_dct(csvfile_input=None):
    df = pd.read_csv(csvfile_input, index_col=False, keep_default_na=False, on_bad_lines='skip', encoding='utf-8')
    # df.drop_duplicates(subset=['request_url', 'payload'], inplace=True)
    # logger.debug(df)
    dct = dict(zip(df['request_url'], df['page_url']))
    # logger.debug(dct)
    return dct


if __name__ == '__main__':
    uri_page_dct = csv_to_dct(csvfile_input='api_request_20221110_1908.csv')
    for x in filelist_dir(root_dir=parent_pwd):
        logger.debug(x)
        if not os.path.exists(f'{x}.bak'):
            pass
            copyfile(x, f'{x}.bak')
        if 'api_request' not in x or 'apirecode_' not in x or 'apirecode_demo' in x:
            pass
            try:
                csv_to_cases(csvfile_input=x)
            except Exception as err:
                logger.error(err)

        if '99_logout.csv' in x:
            pass
            csv_to_cases(csvfile_input=x)

