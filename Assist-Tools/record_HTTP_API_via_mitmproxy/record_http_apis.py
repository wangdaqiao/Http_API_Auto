#!/usr/bin/env python3
from mitmproxy import http
from mitmproxy.tools.main import mitmdump
import json
import csv
import os
import sys
import time
import re
from urllib.parse import unquote, parse_qsl
from loguru import logger

try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    # avoid OverflowError on Windows: "Python int too large to convert to C long"
    csv.field_size_limit(2147483647)

host_lst = ['api.xxx.com', 'stageapi.xxx.com', '127.0.0.1', 'localhost',]


class Follower:
    """
    mitmproxy
    """
    def __init__(self):
        self.host_lst = host_lst
        self.records_dir = 'apirecord_dir'
        date_hour_minute_str = time.strftime("%Y%m%d_%H%M")
        logger.info(f'host_lst: {self.host_lst}')
        if not os.path.exists(self.records_dir):
            os.mkdir(self.records_dir)
        self.log_file = os.path.join(self.records_dir, f'apirecode_{date_hour_minute_str}.csv')
        logger.info(f'log to: {self.log_file}')
        logger.info('init...')

    def response(self, flow: http.HTTPFlow):
        # http.HTTPFlow # object of flow
        # flow.request.headers
        # flow.request.url  #url，include domain and request params but without in body content
        # flow.request.pretty_url # same with flow.request.url, seems not difference
        # flow.request.host  # domain name
        # flow.request.method # method. POST, GET, PATCH, PUT, ...
        # flow.request.scheme # http, https
        # flow.request.path # request path but without the domain name
        # flow.request.get_text() # Request body content, some will put the request parameters in the body, then you can get through this method, return the dictionary type
        # flow.request.query # Returns data of type MultiDictView, with key-value parameter of url
        # flow.request.get_content()  # bytes
        # flow.request.raw_content  # bytes
        # flow.request.urlencoded_form # MultiDictView，r request params when content-type is application/x-www-form-urlencoded, it does not contain the key parameters in the url
        # All the above are some common methods to get the request information, for the response, the same
        # flow.response.status_code
        # flow.response.text  # string, the return content
        # flow.response.content # bytes, the return content
        # flow.response.setText() # Modify the return content without transcoding
        #
        logger.debug(f'{flow.request.method=}  {flow.request.host=}')
        if flow.request.method not in ('GET', 'POST', 'PATCH', 'PUT', 'DELETE'):
            return
        # if flow.response.status_code not in range(200, 600):
        #     return
        if flow.request.host not in self.host_lst:
            return
        # logger.debug(f'{flow.request.path=}')
        # logger.debug(f'{flow.request.url=}')
        params_str = ''
        payload_str = ''
        upload_filename = ''
        skip_urls = ['/dataImport/parsing', '/dataImport/raw']
        request_url = flow.request.path.split("?")[0]
        if any(x in request_url for x in skip_urls):
            logger.debug(f'not record {request_url}')
            return
        # logger.warning(f'{flow.request.cookies=}')
        # logger.warning(f'{dict(flow.request.cookies)=}')
        # logger.warning(f'{flow.request.headers=}')
        # logger.warning(f'{dict(flow.request.headers)=}')
        method = flow.request.method
        # response_length = int(flow.response.headers.get('Content-Length', 0))
        response_length = len(flow.response.content)
        response_duration_time = round(flow.response.timestamp_end - flow.request.timestamp_start, 2)
        finish_time = time.strftime("%Y%m%d-%H:%M:%S", time.localtime())
        try:
            request_content_type = flow.request.headers['Content-Type']
        except KeyError:
            request_content_type = ''
        if r'application/json' in request_content_type:
            data_type = 'json'
        elif r'application/x-www-form-urlencoded' in request_content_type:
            data_type = "data"
        elif r'multipart/form-data' in request_content_type:
            data_type = 'file'
        else:
            data_type = 'params'
        if r'text/plain' in request_content_type or r'application/xml' in request_content_type:
            return
        # handle query
        query = flow.request.query
        if query:
            # may have multiple duplicate parameters, e.g. api.xxx.com/search?q=hi&q=world&lang=cn\
            # the query is MultiDictView[('q', 'hi'), ('q', 'world'), ('lang', 'cn')]
            if any(len(query.get_all(key)) > 1 for key in query):
                request_url = flow.request.path
            else:
                params_str = json.dumps(dict(query), ensure_ascii=False)
        # handle payload & upload file
        if data_type == "data" and method == 'POST':
            payload_str_unquote = unquote(flow.request.content.decode('utf-8'))
            pay_dct = dict(parse_qsl(payload_str_unquote, keep_blank_values=True))
            payload_str = json.dumps(pay_dct, ensure_ascii=False)
        elif data_type == 'file' and method == 'POST':
            request_body = flow.request.get_text()
            # Extract file names using regular expressions
            filename_pattern = r'filename="(.*?)"'
            match = re.search(filename_pattern, request_body)
            if match:
                upload_filename = match.group(1)
                logger.info(f"Extracted filename: {upload_filename}")
            else:
                logger.info("Failed to extract filename.")
        else:
            request_body = flow.request.get_text()
            logger.debug(f'{request_body=}')
            try:
                payload_str = json.dumps(json.loads(request_body),
                                         ensure_ascii=False) if request_body else request_body
            except Exception as err:
                logger.error(err)
                payload_str = request_body
        payload_length = len(payload_str) if payload_str else None
        response_content_type = flow.response.headers.get('Content-Type')
        if response_content_type != 'application/json':
            logger.info(f'{response_content_type=}')
            return
        status_code = flow.response.status_code
        response_text = flow.response.text
        # if response_length > 5000:
        #     response_text = None
        # flow.response.headers["BOOM"] = "boom!boom!boom!"
        try:
            response_text = json.dumps(json.loads(response_text), ensure_ascii=False)
        except Exception as err:
            logger.error(err)
            logger.error(response_text)
        # save api data to csv
        headers = ['request_url',
                   'host',
                   'status_code',
                   'method',
                   'data_type',
                   'params',
                   'payload',
                   'payload_length',
                   'upload_file',
                   'response_text',
                   'response_length',
                   'response_duration_time',
                   'finish_time'
                   ]
        api_content = [request_url,
                       flow.request.host,
                       status_code,
                       method,
                       data_type,
                       params_str,
                       payload_str,
                       payload_length,
                       upload_filename,
                       response_text,
                       response_length,
                       response_duration_time,
                       finish_time
                       ]
        logger.debug(f'will log: {request_url} {method} {response_duration_time=}')
        with open(self.log_file, "a", encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(dict(zip(headers, api_content)))


addons = [
    Follower()
]


def run():
    port = 8889
    logger.info(f"start mitmproxy service at port {port}...")
    pyself = os.path.realpath(__file__)
    mitmdump(['-q', '-s', f'{pyself}', '-p', f'{port}'])
    # os.system("mitmdump -q -s record_http_apis.py -p 8889")  # -q: block the console mitmdump log，only show the script log


if __name__ == '__main__':
    run()
