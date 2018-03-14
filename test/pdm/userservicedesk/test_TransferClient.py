import mock
import unittest
from pdm.cred.CredClient import MockCredClient
from pdm.endpoint.EndpointClient import MockEndpointClient
from pdm.userservicedesk.TransferClientFacade import TransferClientFacade
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.userservicedesk.HRService import HRService
from pdm.cred.CredService import CredService
from urlparse import urlparse

import pdm.framework.Tokens as Tokens


class TestTransferClient(unittest.TestCase):
    # @mock.patch("pdm.workqueue.WorkqueueClient.WorkqueueClient")
    # @mock.patch("pdm.userservicedesk.TransferClient.WorkqueueClient")

    @mock.patch.object(Tokens.TokenService, 'unpack')
    @mock.patch("pdm.userservicedesk.HRService.CredClient")
    @mock.patch("pdm.userservicedesk.TransferClient.CredClient")
    @mock.patch("pdm.userservicedesk.TransferClient.EndpointClient")
    @mock.patch("pdm.workqueue.WorkqueueClient.WorkqueueClient.__new__")
    def setUp(self, wq_mock, endp_mock, tc_cred_mock, cred_mock, mocked_unpack):
        cred_mock.return_value = MockCredClient()
        tc_cred_mock.return_value = MockCredClient()
        tc_cred_mock.return_value.set_token = mock.MagicMock()
        tc_cred_mock.return_value.get_cred = mock.MagicMock(return_value=('private_key', 'public_key'))
        endp_mock.return_value = MockEndpointClient()
        endp_mock.return_value.set_token = mock.MagicMock()

        endp_mock.return_value.add_site('localhost:8080', 'test localhost site')
        self.site_id = endp_mock.return_value.get_sites()[0]['site_id']

        # self._wq_mock = wq_mock
        # self._wq_mock.return_value = mock.MagicMock()
        # self._wq_mock.return_value.list = mock.MagicMock()

        conf = {'CS_secret': 'HJGnbfdsV'}
        # HR
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)  # to skip DB auto build
        token = {'id': 1, 'expiry': None, 'key': 'unused'}

        self.__service.fake_auth("TOKEN", token)
        # database
        self.__service.build_db()  # build manually
        #
        db = self.__service.test_db()
        self.__service.before_startup(conf)  # to continue startup
        # CS
        """
        self.__csservice = FlaskServer("pdm.cred.CredService")
        self.__csservice.test_mode(CredService, None)  # to skip DB auto build
        #token = {'id':1, 'expiry':None, 'key': 'unused'}

        self.__csservice.fake_auth("TOKEN", token)
        # database
        self.__csservice.build_db()  # build manually
        #
        db = self.__csservice.test_db()
        self.__csservice.before_startup(conf)  # to continue startup
        """
        mocked_unpack.return_value = token
        self.__htoken = 'whateverhash'
        self.__client = TransferClientFacade(self.__htoken)
        assert wq_mock.called
        mocked_unpack.assert_called_with(self.__htoken)

    # @mock.patch("pdm.userservicedesk.TransferClient.WorkqueueClient.list")
    def test_list(self):
        url = "http://localhost:8080/root/file.txt"
        parts = urlparse(url)
        # mock_list.return_value = 'root/file.txt'
        with mock.patch.object(self.__client._TransferClient__wq_client, 'list') as mock_list:
            mock_list.return_value = 'root/file.txt'
            assert self.__client.list(url, **{'priority': 2}) == 'root/file.txt'  # **{'token':'hashgfsgg'}
        assert mock_list.called
        mock_list.assert_called_with(self.site_id, parts.path, ('private_key', 'public_key'), protocol=parts.scheme,
                                     priority=2)
        print mock_list.call_args_list
        # assert False

    def tearDown(self):
        pass
