import unittest
import datetime
from pdm.framework.Tokens import TokenService
from pdm.userservicedesk.HRUtils import HRUtils

class TestHRUtils(unittest.TestCase):

    def setUp(self):

        self.__future_date = (datetime.timedelta(0, 600) + datetime.datetime.utcnow()).isoformat()
        plain = {'id': 44, 'expiry': self.__future_date}
        svc = TokenService()
        self._validtoken = svc.issue(plain)

        __past_date = (-datetime.timedelta(0, 60) + datetime.datetime.utcnow()).isoformat()
        plain_expired = {'id': 44, 'expiry': __past_date}
        self._expiredtoken = svc.issue(plain_expired)

        plain_incomplete = {'id': 44}
        self._incomplete = svc.issue(plain_incomplete)

    def test_is_token_expired_insecure(self):
        assert not HRUtils.is_token_expired_insecure(self._validtoken)
        assert HRUtils.is_token_expired_insecure(self._expiredtoken)
        assert HRUtils.is_token_expired_insecure(self._incomplete)

    def test_get_token_expiry_insecure(self):
        assert HRUtils.get_token_expiry_insecure(self._validtoken) ==  self.__future_date

