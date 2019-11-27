import os
import yaml
import collections

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


from bitwarden_pyro.util.logger import ProjectLogger
from bitwarden_pyro.model.actions import ItemActions, WindowActions
from bitwarden_pyro.settings import NAME


class ConfigLoader:
    _default_values = {
        'security': {
            'timeout': 900,  # Session expiry in seconds
            'clear': 5      # Clipboard persistency in seconds
        },
        'keyboard': {
            'enter': str(ItemActions.COPY),
            'type_password': {
                'key': 'Alt+1',
                'hint': 'Type password',
                'show': True
            },
            'type_all': {
                'key': 'Alt+2',
                'hint': 'Type all',
                'show': True
            },
            'mode_uris': {
                'key': 'Alt+u',
                'hint': 'Show URIs',
                'show': True
            },
            'mode_names': {
                'key': 'Alt+n',
                'hint': 'Show names',
                'show': True
            },
            'mode_logins': {
                'key': 'Alt+l',
                'hint': 'Show logins',
                'show': True
            },
            'mode_folders': {
                'key': 'Alt+c',
                'hint': 'Show folders',
                'show': True
            },
            'copy_totp': {
                'key': 'Alt+t',
                'hint': 'totp',
                'show': True
            },
            'sync': {
                'key': 'Alt+r',
                'hint': 'sync',
                'show': True
            }
        },
        'interface': {
            'hide_mesg': False,
            'window_mode': str(WindowActions.NAMES)
        }
    }

    _default_path = f'~/.config/{NAME}/config'

    def __init__(self, args):
        self._logger = ProjectLogger().get_logger()
        self._config = None

        self.__init_config(args)
        self.__init_converters()

    def __init_converters(self):
        self.add_converter('int', int)
        self.add_converter('boolean', bool)
        self.add_converter('windowaction', lambda a: WindowActions[a.upper()])
        self.add_converter('itemaction', lambda a: ItemActions[a.upper()])

    def __init_config(self, args):

        # Load default values from dict
        self._config = self._default_values

        # Command line arguments ovewrite default values and those
        # set by config file
        if not args.no_config:
            self.__from_file(args.config)
        else:
            self._logger.info("Preventing config file from loading")

        self.__from_args(args)

    def __from_args(self, args):
        if args.timeout is not None:
            self.set('security.timeout', args.timeout)
        if args.clear is not None:
            self.set('security.clear', args.clear)
        if args.enter is not None:
            self.set('keyboard.enter', args.enter)
        if args.window_mode is not None:
            self.set('interface.window_mode', args.window_mode)

    def __from_file(self, path):
        if path is None:
            path = self._default_path

        # Resolve to absolute path by either expanding '~' or
        # resolving the relative path
        if path[0] == '~':
            path = os.path.expanduser(path)
        else:
            path = os.path.abspath(path)

        self._logger.info("Loading config from %s", path)

        # If theere is no config file at the location specified
        # create one with default values
        if not os.path.isfile(path):
            self.__create_config(path)
        else:
            with open(path, 'r') as yaml_file:
                config = yaml.load(yaml_file, Loader=Loader)
                flat = self.__flatten_config(config)
                self.__insert_file(flat)

    def __insert_file(self, flat):
        for key, value in flat.items():
            self.set(key, value)

    # Source code adaptem from Imran on StackOverflow
    # https://stackoverflow.com/a/6027615
    def __flatten_config(self, config, parent_key='', sep='.'):
        items = []
        for k, v in config.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, collections.MutableMapping):
                items.extend(
                    self.__flatten_config(
                        v, new_key, sep=sep
                    ).items()
                )
            else:
                items.append((new_key, v))
        return dict(items)

    def __create_config(self, path):
        self._logger.debug("Creating new config from defaults")

        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        with open(path, 'w') as f:
            yaml.dump(self._config, f, Dumper=Dumper)

    def dump(self):
        flat = self.__flatten_config(self._config)
        lines = []
        for key, value in flat.items():
            lines.append(f"{key}={value}")

        return "\n".join(lines)

    def get(self, key):
        path = key.split('.')
        option = self._config.get(path[0])
        for idx, section in enumerate(path[1:]):
            if option is None:
                missing_path = ".".join(path[:idx])
                raise ConfigException(
                    f"Config key {missing_path} could not be found"
                )

            option = option.get(section)

        return option

    def set(self, key, value):
        path = key.split('.')

        # Test to see if the key is valid
        current = self.get(key)
        if current is None:
            raise ConfigException(f"Config key could not be set '{key}'")

        option = self._config.get(path[0])
        for section in path[1:-1]:
            option = option.get(section)

        if not isinstance(value, str):
            value = str(value)

        option[path[-1]] = value

    def add_converter(self, name, converter):
        def getter(self, key):
            raw = self.get(key)
            return converter(raw)

        getter.__name__ = f"get_{name}"
        setattr(self.__class__, getter.__name__, getter)

    @staticmethod
    def get_default(section, option):
        return ConfigLoader._default_values.get(section).get(option)


class ConfigException(Exception):
    """Base class for exceptions thrown by ConfigLoader"""
