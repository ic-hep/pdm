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
        endp_mock.return_value.add_site('remotehost:8080', 'test remotehost site')
        self.site_id = endp_mock.return_value.get_sites()[0]['site_id']
        self.site2_id = endp_mock.return_value.get_sites()[1]['site_id']

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
            assert self.__client.list(url, **{'priority': 2}) == 'root/file.txt'
        assert mock_list.called
        mock_list.assert_called_with(self.site_id, parts.path, ('private_key', 'public_key'), protocol=parts.scheme,
                                     priority=2)
        print mock_list.call_args_list

        wrongurl = "http://localhost2:8080/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'list') as mock_list:
            mock_list.return_value = 'root/file.txt'  # event if ...
            assert self.__client.list(wrongurl, **{'priority': 2}) == None  # we return None
        assert not mock_list.called


    def test_remove(self):
        url = "http://localhost:8080/root/file.txt"
        parts = urlparse(url)
        # mock_remove.return_value = 'root/file.txt'
        with mock.patch.object(self.__client._TransferClient__wq_client, 'remove') as mock_remove:
            mock_remove.return_value = 'root/file.txt removed'
            assert self.__client.remove(url, **{'priority': 2}) == 'root/file.txt removed'
        assert mock_remove.called
        mock_remove.assert_called_with(self.site_id, parts.path, ('private_key', 'public_key'), protocol=parts.scheme,
                                       priority=2)
        print mock_remove.call_args_remove

        wrongurl = "http://localhost2:8080/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'remove') as mock_remove:
            mock_remove.return_value = 'whatever..'  # event if ...
            assert self.__client.remove(wrongurl, **{'priority': 2}) == None  # we return None
        assert not mock_remove.called

    def test_copy(self):
        surl = "http://localhost:8080/root/file.txt"
        turl = "http://remotehost:8080/root/file.txt"
        sparts = urlparse(surl)
        tparts = urlparse(surl)
        with mock.patch.object(self.__client._TransferClient__wq_client, 'copy') as mock_copy:
            mock_copy.return_value = 'root/file.txt copied'
            assert self.__client.copy(surl, turl,
                                      **{'priority': 2}) == 'root/file.txt copied'
        assert mock_copy.called
        mock_copy.assert_called_with(self.site_id, sparts.path, self.site2_id, tparts.path,
                                     ('private_key', 'public_key'), protocol=sparts.scheme,
                                     priority=2)
        print mock_copy.call_args_copy

        wrongurl = "http://localhost2:8080/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'copy') as mock_copy:
            mock_copy.return_value = 'whatever..'  # event if ...
            assert self.__client.copy(wrongurl, turl,
                                      **{'priority': 2}) == None # we return None
        assert not mock_copy.called

    def tearDown(self):
        pass
