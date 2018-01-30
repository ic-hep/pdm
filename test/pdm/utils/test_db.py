#!/usr/bin/env python
""" Test DB utils. """

import mock
import unittest

from pdm.utils.db import managed_session

class TestDBUtils(unittest.TestCase):
  """ Test all DB util functions. """

  def run_db_session(self, test_db):
      with managed_session(test_db) as db_session:
          self.assertEquals(db_session, test_db.session)

  def test_managed_session(self):
    """ Test managed_session generator. """
    test_db = mock.MagicMock()
    test_db.session = mock.MagicMock()
    # Check basic commit
    self.run_db_session(test_db)
    self.assertTrue(test_db.session.commit.called)
    self.assertFalse(test_db.session.rollback.called)
    test_db.session.commit.called = False # Reset
    # Check error case
    test_db.session.commit.side_effect = Exception("DB Error")
    self.assertRaises(Exception, self.run_db_session, test_db)
    self.assertTrue(test_db.session.commit.called)
    self.assertTrue(test_db.session.rollback.called)
    
