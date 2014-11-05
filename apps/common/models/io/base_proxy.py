from .data_layer import DataLayer
from eve.utils import ParsedRequest, config, document_etag
from eve import ID_FIELD


class BaseProxy(DataLayer):
    '''
    Data layer implementation used to connect the models to the data layer.
    Transforms the model data layer API into Eve data layer calls.
    '''
    def __init__(self, data_layer):
        self.data_layer = data_layer

    def etag(self, doc):
        return doc.get(config.ETAG, document_etag(doc))

    def find_one(self, resource, filter, projection):
        req = ParsedRequest()
        req.args = {}
        req.projection = projection
        return self.data_layer.find_one(resource, req, **filter)

    def find(self, resource, filter, projection, **options):
        req = ParsedRequest()
        req.args = {}
        req.projection = projection
        return self.data_layer.find(resource, req, filter)

    def create(self, resource, docs):
        return self.data_layer.create(resource, docs)

    def update(self, resource, filter, doc):
        return self._update(resource, filter, doc)

    def replace(self, resource, filter, doc):
        return self._update(resource, filter, doc, method='replace')

    def delete(self, resource, filter):
        return self.data_layer.delete(resource, filter)

    def _update(self, resource, filter, doc, method='update'):
        _id = doc.get(ID_FIELD, None)
        if ID_FIELD in doc:
            del doc[ID_FIELD]
        res = getattr(self.data_layer, method)(resource, filter[ID_FIELD], doc)
        if _id is not None:
            doc[ID_FIELD] = _id
        return res
