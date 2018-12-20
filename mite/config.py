from itertools import count
import logging
import os


logger = logging.getLogger()


class ConfigManager:
    """Shares config between runners"""
    def __init__(self):
        self._version_id_gen = count(1)
        self._version = 0
        self._config = {}
        self._runner_version_map = {}

    def _get_changes_since(self, version):
        for key, (value, value_version) in self._config.items():
            if value_version > version:
                yield key, value

    def get_changes_for_runner(self, runner_id):
        if runner_id not in self._runner_version_map:
            version = 0
        else:
            version = self._runner_version_map[runner_id]
        self._runner_version_map[runner_id] = self._version
        return list(self._get_changes_since(version))

    def set(self, name, value):
        self._version = next(self._version_id_gen)
        self._config[name] = (value, self._version)

    def __repr__(self):
        return "ConfigManager(version={}, {})".format(
            self._version, " ,".join(["{}={}".format(k, v) for k, v in self._config.items()]))

    def __str__(self):
        self.__repr__()


def default_config_loader():
    result = {}
    for name, value in os.environ.items():
        if name.startswith('MITE_CONF_'):
            key_name = name[10:]
            logger.info('Setting config from ENV variable [%s] %s=%r', name, key_name, value)
            result[key_name] = value
        if name.startswith('MITE_EVAL_CONF_'):
            key_name = name[15:]
            logger.info('Setting config from ENV variable and eval\'ing value [%s] %s=%r', name, key_name, value)
            result[key_name] = eval(value)
    return result
