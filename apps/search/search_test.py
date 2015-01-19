# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.tests import TestCase
from eve.utils import ParsedRequest
from . import init_app
from apps.search import SearchService


def resource_listener(resource, docs):
    for doc in docs['_items']:
        doc['_resource_listener'] = resource


def ingest_listener(docs):
    for doc in docs['_items']:
        doc['_ingest_listener'] = 1


class SearchServiceTestCase(TestCase):

    def setUp(self):
        super().setUp()
        with self.app.app_context():
            self.app.data.insert('ingest', [{}])
            self.app.data.insert('archive', [{'task': {'desk': 1}}])
            init_app(self.app)
            self.app.on_fetched_resource += resource_listener
            self.app.on_fetched_resource_ingest += ingest_listener

    def test_query_post_processing(self):
        with self.app.app_context():
            docs = self.app.data.find('search', None, None)
            self.assertEquals(2, docs.count())

            ingest_docs = [doc for doc in docs if doc['_type'] == 'ingest']
            self.assertEquals('ingest', ingest_docs[0]['_resource_listener'])
            self.assertEquals(1, ingest_docs[0]['_ingest_listener'])

            archive_docs = [doc for doc in docs if doc['_type'] == 'archive']
            self.assertNotIn('_ingest_listener', archive_docs[0])

    def test_using_repo_request_attribute(self):
        with self.app.app_context():
            req = ParsedRequest()
            req.args = {'repo': 'ingest'}
            docs = self.app.data.find('search', req, None)
            self.assertEquals(1, docs.count())
            self.assertEquals('ingest', docs[0]['_type'])

    def test_it_filters_out_private_content(self):
        with self.app.app_context():
            self.app.data.insert('archive', [{'task': {'desk': None}}, {'task': {}}])
            cursor = self.app.data.find('search', None, None)
            self.assertEquals(2, cursor.count())

    def test_if_validates_query(self):
        with self.app.app_context():
            req = {'filtered': {'filter': {'and': [{'not': {'term': {'state': 'spiked'}}}]},
                                'query': {'query_string': {'lenient': False, 'default_operator': 'AND', 'query': '*'}}}}
            validation_result = SearchService().validate_query(req=req)
            self.assertTrue(validation_result['valid'])
