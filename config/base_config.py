#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys
import time
from loguru import logger
import yaml
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
now_minute_from_env: str = os.environ.get('date_hour_minute_str')
if now_minute_from_env:
    date_hour_minute_str = now_minute_from_env
else:
    date_hour_minute_str = time.strftime("%Y%m%d_%H%M")
    os.environ['date_hour_minute_str'] = date_hour_minute_str
logs_dir = os.path.join(project_root_dir, 'logs', date_hour_minute_str)
# logger.debug(f'{logs_dir=}')
allure_xml_dir = os.path.join(project_root_dir, 'report', f'xml_{date_hour_minute_str}')
allure_html_dir = os.path.join(project_root_dir, 'report', f'html_{date_hour_minute_str}')
for x in [logs_dir, allure_xml_dir]:
    if not os.path.exists(x):
        os.makedirs(x)

yml_file = os.path.join(cur_dir, 'config.yaml')
with open(yml_file, 'r', encoding='utf-8') as f:
    dct = yaml.load(f.read(), Loader=yaml.FullLoader)
run_env_from_sys_argv = os.environ.get('run_env')
if run_env_from_sys_argv:
    env_name = run_env_from_sys_argv
else:
    env_name = dct.get('run_env', 'test')
    os.environ['run_env'] = env_name

assert env_name.lower() in ['test', 'stage', 'prod'], f'{env_name=}'

case_pytest_lst = dct.get('case_pytest_lst', [])
env_info = dct.get(env_name)
priorities = dct.get('priorities', ['p0'])
priorities = env_info.get('priorities', priorities)


base_url = env_info.get('base_url')
email = env_info.get('email')
password = env_info.get('password')
need_login = env_info.get('need_login')
admin_account = env_info.get('admin_account')
admin_password = env_info.get('business_tier_password')


if __name__ == '__main__':
    logger.debug(f'{env_name=}')
    logger.debug(f'{base_url=}')
    logger.debug(f'{email=}')
    logger.debug(f'{priorities=}')

