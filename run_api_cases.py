#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
@Project ：Http_API_Automation_PY3
@File    ：run_api_cases.py
@Author  ：Daqiao Wang
@Date    ：2021/01/20
"""

import os
import sys
import time
import subprocess
from pathlib import Path
import socket
import pytest
import copy
import shutil
from loguru import logger
import argparse
parser = argparse.ArgumentParser(description="main framework")
parser.add_argument('run_env', nargs='?', choices=['test', 'prod'], default=None,
                    help='运行环境：test/prod，支持位置参数，如 python run_api_cases.py test'
                         '不传则使用 config/config.yaml 中 run_env 指定的环境')
parser.add_argument('-run_env', dest='run_env_flag', choices=['test', 'prod'], default=None,
                    help='运行环境：test/prod（与位置参数等价，同时传入时位置参数优先）, 如 python run_api_cases.py -run_env prod')
args = parser.parse_args()
# 命令行指定的运行环境必须写入环境变量，config.base_config 只在 import 时读取一次，
# 若不写入 os.environ，-run_env / 位置参数将完全不会生效。
run_env = args.run_env or args.run_env_flag
if run_env:
    os.environ['run_env'] = run_env
from config import base_config
from utils import report_post_handle


def generate_environment_propertiesfile(folder=None):
    """
    generate environment.properties file to report folder
    :return:
    """
    environment_info = f'The_Server = {base_config.base_url}'
    environment_info += f'\nTest_account = {base_config.email}'
    environment_info += f'\nHostname = {socket.gethostname()}'
    # environment_info += f'\nPython_Version = 3.10'
    # environment_info += f'\nallure_Version = 2.17'
    file_path = os.path.join(folder, 'environment.properties')
    with open(file_path, 'w') as fw:
        fw.write(environment_info)


if __name__ == '__main__':
    # project_root_dir = os.path.dirname(__file__)
    # sys.path.append(project_root_dir)
    date_hour_minute_str = base_config.date_hour_minute_str
    logfile = os.path.join(base_config.logs_dir, f'API_{date_hour_minute_str}_summary.log')
    logger.add(logfile, level="INFO", enqueue=True)
    ts = time.time()
    allure_xml_dir = base_config.allure_xml_dir
    allure_html_dir = base_config.allure_html_dir
    # 先清掉同一分钟内上一次运行遗留的 allure 结果目录，再一次性重建，
    if os.path.isdir(allure_xml_dir):
        shutil.rmtree(allure_xml_dir, ignore_errors=True)
    os.makedirs(allure_xml_dir, exist_ok=True)
    generate_environment_propertiesfile(folder=allure_xml_dir)
    logger.info(f'{allure_xml_dir=}')
    base_pytest_lst = ['-s', f'--alluredir={allure_xml_dir}', './cases/']
    case_extra = []
    # case_extra = ['-m', 'm1']
    # case_extra = ['-m', 'm1', '-k', 'test_01_feature_a']
    # case_extra = ['-m', 'm1', '-k', 'feature_b']
    try:
        case_extra_lsts: list[list[str]] = [case_extra, ] if case_extra else base_config.case_pytest_lst
    except Exception as err:
        logger.debug(err)
        sys.exit()
    logger.info(f'{case_extra_lsts=}')
    logger.info(f'The_Server = {base_config.base_url}')
    logger.info(f'Test_account = {base_config.email}')
    logger.info(f'run_env = {base_config.env_name}')

    # 并行交由 pytest-xdist（-n N）处理；这里仅按配置逐组顺序执行 pytest，
    # 避免外层 multiprocessing 与 xdist 进程数叠加，以及多进程同时写
    # 同一个 alluredir / summary 日志 / 请求 csv 造成互相覆盖或串扰。
    for index, lst in enumerate(case_extra_lsts, start=1):
        logger.info(f'run pytest part {index}/{len(case_extra_lsts)}')
        run_lst = copy.deepcopy(base_pytest_lst)
        run_lst.extend(lst)
        pytest.main(run_lst)
    te = time.time()
    report_post_handle.allure_report_send_alert(allure_xml_dir=allure_xml_dir)
    allure_xml_dir = Path(allure_xml_dir)
    # Windows 下 allure 通常是 allure.bat，subprocess 不带 shell 时不会匹配 .bat/.cmd，
    # 会抛 FileNotFoundError: [WinError 2]，因此先用 shutil.which 解析出完整路径。
    allure_bin = shutil.which('allure')
    if not allure_bin:
        raise RuntimeError('未找到 allure 命令，请安装 allure 并将其 bin 目录加入 PATH')
    logger.info(f'{allure_bin=}')
    subprocess.run([allure_bin, 'generate', str(allure_xml_dir), '-o', str(allure_html_dir), '--clean'], check=True)
    logger.info('spend time: {}'.format(te - ts))
    # 不要用 os.system 拼引号：命令以 " 开头且引号数超过 2 个时，cmd /c 会剥掉首尾引号导致命令失效，
    # 改为 subprocess 传参数列表，避免 cmd 的引号解析问题。serve 为阻塞式服务，Ctrl+C 结束。
    subprocess.run([allure_bin, 'serve', str(allure_xml_dir)], check=True)

