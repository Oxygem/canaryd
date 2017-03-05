import socket

from json import dumps as json_dumps, JSONEncoder
from time import sleep

from canaryd.log import logger
from canaryd.packages import requests
from canaryd.settings import CanarydSettings
from canaryd.version import __version__

SESSION = None


class CanaryJSONEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'serialise'):
            return obj.serialise()

        if hasattr(obj, 'isoformat'):
            return obj.isoformat()

        return JSONEncoder.default(self, obj)


def backoff(function, *args, **kwargs):
    data = None
    interval = 0

    error_message = kwargs.get('error_message', 'API error')

    while data is None:
        try:
            return function(*args)

        except ApiError as e:
            if interval <= 290:
                interval += 10

            e.log()

        logger.critical('{0}, retrying in {1}s'.format(error_message, interval))
        sleep(interval)


class ApiError(Exception):
    '''
    Generic exception for problems with the API.
    '''

    def __init__(self, status_code, name, message=None, content=None):
        self.status_code = status_code
        self.name = name
        self.message = message
        self.content = content

    def log(self):
        logger.critical(
            '{0}: {1}{2}'.format(
                self.status_code,
                self.name,
                '({0})'.format(self.message) if self.message else '',
            ),
        )

        if self.content:
            logger.debug('Response data: {0}'.format(self.content))


def get_session():
    global SESSION

    if not SESSION:
        SESSION = requests.Session()

    return SESSION


def make_states_dict(states):
    states_dict = {}

    for plugin, (status, state) in states:
        if status:
            states_dict[plugin.name] = plugin.serialise_state(state)

    return states_dict


def make_changes_dict(states):
    states_dict = {}
    for plugin, (status, changes) in states:
        if status:
            states_dict[plugin.name] = changes

    return states_dict


def make_api_request(
    method, endpoint,
    api_key=None, settings=None, json=None, **kwargs
):
    settings = settings or CanarydSettings()

    api_key = api_key or settings.api_key

    if json:
        kwargs['data'] = json_dumps(json, cls=CanaryJSONEncoder)
        kwargs['headers'] = {
            'Content-Type': 'application/json',
        }

    try:
        response = method(
            '{0}/v{1}/{2}'.format(
                settings.api_base,
                settings.api_version,
                endpoint,
            ),
            auth=('api', api_key),
            **kwargs
        )
    except requests.ConnectionError as e:
        raise ApiError(
            0,
            'Could not connect: {0}'.format(e),
        )

    # Try to get some response JSON data
    response_data = {}

    try:
        response_data = response.json()

    except ValueError:
        raise ApiError(
            response.status_code,
            'Invalid JSON response',
            content=response.content,
        )

    # Capture and re-raise any HTTP/API errors
    try:
        response.raise_for_status()

    except requests.HTTPError as e:
        raise ApiError(
            response.status_code,
            response_data.get('error_name', 'Unknown'),
            message=response_data.get('error_message', e),
            content=response_data,
        )

    return response_data


def ping(settings):
    response_data = make_api_request(
        get_session().get,
        'server/{0}/ping'.format(settings.server_id),
        settings=settings,
    )

    return response_data.get('ping') == 'pong'


def upload_states_return_settings(url, states, settings, json=None):
    json = json or states

    if json is not states:
        json['states'] = states

    response_data = make_api_request(
        get_session().post, url,
        settings=settings,
        json=json,
    )

    return response_data['settings']


def sync_states(states, settings):
    '''
    Uploads a full state to api.servicecanary.com and returns any data sent back
    from the server (settings).
    '''

    return upload_states_return_settings(
        'server/{0}/sync'.format(settings.server_id),
        make_states_dict(states),
        settings,
        json={
            'hostname': socket.gethostname(),
            'canaryd_version': __version__,
        },
    )


def upload_state_changes(states, settings):
    '''
    Uploads partial state to api.servicecanary.com.
    '''

    return upload_states_return_settings(
        'server/{0}/state'.format(settings.server_id),
        make_changes_dict(states),
        settings,
    )


def register(key):
    '''
    Register this server on api.servicecanary.com and return a server id.
    '''

    response_data = make_api_request(
        get_session().post,
        'servers',
        api_key=key,
        json={
            'hostname': socket.gethostname(),
            'canaryd_version': __version__,
        },
    )

    return response_data['server_id']


def signup(email):
    '''
    Signup for api.servicecanary.com and return the access key for that user.
    '''

    response_data = make_api_request(
        get_session().post,
        'signup',
        json={
            'email': email,
        },
    )

    if 'api_key' in response_data:
        return True, response_data['api_key']

    return False, response_data['info']
