#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys
import json
from urllib.parse import urljoin
import datetime
import requests
from loguru import logger
import csv
cur_dir = os.path.dirname(__file__)
project_root_dir = os.path.dirname(cur_dir)
sys.path.append(project_root_dir)
from config import base_config
from utils import write_csv

try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    # for Windows, avoid OverflowError: Python int too large to convert to C long
    csv.field_size_limit(2147483647)

session_dct = dict()


class AppApiBase(object):
    """
    OurApp Api Base
    """
    def __init__(self, url='', params_dict=None, payload_dict=None, http_method='get', data_type=None, files=None,
                 email=None, password=None, need_login=False):
        self.request_url = url
        if url.lower().startswith(r'http://') or url.lower().startswith(r'https://'):
            self.full_url = url
        else:
            self.full_url = urljoin(base_config.base_url, url)
        self.email = email if email else base_config.email
        self.password = password if password else base_config.password
        self.need_login = need_login if need_login else base_config.need_login
        self.headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}
        # logger.info(f'{self.email=}  {self.password=}')
        if not session_dct.get(self.email):
            logger.debug(f'class session for {self.email} is None')
            session_dct[self.email] = self.login_session(email=self.email, password=self.password)
        else:
            logger.debug(f'class session for {self.email} exists already')
        self.params_dict = params_dict
        self.payload_dict = payload_dict
        self.params_str = json.dumps(params_dict, ensure_ascii=False) if params_dict else None
        self.payload_str = json.dumps(payload_dict, ensure_ascii=False) if payload_dict else None
        self.request_length = len(self.payload_str) if self.payload_str else None
        self.http_method = http_method.lower()
        if data_type:
            self.data_type = data_type.lower()
        else:
            if http_method.lower() in ('get', 'delete'):
                self.data_type = 'params'
            elif http_method.lower() in ('post', 'put', 'patch'):
                self.data_type = 'json'
            else:
                self.data_type = 'data'
        if self.data_type == 'data':
            self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self.files = files

    # @staticmethod
    def login_session(self, email=None, password=None):
        """
        create a login requests session for a user.
        """
        # login_url_full = "https://api.testxxx.com/v1/users/login"
        login_url_full = urljoin(base_config.base_url, '/v1/users/login')
        payload = {"email": email, "password": password}
        logger.debug(f'login {login_url_full=} {payload=}')
        session = requests.session()
        if not self.need_login:
            return session
        # TODO:  Please Improve the login section, usually need to update headers as required
        return session
        '''
        response = session.request("POST", login_url_full, json=payload, headers=self.headers, verify=False)
        cookies = response.cookies.get_dict()
        if cookies:
            session.headers.update({'csrf-token': cookies['csrfToken']})
            return session
        else:
            logger.warning(f'response of /v1/users/login: {response}')
            logger.warning('failed to login, quit now')
            sys.exit()
        '''

    def http_request(self, called_py=None):
        """
        make an HTTP request & records the data(uri, method, status code, response, response time, etc.) into a CSV file
        """
        logger.info(f'{called_py=}')
        csvfile_path = os.path.join(base_config.logs_dir, f'API_{base_config.date_hour_minute_str}_{called_py}.csv')
        csv_headers: list = ['request_url',
                             'method',
                             'data_type',
                             'params',
                             'payload',
                             'request_length',
                             'status_code',
                             'response_str',
                             'response_length',
                             'response_time',
                             'finish_time']
        if self.data_type in ('params', 'json', 'file'):
            payload_data = None
            payload_json = self.payload_dict
        elif self.data_type == 'data':
            payload_data = self.payload_dict
            payload_json = None
        else:
            raise ValueError('Optional keyword data_type only be ["params", "json", "data", "file"]')
        if self.files:
            self.headers.pop('Content-Type')
        try:
            r = session_dct.get(self.email).request(url=self.full_url,
                                                    method=self.http_method,
                                                    params=self.params_dict,
                                                    data=payload_data,
                                                    json=payload_json,
                                                    files=self.files,
                                                    timeout=60,
                                                    # proxies={"https": "http://127.0.0.1:9999"},
                                                    verify=False,
                                                    headers=self.headers)
            status_code = r.status_code
            response_length = len(r.content)
            response_time = r.elapsed.total_seconds()
            finish_time = datetime.datetime.now().strftime('%Y%m%d-%H:%M:%S')
            tmp_dct = {}
            try:
                response_json = r.json()
            except Exception as err:
                response_json = {'response_text': r.text}
                logger.exception(f'json loads failed.')
                logger.error(f'full_url: {self.full_url}')
                logger.error(f'payload_dict = {self.payload_dict}')
                logger.error(f'method: {self.http_method}')
                logger.error(f'data_type: {self.data_type}')
                json_failed_error_msg = f'response.json() failed: {err} \nresponse text:\n{r.text}\n'
                logger.error(f'{json_failed_error_msg=}')
                tmp_dct['error_Http_Request'] = json_failed_error_msg
            if status_code != 200:
                logger.warning(f'waring: request status_code is {status_code}.')
            logger.info(f'full_url: {self.full_url}')
            logger.info(f'params_dct: {self.params_dict}')
            logger.info(f'http_method: {self.http_method}')
            logger.info(f'data_type: {self.data_type}')
            logger.info(f'payload_dct: {self.payload_dict}')
            logger.info(f'status_code: {r.status_code}')
            logger.info(f'{response_json=}')
            logger.info(f'{response_time=}')
            response_str = json.dumps(response_json, ensure_ascii=False)
            api_content = [self.request_url,
                           self.http_method.upper(),
                           self.data_type,
                           self.params_str,
                           self.payload_str,
                           self.request_length,
                           status_code,
                           response_str,
                           response_length,
                           response_time,
                           finish_time]
            request_info_dct = dict(zip(csv_headers, api_content))
            write_csv.record_request_csv(csvfile_path=csvfile_path,
                                         csv_row_data=request_info_dct,
                                         csv_headers=csv_headers)
            request_info_dct.update(tmp_dct)
            request_info_dct.update({'params_dct': self.params_dict,
                                     'payload_dct': self.payload_dict,
                                     'response_data': response_json
                                     }
                                    )
        except Exception as err:
            logger.error(f'{err=}')
            logger.error(f'{self.full_url=}')
            api_content = [self.request_url,
                           self.http_method.upper(),
                           self.data_type,
                           self.params_str,
                           self.payload_str,
                           None,  # request_length
                           0,  # status_code
                           err,  # response_data
                           None,  # response_length
                           0,  # response_time
                           None  # finish_time
                           ]
            request_info_dct = dict(zip(csv_headers, api_content))
            write_csv.record_request_csv(csvfile_path=csvfile_path,
                                         csv_row_data=request_info_dct,
                                         csv_headers=csv_headers)
            request_info_dct['error_Http_Request'] = err
            request_info_dct.update({'params_dct': self.params_dict,
                                     'payload_dct': self.payload_dict,
                                     'response_data': response_json
                                     }
                                    )
        finally:
            logger.info(f'{request_info_dct=}')
            return request_info_dct


if __name__ == '__main__':
    aa = AppApiBase()
    bb = AppApiBase()
    logger.debug(f'{session_dct=}')
    obj = AppApiBase(url='/v2/threads',
                     http_method='get',
                     payload_dict={'start': '1', 'limit': '25'}
                     )
    request_info_dct = obj.http_request()
    logger.debug(f'{request_info_dct=}')
    response_data = request_info_dct['response_data']
    logger.debug(f'{response_data=}')
    cc = AppApiBase(email='tester@yourapp.com', password='your-password', need_login=True)
