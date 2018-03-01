import socket

from json import dumps as json_dumps, JSONEncoder
from time import sleep

from canaryd.log import logger
from canaryd.packages import requests
from canaryd.settings import get_settings
from canaryd.version import __version__

SESSION = None
REQUEST_TIMEOUT = 30


class CanaryJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)

        if hasattr(obj, 'serialise'):
            return obj.serialise()

        if hasattr(obj, 'isoformat'):
            return obj.isoformat()

        return JSONEncoder.default(self, obj)


def backoff(function, *args, **kwargs):
    data = None
    interval = 0

    error_message = kwargs.pop('error_message', 'API error')
    max_wait = kwargs.pop('max_wait', 300)

    while data is None:
        try:
            return function(*args, **kwargs)

        except ApiError as e:
            if interval + 10 <= max_wait:
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
            states_dict[plugin.name] = state

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
    settings = settings or get_settings()

    api_key = api_key or settings.api_key

    url = '{0}/v{1}/{2}'.format(
        settings.api_base,
        settings.api_version,
        endpoint,
    )

    logger.debug('Making API request: {0}'.format(url))

    if 'timeout' not in kwargs:
        kwargs['timeout'] = REQUEST_TIMEOUT

    if json:
        json_data = json_dumps(json, cls=CanaryJSONEncoder)
        kwargs['data'] = json_data
        kwargs['headers'] = {
            'Content-Type': 'application/json',
        }

        logger.debug('Request data: {0}'.format(json_data))

    try:
        response = method(
            url,
            auth=('api', api_key),
            **kwargs
        )

    # Connection errors and timeouts
    except requests.ConnectionError as e:
        raise ApiError(0, 'Could not connect to {0}: {1}'.format(url, e))

    # Read timeouts
    except requests.Timeout as e:
        raise ApiError(0, 'Timed out reading from {0}: {1}'.format(url, e))

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
    return make_api_request(
        get_session().get,
        'server/{0}/ping'.format(settings.server_id),
        settings=settings,
    )


def _upload_states_return_settings(url, states, settings, json=None):
    json = json or states

    if json is not states:
        json['states'] = states

    response_data = make_api_request(
        get_session().post, url,
        settings=settings,
        json=json,
        # Explicitly set the max (matching server) timeout for syncing states
        # to avoid any sync "thrashing".
        timeout=600,
    )

    return response_data['settings']


def sync_states(states, settings):
    '''
    Uploads a full state to api.servicecanary.com and returns any data sent back
    from the server (settings).
    '''

    return _upload_states_return_settings(
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

    return _upload_states_return_settings(
        'server/{0}/state'.format(settings.server_id),
        make_changes_dict(states),
        settings,
    )


def create_event(settings, plugin, type, description, data=None):
    return make_api_request(
        get_session().post,
        'server/{0}/event'.format(settings.server_id),
        settings=settings,
        json={
            'plugin': plugin,
            'type': type,
            'description': description,
            'data': data,
        },
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
