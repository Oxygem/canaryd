class ServiceMixin(object):
    @staticmethod
    def event_message(type_, key, data_changes):
        if type_ != 'updated':
            return

        if 'pid' in data_changes:
            return 'Service restarted: {0}'.format(key)

        if 'running' in data_changes:
            running = data_changes['running'][1]

            if running:
                return 'Service started: {0}'.format(key)
            else:
                return 'Service stopped: {0}'.format(key)
