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
import socket
from multiprocessing import Pool
import pytest
import copy
from loguru import logger
if len(sys.argv) == 2:
    os.environ['run_env'] = sys.argv[1].lower()
from config import base_config
from utils import report_post_handle


def generate_environment_propertiesfile(folder=None):
    """
    generate environment.properties file to report folder
    :return:
    """
    enviroment_info = f'The_Server = {base_config.base_url}'
    enviroment_info += f'\nTest_account = {base_config.email}'
    enviroment_info += f'\nHostname = {socket.gethostname()}'
    # enviroment_info += f'\nPython_Version = 3.10'
    # enviroment_info += f'\nallure_Version = 2.17'
    file_path = os.path.join(folder, 'environment.properties')
    with open(file_path, 'w') as fw:
        fw.write(enviroment_info)


def run_case_part(pytest_lst):
    logger.info(f'{pytest_lst=}')
    pytest.main(pytest_lst)


if __name__ == '__main__':
    # project_root_dir = os.path.dirname(__file__)
    # sys.path.append(project_root_dir)
    date_hour_minute_str = base_config.date_hour_minute_str
    logfile = os.path.join(base_config.logs_dir, f'API_{date_hour_minute_str}_summary.log')
    logger.add(logfile, level="INFO", enqueue=True)
    ts = time.time()
    # allure_xml_dir = f'report/xml_{date_hour_minute_str}'
    allure_xml_dir = base_config.allure_xml_dir
    generate_environment_propertiesfile(folder=allure_xml_dir)
    logger.info(f'{allure_xml_dir=}')
    base_pytest_lst = ['-s', f'--alluredir={allure_xml_dir}', '--clean-alluredir', './cases/']
    case_extra = []
    # case_extra = ['-m', 'm1']
    # case_extra = ['-m', 'm1', '-k', 'test_01_homepage_']
    # case_extra = ['-m', 'm1', '-k', '_demo']
    try:
        if case_extra:
            case_extra_lsts = [case_extra, ]
        else:
            case_extra_lsts = base_config.case_pytest_lst
    except NameError as err:
        case_extra_lsts = base_config.case_pytest_lst
    except Exception as err:
        logger.debug(err)
        sys.exit()
    logger.info(f'{case_extra_lsts=}')
    logger.info(f'The_Server = {base_config.base_url}')
    logger.info(f'Test_account = {base_config.email}')

    p = Pool()
    for lst in case_extra_lsts:
        logger.debug(f'{lst=}')
        run_lst = copy.deepcopy(base_pytest_lst)
        run_lst.extend(lst)
        p.apply_async(run_case_part, args=(run_lst,))
    p.close()
    p.join()
    te = time.time()
    report_post_handle.allure_report_send_alert(allure_xml_dir=allure_xml_dir)
    # os.system('allure generate report/xml -o report/html --clean')
    os.system(f'allure generate {allure_xml_dir} -o {base_config.project_root_dir}/report/html_{date_hour_minute_str}/ --clean')
    logger.info('spend time: {}'.format(te - ts))
    os.system(f'allure serve {allure_xml_dir}')
