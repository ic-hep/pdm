# pylint: disable=no-member
"""Tests for the singleton utility."""
import unittest

from pdm.utils.singleton import singleton, SingletonMeta, InstantiationError


class TestSingleton(unittest.TestCase):
    """Singleton test class."""

    def setUp(self):
        """Set up the singleton classes."""
        # explicit metaclass setup -> equivalent to setting __metaclass__
        self.cls_meta = SingletonMeta('test', (object,), {})
        # class decorator setup shoulf be equivalent to above
        self.cls_decor = singleton(type('test', (object,), {}))

    def test_meta_construction(self):
        """Test construction."""
        with self.assertRaises(InstantiationError):
            self.cls_meta()

    def test_decor_construction(self):
        """Test construction."""
        with self.assertRaises(InstantiationError):
            self.cls_decor()

    def test_meta_get_instance(self):
        """Test get_instance."""
        self.assertIs(self.cls_meta.get_instance(), self.cls_meta.get_instance())

    def test_decor_get_instance(self):
        """Test get_instance."""
        self.assertIs(self.cls_decor.get_instance(), self.cls_decor.get_instance())
