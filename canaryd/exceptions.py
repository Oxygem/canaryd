from canaryd.packages.click import ClickException


class CanarydError(ClickException):
    '''
    Generic canaryd exception.
    '''

    def __init__(self, message='exiting!', *args, **kwargs):
        return super(CanarydError, self).__init__(message, *args, **kwargs)


class UserCancelError(CanarydError):
    '''
    Triggered when a user cancels an action.
    '''

    def __init__(self):
        return super(UserCancelError, self).__init__('User cancelled')


class ConfigError(CanarydError):
    '''
    Triggered when the config file is invalid/broken/missing.
    '''
