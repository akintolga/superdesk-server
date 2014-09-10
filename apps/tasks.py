from superdesk.models import BaseModel
from superdesk.notification import push_notification
from superdesk.utc import utcnow
from apps.archive.common import base_schema


def init_app(app):
    TaskModel(app=app)


class TaskModel(BaseModel):
    endpoint_name = 'tasks'
    datasource = {
        'source': 'archive',
        'default_sort': [('_updated', -1)],
        'filter': {'task': {'$exists': True}}
    }
    schema = {k: base_schema[k] for k in ('slugline', 'description_text', 'type', 'task')}
    schema.update({'planning_item': BaseModel.rel('planning', True, type='string')})

    def update_times(self, doc):
        task = doc.get('task', {})
        status = task.get('status', None)
        if status == 'in-progress':
            task.setdefault('started_at', utcnow())

        if status == 'done':
            task.setdefault('finished_at', utcnow())

    def on_create(self, docs):
        for doc in docs:
            self.update_times(doc)

    def on_update(self, updates, original):
        self.update_times(updates)

    def on_created(self, docs):
        push_notification(self.endpoint_name, created=1)

    def on_updated(self, updates, original):
        push_notification(self.endpoint_name, updated=1)

    def on_deleted(self, doc):
        push_notification(self.endpoint_name, deleted=1)