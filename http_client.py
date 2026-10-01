import requests

def fetch_json(url:str)->dict:
    """
    请求接口并解析JSON：请求或解析失败时向调用者抛出异常。
    :param url:
    :return:
    """
    response=requests.get(url,timeout=10)
    response.raise_for_status()
    return response.json()