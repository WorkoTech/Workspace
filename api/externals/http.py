import os
import requests
import logging
import json
logger  = logging.getLogger(__name__)

from api.externals.errors import (
    ExternalUnreachableException,
    HttpException
)

class Http():
    __session = requests.Session()
    __TIMEOUT = os.getenv('HTTP_TIMEOUT', 1)

    @staticmethod
    def __get_headers(token=None):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        if not token is None:
            headers['Authorization'] = token
        return headers

    @staticmethod
    def __call(method, url, token=None, body=None):
        logger.info(f'[{method.upper()}] {url} body={json.dumps(body)} headers={Http.__get_headers(token)} auth={token != None}')
        try:
            response = getattr(Http.__session, method)(
                url,
                timeout=Http.__TIMEOUT,
                headers=Http.__get_headers(token),
                data=json.dumps(body)
            )
        except requests.ConnectionError as e:
            logger.error('Unable to reach external service : ', e)
            raise ExternalUnreachableException(e)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.info(f"Got response {response.text}")
            raise HttpException(e)

        return response

    @staticmethod
    def get(url, token=None):
        return Http.__call('get', url, token)

    @staticmethod
    def post(url, token=None, body=None):
        return Http.__call('post', url, token, body)

    @staticmethod
    def put(url, token=None, body=None):
        return Http.__call('put', url, token, body)

    @staticmethod
    def delete(url, token=None):
        return Http.__call('delete', url, token)
