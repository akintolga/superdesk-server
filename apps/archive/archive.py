from apps.auth.errors import ForbiddenError

SOURCE = 'archive'

import flask
from superdesk.io import get_word_count
from superdesk.resource import Resource
from .common import extra_response_fields, item_url, aggregations, remove_unwanted, update_state
from .common import on_create_item, on_create_media_archive, on_update_media_archive, on_delete_media_archive
from .common import get_user
from flask import current_app as app
from werkzeug.exceptions import NotFound
<<<<<<< HEAD
from superdesk import SuperdeskError, get_resource_service
=======
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
>>>>>>> [SD-1297] Refactoring API (HTTP) errors
from superdesk.utc import utcnow
from eve.versioning import resolve_document_version
from superdesk.activity import add_activity, ACTIVITY_CREATE, ACTIVITY_UPDATE, ACTIVITY_DELETE
from eve.utils import parse_request, config
from superdesk.services import BaseService
from apps.content import metadata_schema
from apps.common.components.utils import get_component
from apps.item_autosave.components.item_autosave import ItemAutosave
from apps.common.models.base_model import InvalidEtag
from apps.legal_archive.components.legal_archive_proxy import LegalArchiveProxy
from copy import copy
import superdesk


def get_subject(doc1, doc2=None):
    for key in ('headline', 'subject', 'slugline'):
        value = doc1.get(key)
        if not value and doc2:
            value = doc2.get(key)
        if value:
            return value


def private_content_filter():
    """Filter out out users private content if this is a user request.

    As private we treat items where user is creator, last version creator,
    or has the item assigned to him atm.
    """
    user = getattr(flask.g, 'user', None)
    if user:
        return {'or': [
            {'exists': {'field': 'task.desk'}},
            {'term': {'task.user': str(user['_id'])}},
            {'term': {'version_creator': str(user['_id'])}},
            {'term': {'original_creator': str(user['_id'])}},
        ]}


class ArchiveVersionsResource(Resource):
    schema = metadata_schema
    extra_response_fields = extra_response_fields
    item_url = item_url
    resource_methods = []
    internal_resource = True
    privileges = {'PATCH': 'archive'}


class ArchiveVersionsService(BaseService):

    def on_create(self, docs):
        for doc in docs:
            doc['versioncreated'] = utcnow()


class ArchiveResource(Resource):
    schema = {
        'old_version': {
            'type': 'number',
        },
        'last_version': {
            'type': 'number',
        },
        'task': {'type': 'dict'}
    }
    schema.update(metadata_schema)
    extra_response_fields = extra_response_fields
    item_url = item_url
    datasource = {
        'search_backend': 'elastic',
        'aggregations': aggregations,
        'projection': {
            'old_version': 0,
            'last_version': 0
        },
        'default_sort': [('_updated', -1)],
        'elastic_filter_callback': private_content_filter
    }
    resource_methods = ['GET', 'POST']
    item_methods = ['GET', 'PATCH', 'PUT']
    versioning = True
    privileges = {'POST': 'archive', 'PATCH': 'archive', 'PUT': 'archive'}


def update_word_count(doc):
    """Update word count if there was change in content.

    :param doc: created/udpated document
    """
    if doc.get('body_html'):
        doc.setdefault('word_count', get_word_count(doc.get('body_html')))


class ArchiveService(BaseService):

    def on_create(self, docs):
        on_create_item(docs)

        for doc in docs:
            doc['version_creator'] = doc['original_creator']
            remove_unwanted(doc)
            update_word_count(doc)

    def on_created(self, docs):
        on_create_media_archive()
        get_component(LegalArchiveProxy).create(docs)
        for doc in docs:
            subject = get_subject(doc)
            if subject:
                msg = 'added new {{ type }} item about "{{ subject }}"'
            else:
                msg = 'added new {{ type }} item with empty header/title'
            add_activity(ACTIVITY_CREATE, msg, item=doc, type=doc['type'], subject=subject)

    def on_update(self, updates, original):
        user = get_user()

        if 'unique_name' in updates and (user['active_privileges'].get('metadata_uniquename', 0) == 0):
            raise ForbiddenError("Unauthorized to modify Unique Name")

        remove_unwanted(updates)

        if self.__is_req_for_save(updates):
            update_state(original, updates)

        lock_user = original.get('lock_user', None)
        force_unlock = updates.get('force_unlock', False)

        original_creator = updates.get('original_creator', None)
        if not original_creator:
            updates['original_creator'] = original['original_creator']

        str_user_id = str(user.get('_id'))
        if lock_user and str(lock_user) != str_user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError(payload='The item was locked by another user')

        updates['versioncreated'] = utcnow()
        updates['version_creator'] = str_user_id
        update_word_count(updates)

        if force_unlock:
            del updates['force_unlock']

    def on_updated(self, updates, original):
        get_component(ItemAutosave).clear(original['_id'])
        get_component(LegalArchiveProxy).update(original, updates)
        on_update_media_archive()

        if '_version' in updates:
            updated = copy(original)
            updated.update(updates)
            add_activity(ACTIVITY_UPDATE, 'created new version {{ version }} for item {{ type }} about "{{ subject }}"',
                         item=updated, version=updates['_version'], subject=get_subject(updates, original),
                         type=updated['type'])

    def on_replace(self, document, original):
        remove_unwanted(document)
        user = get_user()
        lock_user = original.get('lock_user', None)
        force_unlock = document.get('force_unlock', False)
        user_id = str(user.get('_id'))
        if lock_user and str(lock_user) != user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError(payload='The item was locked by another user')
        document['versioncreated'] = utcnow()
        document['version_creator'] = user_id
        if force_unlock:
            del document['force_unlock']

    def on_replaced(self, document, original):
        get_component(ItemAutosave).clear(original['_id'])
        on_update_media_archive()

    def on_delete(self, doc):
        """Delete associated binary files."""

        if doc and doc.get('renditions'):
            for _name, ref in doc['renditions'].items():
                try:
                    app.media.delete(ref['media'])
                except (KeyError, NotFound):
                    pass

    def on_deleted(self, doc):
        on_delete_media_archive()
        add_activity(ACTIVITY_DELETE, 'removed item {{ type }} about {{ subject }}', item=doc,
                     type=doc['type'], subject=get_subject(doc))

    def replace(self, id, document):
        return self.restore_version(id, document) or \
            super().replace(id, document)

    def restore_version(self, id, doc):
        item_id = id
        old_version = int(doc.get('old_version', 0))
        last_version = int(doc.get('last_version', 0))
        if(not all([item_id, old_version, last_version])):
            return None

        old = get_resource_service('archive_versions').find_one(req=None, _id_document=item_id, _version=old_version)
        if old is None:
            raise SuperdeskApiError.notFoundError(payload='Invalid version %s' % old_version)

        curr = get_resource_service(SOURCE).find_one(req=None, _id=item_id)
        if curr is None:
            raise SuperdeskApiError.notFoundError(payload='Invalid item id %s' % item_id)

        if curr[config.VERSION] != last_version:
            raise SuperdeskApiError.preconditionFailedError(payload='Invalid last version %s' % last_version)
        old['_id'] = old['_id_document']
        old['_updated'] = old['versioncreated'] = utcnow()
        del old['_id_document']

        resolve_document_version(old, 'archive', 'PATCH', curr)

        remove_unwanted(old)
        res = super().replace(id=item_id, document=old)

        del doc['old_version']
        del doc['last_version']
        doc.update(old)
        return res

    def __is_req_for_save(self, doc):
        """
        Patch of /api/archive is being used in multiple places. This method differentiates from the patch
        triggered by user or not.
        """

        if 'req_for_save' in doc:
            req_for_save = doc['req_for_save']
            del doc['req_for_save']

            return req_for_save == 'true'

        return True


class AutoSaveResource(Resource):
    endpoint_name = 'archive_autosave'
    item_url = item_url
    schema = {
        '_id': {'type': 'string'}
    }
    schema.update(metadata_schema)
    resource_methods = ['POST']
    item_methods = ['GET', 'PUT', 'PATCH']
    resource_title = endpoint_name
    privileges = {'POST': 'archive', 'PATCH': 'archive', 'PUT': 'archive'}


class ArchiveSaveService(BaseService):

    def create(self, docs, **kwargs):
        if not docs:
            raise SuperdeskApiError.notFoundError('Content is missing', 400)
        req = parse_request(self.datasource)
        try:
            get_component(ItemAutosave).autosave(docs[0]['_id'], docs[0], get_user(required=True), req.if_match)
        except InvalidEtag:
            raise SuperdeskApiError.preconditionFailedError('Client and server etags don\'t match', 412)
        return [docs[0]['_id']]


superdesk.workflow_state('in_progress')
superdesk.workflow_action(
    name='save',
    include_states=['draft', 'fetched', 'routed', 'submitted'],
    privileges=['archive']
)

superdesk.workflow_state('submitted')
superdesk.workflow_action(
    name='move',
    exclude_states=['ingested', 'spiked', 'on-hold', 'published', 'killed'],
    privileges=['archive']
)
