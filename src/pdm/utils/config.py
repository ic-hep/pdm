"""Configuration System Module."""
import ast
import logging
from os.path import abspath, realpath, expanduser, expandvars
from copy import deepcopy
from ConfigParser import SafeConfigParser
from collections import defaultdict

from .singleton import singleton


@singleton
class ConfigSystem(object):
    """Config system singleton."""

    def __init__(self):
        """Initialisation."""
        self._config = defaultdict(dict)
        self._logger = logging.getLogger(__name__)

    @property
    def config(self):
        """The current state of the configuration."""
        return dict(deepcopy(self._config))

    @property
    def sections(self):
        """Get list of sections."""
        return self._config.keys()

    def get_section(self, section):
        """Return a given section."""
        return deepcopy(self._config[section])

    def setup(self, filenames='~/.config/pdm/pdm.conf'):
        """Setup the configuration system."""
        config_parser = SafeConfigParser()
        config_parser.optionxform = str

        if isinstance(filenames, basestring):
            filenames = [filenames]
        filenames = {abspath(realpath(expanduser(expandvars(filename))))
                     for filename in filenames}

        read_files = config_parser.read(filenames)

        if read_files:
            self._logger.info("Read config files: %s", read_files)

        for skipped_file in filenames.difference(read_files):
            self._logger.warning("Failed to read config file: %s ... file skipped!",
                                 skipped_file)

        for section in config_parser.sections():
            self._config[section].update((key, ast.literal_eval(val))
                                         for key, val in config_parser.items(section))


def getConfig(section):  # pylint: disable=invalid-name
    """
    Get config helper function.

    Return the config for the given section.
    """
    return ConfigSystem.get_instance().get_section(section)  # pylint: disable=no-member
