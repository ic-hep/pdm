import mock
import unittest
import datetime
from pdm.userservicedesk.TransferClientFacade import TransferClientFacade
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.userservicedesk.HRService import HRService

import pdm.framework.Tokens as Tokens


class TestTransferClient(unittest.TestCase):
    # @mock.patch("pdm.workqueue.WorkqueueClient.WorkqueueClient")
    # @mock.patch("pdm.userservicedesk.TransferClient.WorkqueueClient")

    ##@mock.patch.object(HRService, 'check_token')
    @mock.patch("pdm.userservicedesk.HRService.SiteClient")
    @mock.patch.object(Tokens.TokenService, 'unpack')
    @mock.patch("pdm.userservicedesk.TransferClient.SiteClient")
    @mock.patch("pdm.workqueue.WorkqueueClient.WorkqueueClient.__new__")
    def setUp(self, wq_mock, site_mock, mocked_unpack, hr_site_client_mock):
        self.__future_date = (datetime.timedelta(0, 600) + datetime.datetime.utcnow()).isoformat()

        site_mock().get_sites.return_value = \
            [{'site_id': 1, 'site_name': 'localhost', 'site_desc': 'test localhost site'},
             {'site_id': 2, 'site_name': 'remotehost', 'site_desc': 'test remotehost site'}]

        site_mock.return_value.set_token = mock.MagicMock()

        self.site_id = site_mock().get_sites()[0]['site_id']
        self.site2_id = site_mock().get_sites()[1]['site_id']

        conf = {'CS_secret': 'HJGnbfdsV',
                'smtp_server': 'localhost',
                'verification_url': 'https://pdm.grid.hep.ph.ic.ac.uk:5443/web/verify',
                'smtp_server_login': 'centos@localhost',
                'smtp_starttls': 'OPTIONAL',
                'smtp_login_req': 'OPTIONAL',
                'display_from_address': 'PDM mailer <centos@localhost>',
                'mail_subject': 'PDM registration - please verify your email address.',
                'mail_expiry': '12:00:00',
                'mail_token_secret': 'somemailsecretstring'}
        # HR
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)  # to skip DB auto build
        token = {'id': 1, 'expiry': self.__future_date}

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

    def test_list(self):
        site = "localhost:/root/file.txt"

        with mock.patch.object(self.__client._TransferClient__wq_client, 'list') as mock_list:
            mock_list.return_value = 'root/file.txt'
            assert self.__client.list(site, **{'priority': 2}) == 'root/file.txt'
        assert mock_list.called
        mock_list.assert_called_with(self.site_id, '/root/file.txt',
                                     priority=2)
        print(mock_list.call_args_list)

        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'list') as mock_list:
            mock_list.return_value = 'root/file.txt'  # event if ...
            assert self.__client.list(wrongurl, **{'priority': 2}) == []  # we return []
        assert not mock_list.called

    def test_sitelist(self):
        sites = self.__client.list_sites()
        print(sites)
        assert sites[0]['site_name'] == 'localhost'
        assert sites[1]['site_name'] == 'remotehost'
        assert 'site_id' not in [list(dd.keys()) for dd in sites]

    def test_remove(self):
        site = "localhost:/root/file.txt"
        # mock_remove.return_value = 'root/file.txt'
        with mock.patch.object(self.__client._TransferClient__wq_client, 'remove') as mock_remove:
            mock_remove.return_value = 'root/file.txt removed'
            assert self.__client.remove(site, **{'priority': 2}) == 'root/file.txt removed'
        assert mock_remove.called
        mock_remove.assert_called_with(self.site_id, '/root/file.txt',
                                       priority=2)
        print(mock_remove.call_args_remove)

        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'remove') as mock_remove:
            mock_remove.return_value = 'whatever..'  # event if ...
            assert self.__client.remove(wrongurl, **{'priority': 2}) == None  # we return None
        assert not mock_remove.called

    def test_copy(self):
        s_site = "localhost:/root/file.txt"
        t_site = "remotehost:/root/file.txt"

        with mock.patch.object(self.__client._TransferClient__wq_client, 'copy') as mock_copy:
            mock_copy.return_value = 'root/file.txt copied'
            assert self.__client.copy(s_site, t_site,
                                      **{'priority': 2}) == 'root/file.txt copied'
        assert mock_copy.called
        mock_copy.assert_called_with(self.site_id, '/root/file.txt',
                                     self.site2_id, '/root/file.txt',
                                     priority=2)

        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'copy') as mock_copy:
            mock_copy.return_value = 'whatever..'  # even if ...
            assert self.__client.copy(wrongurl, t_site,
                                      **{'priority': 2}) == None  # we return None
        assert not mock_copy.called

    def test_split_site_path(self):
        site = "localhost:/root/file.txt"
        malformed_site = "localhost/root/file.txt"  # mind a missing colon
        multicolon_site = "localhost:/root/file.txt:1"

        a, b = TransferClientFacade.split_site_path(site)
        assert a == 'localhost'
        assert b == '/root/file.txt'

        c, d = TransferClientFacade.split_site_path(malformed_site)
        assert d is None
        assert c is None

        e, f = TransferClientFacade.split_site_path(multicolon_site)
        assert e == 'localhost'
        assert f == '/root/file.txt:1'

    def test_mkdir(self):
        site = "localhost:/root/subdir"
        with mock.patch.object(self.__client._TransferClient__wq_client, 'mkdir') as mock_mkdir:
            mock_mkdir.return_value = 'root/subdir created'
            assert self.__client.mkdir(site, **{'priority': 2}) == 'root/subdir created'
        assert mock_mkdir.called
        mock_mkdir.assert_called_with(self.site_id, '/root/subdir',
                                      priority=2)
        # now unknown site:
        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'mkdir') as mock_mkdir:
            mock_mkdir.return_value = 'whatever..'  # event if ...
            assert self.__client.mkdir(wrongurl, **{'priority': 2}) == None  # we return None
        assert not mock_mkdir.called

    def test_rename(self):
        s_site = "localhost:/root/file.txt"
        t_site = ":/root/file2.txt"

        with mock.patch.object(self.__client._TransferClient__wq_client, 'rename') as mock_rename:
            mock_rename.return_value = 'root/file.txt renamed'
            assert self.__client.rename(s_site, t_site,
                                        **{'priority': 2}) == 'root/file.txt renamed'
        assert mock_rename.called
        mock_rename.assert_called_with(self.site_id, '/root/file.txt',
                                       '/root/file2.txt',
                                       priority=2)

        wrongurl = "localhost2:/root/file.txt"  # no such site,
        with mock.patch.object(self.__client._TransferClient__wq_client, 'rename') as mock_rename:
            mock_rename.return_value = 'whatever..'  # even if ...
            assert self.__client.rename(wrongurl, t_site,
                                        **{'priority': 2}) == None  # we return None
        assert not mock_rename.called

    def tearDown(self):
        pass
