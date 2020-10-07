#!/usr/bin/env python
"""
Provides search engine implementations for use in app.py.
"""
import string
import abc
import csv
import time
from collections import namedtuple
from collections.abc import Iterable
import logging
import sys

from util import InvalidQueryError, Results, make_python_identifier

logger = logging.getLogger(__name__)


class SearchEngineBase(abc.ABC):
    """Base class for all search engines used by app.py"""

    @abc.abstractmethod
    def evaluate_query(self, query: str) -> Results:
        """Evaluates search query and returns Results object"""


class IndexSearchEngine(SearchEngineBase):
    """Abstract class for search engines using an index for the search mechanism.

       The search algorithm for this type of search engine relies on the creation of an index
       from a corpus of Documents, where each key in the index is a searchable term, and the
       corresponding values are the indexes of the corpus whose Documents 'match' the term.
       The index is built and held in memory upon instanciation of the class to allow for rapid
       querying.
    """

    def __init__(self, filepath, skiprows=None):
        logger.info(f'Initializing {self.__class__.__name__}')
        # TODO get the data into a db and access via SQLAlchemy
        self._load_corpus(filepath, skiprows)
        self._build_index()
        logger.info(f"Initialized {self}")

    def evaluate_query(self, query: str, sort_by: str = None) -> Results:
        """
        Search for and return results that match the terms in the query.

        For a search query consisting of multiple terms, the results will
        be the intersection of the results for the individual terms. Results
        can be sorted by any field by specifying 'sort_by'. An invalid query
        will raise.
        """
        t1 = time.time_ns()
        self._validate_query(query)
        query_clean = self._clean_string(query)  # clean the query in the same way as index was cleaned
        results = self._get_results(query_clean)
        if sort_by:
            results = self._sort_results(query_clean, results, sort_by)
        return Results(query=query, results=results, execution_time=time.time_ns() - t1)

    def _get_results(self, query: str) -> list:
        """
        Gets indices of documents that match query by lookup in the
        search term index. Indices are then used to retieve documents from
        corpus
        """
        idx_matchs_all = []
        for term in query.split():
            match = self._index.get(term, None)
            if match:
                idx_matchs_all.append(match)
        if not idx_matchs_all:
            return []
        idxs = set.intersection(*idx_matchs_all)
        return [self._corpus[idx] for idx in idxs]

    def _load_corpus(self, filepath, skiprows):
        """
        Loads a corpus from csv file

        Each row in the csv is considered an individual document. A document
        is represented by the namedtuple Document, which is defined within this
        method once the fields are known. This means we can add fields to
        the csv any they will be included in the search automatically
        """
        # TODO get the test_data into a db and access via SQLAlchemy. Won't have do
        #  define a namedtuple here anymore
        corpus = []
        with open(filepath, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            if skiprows:
                for _ in range(skiprows):
                    next(csv_reader)
            fields = next(csv_reader)
            Document = namedtuple('Document', [make_python_identifier(field) for field in fields])
            for document in csv_reader:
                corpus.append(Document(*document))
        self._corpus = corpus

    def _build_index(self):
        """
        The index is a dictionary whose keys are the searchable terms and the values
        are lists of ints representing the location of matching documents within
        the corpus. Fuzzy searching can be achieved by 'fuzzifing' each term within
        the corpus and adding the results to the index.
        """
        logger.debug('Building index')
        index = {}
        for idx, document in enumerate(self._corpus):
            text = ' '.join(document)
            text_cleaned = self._clean_string(text)  # Clean all text. Search terms should be cleaned in the same way
            for token in text_cleaned.split():
                for x in self._fuzzify(token):
                    index.setdefault(x, set()).add(idx)
        self._index = index
        logger.debug('Index built')

    def _clean_string(self, term: str) -> str:
        return term.lower().translate(str.maketrans('', '', string.punctuation))

    @abc.abstractmethod
    def _fuzzify(self, search_term: str) -> Iterable:
        """Implement method to create fuzzifications of search_term to store in index"""

    @abc.abstractmethod
    def _validate_query(self, query: str):
        raise InvalidQueryError

    @abc.abstractmethod
    def _sort_results(self, query, results, sort_by: str = None) -> Iterable:
        """Should return sorted results based on the given query and sort_by field"""

    def __repr__(self):
        return f"{self.__class__.__name__}: {int(self.__sizeof__() * 1e-6)}MB"

    def __sizeof__(self):
        size = 0
        size += sys.getsizeof(self._index)
        size += sys.getsizeof(self._corpus)
        # sys.getsizeof() doesnt work for nested data structures
        # so we need to look inside self._index and self._corpus
        for _, v in self._index.items():
            size += sys.getsizeof(v)
        for document in self._corpus:
            size += sys.getsizeof(document)
        return size


class FuzzySearchEngine(IndexSearchEngine):
    """Concrete subclass of IndexSearchEngine. Also implements cls.from_csv()"""

    def _fuzzify(self, word: str) -> list:
        """
        Implements a begins-with fuzzification methodology.

        Returns a list of strings where each string is the first n characters of
        the word for n in {3 .. len(word)}.
        e.g. 'abcdef' -> ['abc', 'abcd', 'abcde', 'abcdef']
        """
        words = [word[:n] for n in range(3, len(word) + 1)]
        words.append(word)
        return words

    def _validate_query(self, query: str, n: int = 3):
        if len(query.strip()) < n:
            raise InvalidQueryError(f"Query must be at least {n} characters")

    def _sort_results(self, query, results, sort_by: str = None) -> list:
        """
        Sorts results by sort_by column.

        The sorting is performed based on the position of the first occurence of
        first query term in the field to sort on.  e.g. The first occurence 'xyz'
        is at position 3 and 1 in the following strings:
        'xxxx xxxx xxxx XYZx xxxx'
        'xxxx xXYZ xxxx XYZx xxxx'
        See comments for a further description of the implementation
        """
        # Get the term to find and the column index of the search field
        term = query.split()[0]
        sort_by = make_python_identifier(sort_by)

        # Split the results into documents applicable for sorting and those that aren't
        to_sort = []
        the_rest = []
        for doc in results:
            try:
                text = getattr(doc, sort_by)
            except AttributeError:
                raise AttributeError(f"Could not sort by '{sort_by}'. Please use one of {doc._fields}")
            else:
                text_clean = self._clean_string(text)
                if term in text_clean:
                    to_sort.append(doc)
                else:
                    the_rest.append(doc)

        def sorter(doc) -> int:
            """Custom key function that is supplied to 'sorted()' to customize the sort order"""
            haystack = self._clean_string(getattr(doc, sort_by))
            # get all occurrences of term in haystack
            positions = [i for i, token in enumerate(haystack.split()) if term in token]
            return positions[0]

        sorted_docs = sorted(to_sort, key=sorter)
        sorted_docs.extend(the_rest)
        return sorted_docs
