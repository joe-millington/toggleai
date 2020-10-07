import json

import requests


def test_good_request():
    r = requests.get('http://127.0.0.1/?q=test')
    respose = json.loads(r.text)
    assert 'data' in respose.keys()


def test_bad_request():
    response = requests.get('http://127.0.0.1/?q=te')
    respose = json.loads(response.text)
    assert 'errors' in respose.keys()
