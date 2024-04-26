#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
'''
@Project ：Http_API_Automation_PY3
@File    ：common_funs.py
@Author  ：Daqiao Wang
@Date    ：2021/4/20
'''

import os
import sys
from datetime import datetime
import socket
import pandas as pd
from loguru import logger
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
sys.path.append(project_root_dir)
from config import base_config


def get_host_ip():
    """
    Return the IP address of the host
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def case_ids_define(data_total):
    case_ids = ['-'.join([x['request_url'], x['http_method']]) for x in data_total]
    return case_ids


def find_latest_file(root_dir: str = '', extension_name: str|None = None):
    """
    Find the latest modified file in the directory.

    Args:
        root_dir (str): The root directory to search for files. Default is current directory.
        extension_name (str): The file extension to filter files. Default is '.csv'.

    Returns:
        str: The path of the latest modified file, or None if no file is found.
    """
    latest_file = None
    latest_time = datetime(1970, 1, 1)
    for x in filelist_dir(root_dir=root_dir):
        if extension_name and x.endswith(extension_name):
            mod_stamptime = os.path.getmtime(x)
            mod_datetime = datetime.fromtimestamp(mod_stamptime)
            # logger.debug(f'{x=}, {mod_stamptime=} {mod_datetime=}')
            if mod_datetime > latest_time:
                latest_time = mod_datetime
                latest_file = x
    return latest_file


def filelist_dir(root_dir=''):
    if os.path.isdir(root_dir):
        for root, dirs, files in os.walk(root_dir, topdown=True):
            for name in files:
                yield os.path.join(root, name)
    else:
        logger.warning(f'{root_dir} is not a dir.')
        return


def csv_to_df(csv_files: str | list):
    """
        Reads a CSV file (or a list of CSV files) and converts it into a pandas DataFrame.

        Parameters:
            csv_files (str|list): The path to the CSV file.

        Returns:
            pandas.DataFrame: The DataFrame containing the data from the CSV file.
        """
    if isinstance(csv_files, str):
        csv_files = [csv_files,]
    logger.info(f'{csv_files=}')
    dfs = []
    for csv_file in csv_files:
        df_tmp = pd.read_csv(csv_file, index_col=False, keep_default_na=False, on_bad_lines='skip')
        dfs.append(df_tmp)
    combined_df = pd.concat(dfs, ignore_index=True)
    # logger.info(f'{len(combined_df)=}')
    keep_cols = ['request_url', 'method', 'status_code', 'params', 'payload', 'response_time', 'finish_time']
    df1 = combined_df[keep_cols]
    df_final = df1.copy()
    # df_final['response_time'] = pd.to_numeric(df1['response_time'], errors='coerce')
    # df_final['status_code'] = pd.to_numeric(df1['status_code'], errors='coerce', downcast='integer')
    # df_final = df_final.dropna(subset=['status_code'])
    # df_final['status_code'] = df_final['status_code'].astype(int)
    df_final = df_final[(df_final['status_code'] != 200) | (df_final['response_time'] > 3.0)]
    df_final = df_final.sort_values(by=['status_code', 'response_time'], ascending=False).head(30)
    return df_final


def df_to_html(df):
    """
    Convert a pandas dataframe to HTML code.

    Args:
        df (pandas.DataFrame): The dataframe to be converted.

    Returns:
        str: The HTML code representing the dataframe.
    """
    # Pandas DataFrame to HTML
    html_table = df.to_html(index=False, na_rep='', justify='center')
    html_head = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CSV to HTML</title>
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
            }
            td {
                border: 2px solid #dd;
                padding: 2px dashed blue;
                white-space: nowrap;
                overflow: auto; /* Displays a horizontal scroll bar when the cell content exceeds the width */
                max-width: 280px;
                max-height: 200px;
            }
            tr:nth-child(even) {
              background-color: #f2f2f2;
            }
            tr:nth-child(even) td {
                background-color: #e6f2ff;
            }
        </style>
    </head>
    <body>
    """
    html_tail = """
    </body>
    </html>
    """
    html_code = html_head + html_table + html_tail
    return html_code


if __name__ == '__main__':
    latest_file = find_latest_file(root_dir=base_config.logs_dir, extension_name='.csv')
    logger.debug(f'{latest_file=}')
