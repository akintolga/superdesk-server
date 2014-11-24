import logging

from flask import current_app as app

from superdesk.activity import add_activity
from superdesk.services import BaseService
from superdesk.utils import is_hashed, get_hash
from superdesk import get_resource_service, SuperdeskError
from superdesk.emails import send_user_status_changed_email, send_activate_account_email
from superdesk.utc import utcnow
import superdesk

logger = logging.getLogger(__name__)


def get_display_name(user):
    if user.get('first_name') or user.get('last_name'):
        display_name = '%s %s' % (user.get('first_name', ''), user.get('last_name', ''))
        return display_name.strip()
    else:
        return user.get('username')


class UsersService(BaseService):

    def on_create(self, docs):
        for user_doc in docs:
            user_doc.setdefault('display_name', get_display_name(user_doc))

    def on_created(self, docs):
        for user_doc in docs:
            self.update_user_defaults(user_doc)
            add_activity('created user {{user}}', user=user_doc.get('display_name', user_doc.get('username')))

    def on_updated(self, updates, user):
        self.handle_status_changed(updates, user)

    def handle_status_changed(self, updates, user):
        status = updates.get('is_active', None)
        if status is not None and status != self.user_is_active(user):
            if not status:
                # remove active tokens
                get_resource_service('auth').delete_action({'username': user.get('username')})
            # send email notification
            send_email = get_resource_service('preferences').email_notification_is_enabled(user['_id'])
            if send_email:
                send_user_status_changed_email([user['email']], status)

    def on_deleted(self, doc):
        add_activity('removed user {{user}}', user=doc.get('display_name', doc.get('username')))

    def find_one(self, req, **lookup):
        doc = super().find_one(req, **lookup)
        if (doc is not None):
            self.set_privileges(doc)
        return doc

    def on_fetched(self, document):
        for doc in document['_items']:
            self.update_user_defaults(doc)

    def update_user_defaults(self, doc):
        """Set default fields for users"""
        doc.setdefault('display_name', get_display_name(doc))
        doc.pop('password', None)

    def user_is_waiting_activation(self, doc):
        return doc.get('needs_activation', False)

    def user_is_active(self, doc):
        return doc.get('is_active', False)

    def set_privileges(self, doc):
        role_id = doc.get('role', {})
        if role_id != {}:
            role = get_resource_service('roles').find_one(_id=role_id, req=None)
            role_privileges = role.get('privileges', {})
            doc['active_privileges'] = dict(list(role_privileges.items()) + list(doc.get('privileges', {}).items()))


class DBUsersService(UsersService):
    """
    Service class for UsersResource and should be used when AD is inactive.
    """

    def on_create(self, docs):
        super().on_create(docs)
        for doc in docs:
            if doc.get('password', None) and not is_hashed(doc.get('password')):
                doc['password'] = get_hash(doc.get('password'), app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12))

    def on_created(self, docs):
        """Send email to user with reset password token."""
        super().on_created(docs)
        resetService = get_resource_service('reset_user_password')
        activate_ttl = app.config['ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE']
        for doc in docs:
            if self.user_is_waiting_activation(doc):
                tokenDoc = {'user': doc['_id'], 'email': doc['email']}
                id = resetService.store_reset_password_token(tokenDoc, doc['email'], activate_ttl, doc['_id'])
                if not id:
                    raise SuperdeskError('Failed to send account activation email.')
                tokenDoc.update({'username': doc['username']})
                send_activate_account_email(tokenDoc)

    def on_update(self, updates, user):
        if updates.get('first_name') or updates.get('last_name'):
            updated_user = {'first_name': updates.get('first_name', ''),
                            'last_name': updates.get('last_name', ''),
                            'username': user.get('username', '')}
            updated_user.setdefault('first_name', user.get('first_name', ''))
            updated_user.setdefault('last_name', user.get('last_name', ''))
            updates['display_name'] = get_display_name(updated_user)

    def update_password(self, user_id, password):
        """
        Update the user password.
        Returns true if successful.
        """
        user = self.find_one(req=None, _id=user_id)

        if not user:
            raise SuperdeskError(payload='Invalid user.')

        if not self.user_is_active(user):
            raise SuperdeskError(status_code=403, message='Updating password is forbidden.')

        updates = {}
        updates['password'] = get_hash(password, app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12))
        updates[app.config['LAST_UPDATED']] = utcnow()
        if self.user_is_waiting_activation(user):
            updates['needs_activation'] = False

        self.patch(user_id, updates=updates)


class ADUsersService(UsersService):
    """
    Service class for UsersResource and should be used when AD is active.
    """

    readonly_fields = ['username', 'display_name', 'password', 'email', 'phone', 'first_name', 'last_name']

    def on_fetched(self, doc):
        super().on_fetched(doc)
        for document in doc['_items']:
            document['_readonly'] = ADUsersService.readonly_fields

    def on_fetched_item(self, doc):
        super().update_user_defaults(doc)
        doc['_readonly'] = ADUsersService.readonly_fields


class RolesService(BaseService):

    def on_update(self, updates, original):
        if updates.get('is_default'):
            # if we are updating the role that is already default that is OK
            if original.get('is_default'):
                return
            self.remove_old_default()

    def on_create(self, docs):
        for doc in docs:
            # if this new one is default need to remove the old default
            if doc.get('is_default'):
                self.remove_old_default()

    def on_delete(self, docs):
        if docs.get('is_default'):
            raise superdesk.SuperdeskError('Cannot delete the default role')

    def remove_old_default(self):
        # see of there is already a default role and set it to no longer default
        old = self.find_one(req=None, is_default=True)
        # make it no longer default
        if old:
            get_resource_service('roles').update(old.get('_id'), {"is_default": False})
