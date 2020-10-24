import requests


class ExternalUnreachableException(Exception):
    pass


class HttpException(requests.exceptions.HTTPError):
    pass
