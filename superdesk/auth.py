
from functools import wraps
from base64 import b64decode
from flask import request, make_response

import superdesk

def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if get_auth_token():
            return f(*args, **kwargs)
        restful.abort(401)
    return wrapper

def create_token(user, db=superdesk.db):
    token_id = utils.get_random_string(40)
    token = {
        'token': token_id,
        'user': {
            'username': user.get('username')
        }
    }

    db.tokens.save(token)
    return token

def get_auth_token(db=superdesk.db):
    """Get token data for token in Authorization header"""
    token = b64decode(request.headers.get('Authorization', '').replace('Basic ', ''))[:40]
    return db.tokens.find_one({'token': token.decode('ascii')})

def authenticate(db=superdesk.db, **kwargs):
    if 'username' not in kwargs:
        raise AuthException("invalid credentials")

    user = db.users.find_one({'username': kwargs.get('username')})
    if not user:
        raise AuthException("username not found")

    if user.get('password') != kwargs.get('password'):
        raise AuthException("invalid credentials")

    return user

class AuthException(Exception):
    pass

class AuthResource(object):

    @auth_required
    def get(self):
        return get_auth_token()

    def post(self):
        try:
            user = authenticate(**request.get_json())
            token = create_token(user)
            return token, 201
        except AuthException as err:
            return {'message': err.args[0], 'code': 401}, 401

superdesk.DOMAIN.update({
    'auth': {
        'schema': {
            'username': {
                'type': 'string'
            },
            'password': {
                'type': 'string'
            }
        },
        'item_methods': []
    }
})