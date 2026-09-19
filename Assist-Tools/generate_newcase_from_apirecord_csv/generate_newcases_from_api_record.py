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
from urllib.parse import urlparse
import re

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
    # 这里必须用 root_dir 拼出绝对路径再判断，否则脚本不在该目录下运行时
    # os.path.isfile / os.path.getmtime 会基于当前工作目录判断，导致全部失效。
    file_lst = [os.path.join(root_dir, x) for x in os.listdir(root_dir)
                if x.endswith(ext) and '_cases' not in x and '_dropduplicate' not in x
                and os.path.isfile(os.path.join(root_dir, x))]
    if not file_lst:
        raise FileNotFoundError(f'no {ext} record file found in {root_dir}, '
                                f'please pass the record csv path as the first command-line argument.')
    latest_file = max(file_lst, key=os.path.getmtime)
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
    except Exception as error:
        logger.error(f'{target=}')
        logger.error(f'to_json_schema failed: {error!r}, target preview: {str(target)[:300]}')
        return None


# Windows 文件名非法字符（含路径分隔符），统一替换成下划线
ILLEGAL_FILENAME_CHARS_PATTERN = re.compile(r'[<>:"\\|?*/]')


def safe_schema_name(url: str) -> str:
    """
    Convert a request url into a safe json schema filename prefix.
    只取 path 部分（去掉 host/query），并过滤掉 Windows 文件名非法字符，
    避免 request_url 带 host（形如 http://127.0.0.1:5000/v1/x）时
    因文件名含 ':' 导致 open() 抛 OSError 中断整个脚本。
    """
    path = urlparse(url).path or url
    return ILLEGAL_FILENAME_CHARS_PATTERN.sub('_', path)


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
df = pd.read_csv(csv_input, index_col=False, keep_default_na=False, on_bad_lines='skip', encoding='utf-8')
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
# 待落盘的新用例：(row, schema 文件名, schema)。这里只收集、不写文件，
# 统一在 step 4 落盘，见下方说明。
pending_cases = list()
# print(df)
json_schema_files_dir = os.path.join(grand_dir, 'cases', 'jsonfiles')
logger.debug(f'{json_schema_files_dir=}')
exist_jsonfile_fullpath_lst = list(filelist_dir(root_dir=json_schema_files_dir))
exist_jsonfile_onlyname_lst = [os.path.basename(x) for x in exist_jsonfile_fullpath_lst]
exist_jsonfile_dct = dict(zip(exist_jsonfile_onlyname_lst, exist_jsonfile_fullpath_lst))
# logger.debug(f'{exist_jsonfile_dct=}')
# 用绝对路径，避免从其他工作目录执行时把 schema 写到意料之外的位置。
new_jsonschema_files_dir = os.path.join(cur_dir, 'new_jsonschema_files_dir')

skip_urls = [
    '/v1/projects/projectInformation/*',
    '/v2/sequencetemplate/*/steps',
    '/v2/sequencetemplate/*',
]

for index, row in df2.iterrows():
    # 统一的跳过判断：用 urlparse 取出 path 再匹配，避免 request_url 带 host/query
    # 时匹配不上；同时统一大小写，消除 fnmatch 在 Windows/Linux 上的大小写差异。
    # 该判断必须放在 schema 是否已存在之前，保证两种分支行为一致。
    request_path = urlparse(row['request_url']).path or row['request_url']
    if any(fnmatch(request_path.lower(), x.lower()) for x in skip_urls):
        logger.debug(f'skip url: {row["request_url"]}')
        continue
    method = row['method']
    json_schema_filename = f'{safe_schema_name(row["request_url"])}_{method}_{row["status_code"]}.json'
    # logger.debug(f'{json_schema_filename=}')
    row['json_schema_file'] = json_schema_filename
    jsonschema_file_fullpath = exist_jsonfile_dct.get(json_schema_filename)
    # logger.debug(f'{jsonschema_file_fullpath=}')
    if json_schema_filename in exist_jsonfile_dct:
        # schema 已存在：不生成新 case，只拿已有 schema 校验本次响应
        response_text = row['response_text']
        try:
            json_data = json.loads(response_text)
            with open(jsonschema_file_fullpath, encoding='utf-8') as fr:
                schema = json.load(fr)
                try:
                    validate(instance=json_data, schema=schema)
                except SchemaError as err:
                    # logger.error(f'{json_data=}')
                    logger.error(schema)
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
        continue
    # P2-d：只有确认需要新建 schema 时才解析响应体，
    # 避免在 schema 已存在的行上做无用解析，也避免为非 JSON 响应打出误导性 error 日志。
    schema: dict = to_json_schema(row['response_text'])
    if schema is None:
        # 响应为空/非 JSON 时 to_json_schema 返回 None，此时既不能写 null schema
        # 文件，也不能生成 case，否则运行时 validate(data, None) 必然报 SchemaError。
        logger.warning(f'{json_schema_filename=} failed to generate json schema, skip this case.')
        continue
    logger.debug(f'{json_schema_filename=} not exists, create it.')
    row['upload_file'] = None
    row['var_extract'] = None
    row['run_env'] = 'all'
    row['test_account'] = 'all'
    row['priority'] = 'p0'
    pending_cases.append((row, json_schema_filename, schema))

# step 4: 统一落盘。先写 schema 文件，只有写成功的行才进入 cases csv。
# 这样不会出现"schema 已落盘、case 却没记录"的孤儿 schema 文件
# ——孤儿文件一旦被人工拷进 cases/jsonfiles，后续运行会命中"已存在"分支，
# 导致该用例被永久跳过且无任何提示。
new_cases = list()
if pending_cases:
    os.makedirs(new_jsonschema_files_dir, exist_ok=True)
for case_row, json_schema_filename, schema in pending_cases:
    try:
        with open(os.path.join(new_jsonschema_files_dir, json_schema_filename), 'w', encoding='utf-8') as fw:
            json.dump(schema, fw, indent=4)
    except OSError as err:
        logger.error(f'write json schema file failed: {json_schema_filename}, {err!r}, skip this case.')
        continue
    new_cases.append(case_row)
# logger.debug(len(new_cases))

if new_cases:
    df_newcase = pd.DataFrame(new_cases)
    # logger.debug(df_newcase)
    # logger.debug(df_newcase.columns)
    df_newcase.to_csv(csv_cases, index=False,
                      columns=['request_url', 'method', 'data_type', 'params', 'json_schema_file', 'status_code', 'payload', 'upload_file',
                                'var_extract', 'run_env', 'test_account', 'priority',
                               'page_url', 'remark'], encoding='utf-8')
    logger.info(f'{len(new_cases)} new case(s) written to {csv_cases}')
else:
    logger.info('no new case')
te = time.time()
logger.debug(f'Task finished: {te - ts} s.')
logger.debug(csv_input)
