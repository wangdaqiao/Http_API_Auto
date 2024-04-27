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
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers, extrasaction='ignore')
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(csv_row_data)
    except Exception as err:
        logger.error(err)


if __name__ == '__main__':
    import json
    csvheaders = ['request_url', 'payload', 'length']

    request_url1 = '/v1/getNewUpdatesList'
    payload_dct1 = {"start": "0", "limit": "10", "offset": False, "selectedId": None}
    payload_str1 = json.dumps(payload_dct1, indent=None, ensure_ascii=False)
    api_content1 = [request_url1, payload_str1, 144]
    res_info_dct1 = dict(zip(csvheaders, api_content1))
    logger.info(res_info_dct1)
    record_request_csv(csvfile_path='demo_write.csv', csv_row_data=res_info_dct1, csv_headers=csvheaders)
    record_request_csv(csvfile_path='demo_write.csv', csv_row_data=res_info_dct1, csv_headers=['request_url', 'payload'])
