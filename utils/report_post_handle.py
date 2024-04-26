#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
@Project ：Http_API_Automation_PY3
@File    ：report_post_handle.py
@Author  ：Daqiao Wang
@Date    ：2021/4/22
"""

import os
import sys
import glob
import json
import socket
from collections import defaultdict
from loguru import logger
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
sys.path.append(project_root_dir)
from config import base_config
from utils import common_funs


date_hour_minute_str = base_config.date_hour_minute_str


def analyze_allure_report(allure_xml_dir="report/xml"):
    """
    Analyze the data of Allure generated and count the number of passed/failed/broken/skipped/unknown cases
    :param allure_xml_dir: str
    :return: defaultdict(int)
    """
    logger.info(f'{allure_xml_dir=}')
    assert os.path.exists(allure_xml_dir)
    json_files = glob.glob(f'{allure_xml_dir}/*-result.json')
    # logger.debug(json_files)
    total_times = 0
    case_result_dct = defaultdict(dict)
    for jsonfile in json_files:
        total_times += 1
        with open(jsonfile, 'r', encoding='utf-8') as f:
            jdata = json.load(f)
        status_case = jdata.get('status')
        history_id = jdata.get('historyId')
        if 'status' not in case_result_dct[history_id]:
            case_result_dct[history_id]['status'] = []
            case_result_dct[history_id]['fullName'] = jdata.get('name')
        case_result_dct[history_id]['status'].append(status_case)
    # pprint(case_statuss_dct)
    # logger.debug(len(case_result_dct))
    result_dct = defaultdict(int)
    retry_passed_case_names: list = list()
    failed_broken_only_case_names: list = list()
    for _, case_dct in case_result_dct.items():
        case_name = case_dct.get('fullName')
        status_case_lst = case_dct.get('status')
        result_dct['total_times'] += 1
        if any('passed' == x for x in status_case_lst):
            result_dct['passed_times'] += 1
        elif all('failed' == x for x in status_case_lst):
            result_dct['failed_times'] += 1
            failed_broken_only_case_names.append(case_name)
        elif all(x in ['broken', 'failed'] for x in status_case_lst):
            result_dct['broken_times'] += 1
            failed_broken_only_case_names.append(case_name)
        elif any(x in ['broken', 'skipped'] for x in status_case_lst):
            result_dct['skipped_times'] += 1
        if 'unknown' in status_case_lst:
            result_dct['unknown_times'] += 1
        if 'passed' in status_case_lst and len(set(status_case_lst)) > 1:
            result_dct['retry_ok_times'] += 1
            retry_passed_case_names.append(case_name)

    if len(retry_passed_case_names) > 4:
        retry_passed_case_names = retry_passed_case_names[:4]
        retry_passed_case_names.append('......')
    if len(failed_broken_only_case_names) > 4:
        failed_broken_only_case_names = failed_broken_only_case_names[:4]
        failed_broken_only_case_names.append('......')
    #
    result_dct['retry_passed_case_name'] = '\n'.join(retry_passed_case_names)
    result_dct['failed_broken_only_case_name'] = '\n'.join(failed_broken_only_case_names)
    logger.debug(f'result_dct: {result_dct}')
    return result_dct


def report_by_status_code_response_time(csv_rootdir=None, api_issue_html=None):
    csv_rootdir = csv_rootdir if csv_rootdir else base_config.logs_dir
    logger.info(f'{csv_rootdir=}')
    csv_lst = [x for x in common_funs.filelist_dir(root_dir=csv_rootdir) if x.endswith('.csv')]
    if not csv_lst:
        logger.warning(f'no csv file found in "{csv_rootdir}", return None')
        return
    df = common_funs.csv_to_df(csv_lst)
    html_code = common_funs.df_to_html(df)
    with open(api_issue_html, 'w', encoding='utf-8') as fw:
        fw.write(html_code)
    return df


def allure_report_send_alert(allure_xml_dir=None, csv_rootdir=None):
    """
    generate alert message text
    """
    if allure_xml_dir is None:
        allure_xml_dir = os.path.join(project_root_dir, 'report', 'xml')
    elif not os.path.isabs(allure_xml_dir):
        allure_xml_dir = os.path.join(project_root_dir, allure_xml_dir)
    if not os.path.exists(allure_xml_dir):
        logger.error(f'xml data dir: {allure_xml_dir} not exists.')
        return
    if csv_rootdir is None:
        csv_rootdir = os.path.join(project_root_dir, base_config.logs_dir)
    elif not os.path.isabs(csv_rootdir):
        csv_rootdir = os.path.join(project_root_dir, csv_rootdir)
    if not os.path.exists(csv_rootdir):
        logger.warning(f'csv data dir: {csv_rootdir} not exists.')
    cases_result = analyze_allure_report(allure_xml_dir=allure_xml_dir)
    # logger.debug(cases_result)
    myip = common_funs.get_host_ip()
    total_case_number = cases_result.get('total_times', 0)
    passed_case_number = cases_result.get('passed_times', 0)
    skipped_case_number = cases_result.get('skipped_times', 0)
    failed_case_number = cases_result.get('failed_times', 0)
    broken_case_number = cases_result.get('broken_times', 0)
    retry_ok_case_number = cases_result.get('retry_ok_times', 0)
    unknown_case_number = cases_result.get('unknown_times', 0)
    msg_text = f'There are {total_case_number} API cases'
    if passed_case_number:
        msg_text += f', {passed_case_number} passed'
    if skipped_case_number:
        msg_text += f', {skipped_case_number} skipped'
    if unknown_case_number:
        msg_text += f', {unknown_case_number} unknown'
    if retry_ok_case_number:
        msg_text += f', {retry_ok_case_number} failed once and retry passed, they are:\n'
        msg_text += cases_result.get('retry_passed_case_name')
    msg_text += '\n'
    all_api_good = False
    if total_case_number == passed_case_number + skipped_case_number + unknown_case_number:
        logger.debug('all api cases work well.')
        all_api_good = True
        msg_text = 'Good. ' + msg_text
    if failed_case_number > 0 or broken_case_number > 0:
        logger.debug('Some api case failed or broken')
        all_api_good = False
        msg_text = r'<@jianwang>. ' + msg_text + '-' * 25 + '\n'
        if failed_case_number:
            msg_text += f'{failed_case_number} always failed'
        if broken_case_number:
            msg_text += f', {broken_case_number} always broken'
        msg_text += f'. The Failed/Broken cases are:\n'
        msg_text += cases_result.get('failed_broken_only_case_name')
    msg_text += '\n' + '-' * 25
    msg_text += f'\nThe Server: {base_config.base_url} user account: {base_config.email}, run api autotest on: {socket.gethostname()} {myip}'
    msg_text += f'\nFor details: https://allure.testxxx.com/allure_html_api/{date_hour_minute_str}/\n'
    logger.info(f'{myip=} {all_api_good=}')
    api_issues_html_dir = os.path.join(project_root_dir, 'report', 'api_issues')
    if not os.path.exists(api_issues_html_dir):
        os.makedirs(api_issues_html_dir)
    api_issue_html = os.path.join(api_issues_html_dir, f'api_issues_{date_hour_minute_str}.html')
    df = report_by_status_code_response_time(csv_rootdir=csv_rootdir, api_issue_html=api_issue_html)
    if df is not None:
        number = len(df)
        if number >= 1:
            msg_text += f'There are {number} apis with incorrect status_code or more than 3 seconds.'
            # msg_text += f'\nFor details: https://allure.testxxx.com/report_api_issue/{date_hour_minute_str}.html '
            msg_text += f'\nFor details: {api_issue_html} '
        else:
            logger.debug('All api status code is 200, and response time is less than 3s.')
    logger.info(f'{msg_text=}')
    # Send alert messages if necessary (via slack, Dingding, email, etc.)



if __name__ == '__main__':
    allure_xml_dir = "report/xml_test"
    csv_rootdir = 'logs/20240424_1815'
    # allure_report_send_alert(allure_xml_dir=allure_xml_dir, csv_rootdir=csv_rootdir)
    allure_report_send_alert(allure_xml_dir=allure_xml_dir)
