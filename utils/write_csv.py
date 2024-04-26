# -*- coding: utf-8 -*-
'''
@Time    : 2024/4/10 19:03
@Author  : Daqiao Wang
@File    : write_csv.py
'''

import csv
from loguru import logger

def record_request_csv(csvfile_path=None, csv_row_data: dict=None, csv_headers: list=None):
    """
    record http request data to csv file
    """
    if not csvfile_path:
        logger.error('csvfile_path is None')
        return
    try:
        with open(csvfile_path, "a+", encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, csv_headers)
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(csv_row_data)
    except Exception as err:
        logger.error(err)
