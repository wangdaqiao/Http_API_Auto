#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
@Project ：API_Auto_PY3
@Author  ：Daqiao Wang
@Date    ：2023/3/26
"""

import sys
import os
import time
from genson import SchemaBuilder
import json
from jsonschema import validate
from jsonschema.exceptions import SchemaError, ValidationError
import pandas as pd
from loguru import logger
from fnmatch import fnmatch

'''
Run this .py with command-line argument
step 1: If run this .py with command-line argument, the first argument is the api record .csv to be processed,
        If run without command-line argument, it wil handle the latest api record .csv file in current directory.
step 2: drop duplicates by 'request_url', 'params', and 'payload', and save to new .csv file.
step 3: Read the data line by line, skip but take json schema validate if the api has been processed,
         otherwise generate a json schema file based on the response text and add it to the new test case.
         Finally, generate a new test case csv file(***_case.csv)
'''

cur_dir = os.path.dirname(__file__)
par_dir = os.path.dirname(cur_dir)
grand_dir = os.path.dirname(par_dir)
logger.debug(f'{grand_dir=}')


def find_latest_file(root_dir, ext='.csv'):
    """Find the latest modified file in the directory"""
    file_lst = [x for x in os.listdir(root_dir) if
                os.path.isfile(x) and '_cases' not in x and '_dropduplicate' not in x and x.endswith(ext)]
    file_lst.sort(key=lambda fn: os.path.getmtime(fn))
    logger.debug(f'latest_csv_file is： {file_lst[-1]}')
    latest_file = os.path.join(root_dir, file_lst[-1])
    logger.debug(f'latest csv file full path：{latest_file}')
    return latest_file


def to_json_schema(target):
    try:
        builder = SchemaBuilder(schema_uri=False)
        # builder.add_schema({"type": "object", "properties": {}})
        if isinstance(target, str):
            target = json.loads(target)
        builder.add_object(target)
        # print(builder.to_json(indent=2))
        return builder.to_schema()
    except BaseException as error:
        logger.error(target)
        logger.error(error)
        return None


def filelist_dir(root_dir=cur_dir):
    if os.path.isdir(root_dir):
        for root, dirs, files in os.walk(root_dir, topdown=True):
            for name in files:
                if name.endswith('.json'):
                    yield os.path.join(root, name)
    else:
        logger.warning(f'{root_dir} is not a dir.')
        return

# step 1:
ts = time.time()
if len(sys.argv) > 1:
    csv_input = sys.argv[1]
else:
    csv_input = find_latest_file(cur_dir, ext='.csv')
# csv_input = 'apirecode_20210325_demo.csv'
logger.debug(csv_input)

# step 2:
csv_output_drop_duplicate = csv_input[:-4] + '_dropduplicate.csv'
csv_cases = csv_input[:-4] + '_cases.csv'
df = pd.read_csv(csv_input, index_col=False, encoding='utf-8')
df.drop_duplicates(subset=['request_url', 'params', 'payload'], inplace=True)
df.reset_index(drop=True, inplace=True)
# df.sort_values(by=['finish_time'], inplace=True)
for x in ['page_url', 'remark']:
    if x not in df.columns:
        df[x] = ''
df2 = df[['request_url', 'method', 'data_type', 'params', 'payload', 'response_length', 'status_code',
          'response_text', 'page_url', 'remark']]
# df2.to_csv(csv_output_drop_duplicate, index=False, encoding='utf-8')
logger.debug(f'{df2.columns=}')

# step 3:
rows = list()
# print(df)
json_schema_files_dir = os.path.join(grand_dir, 'cases', 'jsonfiles')
logger.debug(f'{json_schema_files_dir=}')
exist_jsonfile_fullpath_lst = list(filelist_dir(root_dir=json_schema_files_dir))
exist_jsonfile_onlyname_lst = [os.path.basename(x) for x in exist_jsonfile_fullpath_lst]
exist_jsonfile_dct = dict(zip(exist_jsonfile_onlyname_lst, exist_jsonfile_fullpath_lst))
# logger.debug(f'{exist_jsonfile_dct=}')
new_jsonschema_files_dir = 'new_jsonschema_files_dir'
if not os.path.exists(new_jsonschema_files_dir):
    os.mkdir(new_jsonschema_files_dir)

skip_urls = [
    '/v1/projects/projectInformation/*',
    '/v2/sequencetemplate/*/steps',
    '/v2/sequencetemplate/*',
]

for index, row in df2.iterrows():
    response_text = row['response_text']
    method = row['method']
    schema: dict = to_json_schema(response_text)
    row['upload_file'] = None
    row['var_extract'] = None
    row['run_env'] = 'all'
    row['test_account'] = 'all'
    row['priority'] = 'p0'
    json_filename_split_tmp = row['request_url'].split('?')[0].replace('/', '_')
    json_schema_filename = f'{json_filename_split_tmp}_{method}_{row["status_code"]}.json'
    # logger.debug(f'{json_schema_filename=}')
    row['json_schema_file'] = json_schema_filename
    jsonschema_file_fullpath = exist_jsonfile_dct.get(json_schema_filename)
    # logger.debug(f'{jsonschema_file_fullpath=}')
    if json_schema_filename not in exist_jsonfile_dct:
        if not any(fnmatch(row['request_url'], x) for x in skip_urls):
            logger.debug(f'{json_schema_filename=} not exists, create it.')
            jsonschema_file_fullpath = os.path.join(new_jsonschema_files_dir, json_schema_filename)
            rows.append(row)
            with open(jsonschema_file_fullpath, 'w', encoding='utf-8') as fw:
                json.dump(schema, fw, indent=4)
    else:
        # logger.debug(f'{json_schema_filename=} is exists.')
        try:
            json_data = json.loads(response_text)
            with open(jsonschema_file_fullpath, encoding='utf-8') as fr:
                schema = json.load(fr)
                try:
                    validate(instance=json_data, schema=schema)
                except SchemaError as err:
                    # logger.error(f'{json_data=}')
                    logger.error(json.loads(schema))
                    err_msg = "schema error：\n：Error Location: {}\nprompt msg：{}".format(
                        " --> ".join([str(x) for x in err.path]), err.message)
                    logger.error(err_msg)
                except ValidationError as err:
                    logger.error(f'{json_data=}')
                    logger.error(f'{schema=}')
                    err_msg = "json data schema validation failure：\nError Fields：{}\nprompt：{}".format(
                        " --> ".join([str(x) for x in err.path]), err.message)
                    logger.debug(f'jsonfile: {json_schema_filename} is exists.')
                    logger.error(err_msg)
                    logger.debug('*' * 25)
        except Exception as err:
            logger.error(f'{err=}')
            logger.error(f'{response_text=}')

# logger.debug(len(rows))
df_newcase = pd.DataFrame(rows)
# logger.debug(len(df_newcase))
# logger.debug(df_newcase)
# logger.debug(df_newcase.columns)


if rows:
    df_newcase.to_csv(csv_cases, index=False,
                      columns=['request_url', 'method', 'data_type', 'params', 'json_schema_file', 'status_code', 'payload', 'upload_file',
                                'var_extract', 'run_env', 'test_account', 'priority',
                               'page_url', 'remark'], encoding='utf-8')
else:
    logger.info('no new case')
te = time.time()
logger.debug(f'Task finished: {te - ts} s.')
logger.debug(csv_input)
