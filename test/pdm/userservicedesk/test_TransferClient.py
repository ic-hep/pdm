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

    ##@mock.patch.object(HRService, 'check_token')
    @mock.patch.object(Tokens.TokenService, 'unpack')
    @mock.patch("pdm.userservicedesk.HRService.CredClient")
    @mock.patch("pdm.userservicedesk.TransferClient.EndpointClient")
    @mock.patch("pdm.workqueue.WorkqueueClient.WorkqueueClient.__new__")
    def setUp(self, wq_mock, endp_mock, cred_mock, mocked_unpack):
        cred_mock.return_value = MockCredClient()
        endp_mock.return_value = MockEndpointClient()
        endp_mock.return_value.set_token = mock.MagicMock()

        endp_mock.return_value.add_site('localhost', 'test localhost site')
        endp_mock.return_value.add_site('remotehost', 'test remotehost site')
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

        # mock_ct.return_value =1

        mocked_unpack.return_value = token
        self.__htoken = 'whateverhash'
        self.__client = TransferClientFacade(self.__htoken)
        assert wq_mock.called
        mocked_unpack.assert_called_with(self.__htoken)

    # @mock.patch("pdm.userservicedesk.TransferClient.WorkqueueClient.list")
    @mock.patch("pdm.userservicedesk.TransferClient.CredClient")
    def test_list(self, tc_cred_mock):
        tc_cred_mock.return_value = MockCredClient()
        tc_cred_mock.return_value.set_token = mock.MagicMock()
        tc_cred_mock.return_value.add_cred = mock.MagicMock(return_value=('private_key', 'public_key'))

        site = "localhost:/root/file.txt"
        # parts = urlparse(url)
        # mock_list.return_value = 'root/file.txt'
        with mock.patch.object(self.__client._TransferClient__wq_client, 'list') as mock_list:
            mock_list.return_value = 'root/file.txt'
            assert self.__client.list(site, **{'priority': 2}) == 'root/file.txt'
        assert mock_list.called
        mock_list.assert_called_with(self.site_id, '/root/file.txt', ('private_key', 'public_key'),
                                     priority=2)
        print mock_list.call_args_list

        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'list') as mock_list:
            mock_list.return_value = 'root/file.txt'  # event if ...
            assert self.__client.list(wrongurl, **{'priority': 2}) == None  # we return None
        assert not mock_list.called

    def test_sitelist(self):
        sites = self.__client.list_sites()
        print sites
        assert sites[0]['site_name'] == 'localhost'
        assert sites[1]['site_name'] == 'remotehost'
        assert 'site_id' not in [dd.keys() for dd in sites]

    @mock.patch("pdm.userservicedesk.TransferClient.CredClient")
    def test_remove(self, tc_cred_mock):
        tc_cred_mock.return_value = MockCredClient()
        tc_cred_mock.return_value.set_token = mock.MagicMock()
        tc_cred_mock.return_value.add_cred = mock.MagicMock(return_value=('private_key', 'public_key'))

        site = "localhost:/root/file.txt"
        # mock_remove.return_value = 'root/file.txt'
        with mock.patch.object(self.__client._TransferClient__wq_client, 'remove') as mock_remove:
            mock_remove.return_value = 'root/file.txt removed'
            assert self.__client.remove(site, **{'priority': 2}) == 'root/file.txt removed'
        assert mock_remove.called
        mock_remove.assert_called_with(self.site_id, '/root/file.txt', ('private_key', 'public_key'),
                                       priority=2)
        print mock_remove.call_args_remove

        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'remove') as mock_remove:
            mock_remove.return_value = 'whatever..'  # event if ...
            assert self.__client.remove(wrongurl, **{'priority': 2}) == None  # we return None
        assert not mock_remove.called

    @mock.patch("pdm.userservicedesk.TransferClient.CredClient")
    def test_copy(self, tc_cred_mock):
        tc_cred_mock.return_value = MockCredClient()
        tc_cred_mock.return_value.set_token = mock.MagicMock()
        tc_cred_mock.return_value.add_cred = mock.MagicMock(return_value=('private_key', 'public_key'))

        s_site = "localhost:/root/file.txt"
        t_site = "remotehost:/root/file.txt"

        with mock.patch.object(self.__client._TransferClient__wq_client, 'copy') as mock_copy:
            mock_copy.return_value = 'root/file.txt copied'
            assert self.__client.copy(s_site, t_site,
                                      **{'priority': 2}) == 'root/file.txt copied'
        assert mock_copy.called
        mock_copy.assert_called_with(self.site_id, '/root/file.txt',
                                     self.site2_id, '/root/file.txt',
                                     ('private_key', 'public_key'),
                                     priority=2)
        print mock_copy.call_args_copy

        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'copy') as mock_copy:
            mock_copy.return_value = 'whatever..'  # event if ...
            assert self.__client.copy(wrongurl, t_site,
                                      **{'priority': 2}) == None  # we return None
        assert not mock_copy.called

    def test_split_site_path(self):
        site = "localhost:/root/file.txt"
        malformed_site = "localhost/root/file.txt" # mind a missing colon
        multicolon_site = "localhost:/root/file.txt:1"

        a, b = TransferClientFacade.split_site_path(site)
        assert a == 'localhost'
        assert b == '/root/file.txt'

        c, d  = TransferClientFacade.split_site_path(malformed_site)
        assert d is None
        assert c is None

        e, f  = TransferClientFacade.split_site_path(multicolon_site)
        assert e == 'localhost'
        assert f == '/root/file.txt:1'


    def tearDown(self):
        pass
