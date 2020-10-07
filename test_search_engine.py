import pytest
import configparser
import os

from engines import FuzzySearchEngine
from util import InvalidQueryError, convert_to_schema

current_dir = os.path.dirname(__file__)
config_path_rel = 'settings/config_test.ini'
config_path_abs = os.path.join(current_dir, config_path_rel)

config = configparser.ConfigParser()
config.read(config_path_abs)


@pytest.fixture()
def engine():
    yield FuzzySearchEngine(filepath=config['FILES']['CORPUS'], skiprows=1)


def test_invalid_query(engine):
    with pytest.raises(InvalidQueryError):
        engine.evaluate_query(query='aa')


def test_result_schema(engine):
    result = engine.evaluate_query('NotATerm')
    result = result.to_json()

    results_schema = {
        'meta': {
            'query': str,
            'execution_time_ms': float
        },
        "data": list
    }
    convert_to_schema(result)
    assert result == results_schema, "Json schema of Result.to_json() does not match required schema"


def test_empty_results(engine):
    result = engine.evaluate_query('NotATerm').to_json()
    assert len(result['data']) == 0


@pytest.mark.parametrize('query, expected', [
    ('FindMeA1', 'Document1'),
    ('FindMeB1', 'Document2'),
    ('FindMeC1', 'Document3'),
    ('FindMeD1', 'Document4'),
    ('Document5A', 'Document5A'),
])
def test_all_fields_searchable(engine, query, expected):
    result = engine.evaluate_query(query).to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == expected


def test_intersection(engine):
    result = engine.evaluate_query('FindMeA2 FindMeB2').to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == 'Document7'


def test_tokenize_fields(engine):
    result = engine.evaluate_query('FindMeA3').to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == 'Document9'


@pytest.mark.parametrize('query, expected', [
    ('ABC', 'Document10'),
    ('ABCD', 'Document10'),
    ('ABCDE', 'Document10'),
    ('ABCDEF', 'Document10'),
    ('ABCDEFG', 'Document10'),
    ('ABCDEFGH', 'Document10'),
    ('ABCDEFGHI', 'Document10'),
])
def test_starts_with(engine, query, expected):
    result = engine.evaluate_query(query).to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == expected


def test_case_insensitive(engine):
    result = engine.evaluate_query('FINDMEA5').to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == 'Document11'


def test_multiple_results(engine):
    result = engine.evaluate_query('FindMeA6').to_json()
    assert len(result['data']) == 2
    assert result['data'][0]['document'] == 'Document12'
    assert result['data'][1]['document'] == 'Document13'


def test_query_independence(engine):
    result = engine.evaluate_query('FindMeA7').to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == 'Document14'
    result = engine.evaluate_query('FindMeA8').to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == 'Document15'


def test_sort(engine):
    result = engine.evaluate_query('FindMeA9', sort_by='HeaderB').to_json()
    assert len(result['data']) == 3
    assert [doc['document'] for doc in result['data']] == ['Document18', 'Document17', 'Document16']


def test_fuzzy(engine):
    result = engine.evaluate_query('fuz').to_json()
    assert len(result['data']) == 1
    assert result['data'][0]['document'] == 'Document19'

