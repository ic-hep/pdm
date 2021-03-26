#!/usr/bin/env python
""" Test DB utils. """

import unittest
import unittest.mock as mock

from pdm.utils.db import managed_session

class TestDBUtils(unittest.TestCase):
  """ Test all DB util functions. """

  def run_db_session(self, test_request, **kwargs):
      with managed_session(test_request, **kwargs) as db_session:
          self.assertEqual(db_session, test_request.db.session)

  def test_managed_session(self):
    """ Test managed_session generator. """
    test_request = mock.MagicMock()
    test_request.db = mock.MagicMock()
    test_request.db.session = mock.MagicMock()
    # Check basic commit
    self.run_db_session(test_request)
    self.assertTrue(test_request.db.session.commit.called)
    self.assertFalse(test_request.db.session.rollback.called)
    test_request.db.session.commit.called = False # Reset
    # Check error case
    test_request.db.session.commit.side_effect = Exception("DB Error")
    self.assertRaises(Exception, self.run_db_session, test_request)
    self.assertTrue(test_request.db.session.commit.called)
    self.assertTrue(test_request.db.session.rollback.called)
    test_request.db.session.commit.called = False
    test_request.db.session.rollback.called = False
    # Check abort error case
    from werkzeug.exceptions import InternalServerError
    self.assertRaises(InternalServerError, self.run_db_session,
                      test_request, http_error_code=500)
    self.assertTrue(test_request.db.session.commit.called)
    self.assertTrue(test_request.db.session.rollback.called)
