"""Tests for the config utility."""
import unittest
from collections import defaultdict
from textwrap import dedent
from tempfile import NamedTemporaryFile

from pdm.utils.config import ConfigSystem, getConfig


class TestConfigSystem(unittest.TestCase):
    """Configuration system test class."""

    def setUp(self):
        """Set up the configuration system object and test objects."""
        self.cfg = ConfigSystem.get_instance()  # pylint: disable=no-member
        self.test_ref = defaultdict(dict, {'my_section': {'my_var_str': 'hello world',
                                                          'my_var_int': 12}})

    def test_initialisation(self):
        """Test initialisation."""
        namespace = vars(self.cfg)
        self.assertIn('_config', namespace)
        self.assertIsInstance(namespace['_config'], dict)

    def test_config(self):
        """Test config property."""
        self.cfg._config = self.test_ref
        self.assertEqual(self.cfg.config, self.test_ref)

    def test_get_section_list(self):
        """Test get section list."""
        self.cfg._config = self.test_ref
        self.assertEqual(self.cfg.sections, list(self.test_ref.keys()))

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
            tmpfile.write(dedent("""
            [my_section]
            my_var_str = 'hello world'
            my_var_int = 12
            """))
            tmpfile.flush()

            self.cfg._config.clear()
            self.cfg.setup(tmpfile.name)
            self.assertEqual(self.cfg._config, self.test_ref)

        # Test with no-existant file.
        with self.assertRaises(IOError):
            self.cfg.setup('blah')

        # Test corrupted config.
        with NamedTemporaryFile() as tmpfile:
            tmpfile.write("blah ][")
            tmpfile.flush()
            with self.assertRaises(Exception):
                self.cfg.setup(tmpfile.name)

        # Test ignore exceptions
        self.cfg.setup('blah', ignore_errors=True)

    def test_multi_configs(self):
        """Test reading in multiple configs."""
        with NamedTemporaryFile() as file1,\
             NamedTemporaryFile() as file2:
            file1.write(dedent("""
            [section_one]
            var_one = 12
            """))
            file1.flush()
            file2.write(dedent("""
            [section_two]
            var_two = 'hello world'
            """))
            file2.flush()

            # Test reading in individually
            self.cfg._config.clear()
            self.cfg.setup(file1.name)
            self.cfg.setup(file2.name)
            self.assertEqual(self.cfg.config,
                             {'section_one': {'var_one': 12},
                              'section_two': {'var_two': 'hello world'}})

            # Test reading in together
            self.cfg._config.clear()
            self.cfg.setup([file1.name, file2.name])
            self.assertEqual(self.cfg.config,
                             {'section_one': {'var_one': 12},
                              'section_two': {'var_two': 'hello world'}})
