"""Helper classes and functions for engines.py"""
import re
import keyword
from collections.abc import MutableMapping


class InvalidQueryError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class Results:
    """
    Wraps query, query execution time, results, fields and provides method
    to convert results into json schema
    """
    def __init__(self, query, results, execution_time):
        self._query = query
        self._data = results
        self._execution_time = execution_time * 1e-6

    @property
    def query(self):
        return self._query

    @property
    def data(self):
        return self._data

    @property
    def execution_time(self):
        return self._execution_time

    def to_json(self):
        obj = {
            'meta': {
                'query': self.query,
                'execution_time_ms': self.execution_time
            },
            'data': [
                dict(zip(document._fields, document)) for document in self.data
            ]
        }
        return obj

    def __len__(self):
        return len(self.data)


def make_python_identifier(string):
    s = string.lower()
    s = s.strip()
    # Make spaces into underscores
    s = re.sub('[\\s\\t\\n]+', '_', s)
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '', s)
    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '', s)
    # Check that the string is not a python identifier
    while s in keyword.kwlist:
        s += '_1'
    return s


def convert_to_schema(json_like):
    """
    Replaces all dict values to their types. Operates inplace.
    """
    for key, value in json_like.items():
        if isinstance(value, MutableMapping):
            convert_to_schema(value)
        else:
            json_like[key] = type(value)
