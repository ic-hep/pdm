"""Tests for the config utility."""
import unittest
from textwrap import dedent
from tempfile import NamedTemporaryFile

from pdm.utils.config import ConfigSystem, getConfig


class TestConfigSystem(unittest.TestCase):
    """Configuration system test class."""

    def setUp(self):
        """Set up the configuration system object and test objects."""
        self.cfg = ConfigSystem.get_instance()  # pylint: disable=no-member
        self.test_ref = {'my_section': {'my_var_str': 'hello world',
                                        'my_var_int': 12}}
        self.test_cfg = dedent("""
        [my_section]
        my_var_str = 'hello world'
        my_var_int = 12
        """)

    def test_initialisation(self):
        """Test initialisation."""
        namespace = vars(self.cfg)
        self.assertIn('_config', namespace)
        self.assertIsInstance(namespace['_config'], dict)

    def test_config(self):
        """Test config property."""
        self.cfg._config = self.test_ref
        self.assertEqual(self.cfg.config, self.test_ref)

    def test_get_section(self):
        """Test getting a section."""
        self.cfg._config = self.test_ref
        self.assertEqual(self.cfg.get_section('my_section'), self.test_ref['my_section'])

    def test_getConfig(self):  # pylint: disable=invalid-name
        """Test getConfig helper function."""
        self.cfg._config = self.test_ref
        self.assertEqual(getConfig('my_section'), self.test_ref['my_section'])

    def test_setup(self):
        """Test the setup method."""
        with NamedTemporaryFile() as tmpfile:
            tmpfile.write(self.test_cfg)
            tmpfile.flush()
            self.cfg.setup(tmpfile.name)
            self.assertEqual(self.cfg._config, self.test_ref)
