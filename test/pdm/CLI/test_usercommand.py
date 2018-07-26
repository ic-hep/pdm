import mock
import unittest
import argparse
import tempfile
import datetime
from pdm.framework.Tokens import TokenService
from pdm.CLI.user_subcommand import UserCommand

class TestUsercommand(unittest.TestCase):
    # @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    def setUp(self):
        # self._mocked_facade = mocked_facade
        # self._mocked_facade.return_value = MockTransferClientFacade("anything")

        self._parser = argparse.ArgumentParser()
        subparsers = self._parser.add_subparsers()
        UserCommand(subparsers)
        self._tmp_file = tempfile.NamedTemporaryFile(dir='/tmp')
        future_date = (datetime.timedelta(0, 600) + datetime.datetime.utcnow()).isoformat()
        plain = {'id': 44, 'expiry': future_date}
        svc = TokenService()
        validtoken = svc.issue(plain)
        self._tmp_file.write(validtoken)
        self._tmp_file.flush()

    def tearDown(self):
        self._tmp_file.close()

    @mock.patch('pdm.CLI.user_subcommand.SiteClient')
    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    def test_copy(self, mocked_facade, mock_sleep, mock_site_client):
        """ test if possible extra keys have been removed fromkeywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        mock_site_client.return_value = mock_site_client
        mock_site_client.get_sites = mock.MagicMock(return_value=[{'site_name': 'source', 'site_id': 1},
                                                                  {'site_name': 'dest', 'site_id': 2}])
        mocked_facade.return_value = mock.MagicMock()
        mocked_facade.split_site_path = mock.MagicMock()  # static, so no return_value
        mocked_facade.split_site_path.return_value = ('source', 'aaa')

        mocked_facade.return_value.status.return_value = {'status': 'DONE', 'id': 1}
        mocked_copy = mocked_facade.return_value.copy
        mocked_copy.return_value = {'status': 'DONE', 'id': 1}
        args = self._parser.parse_args('copy source:aaa dest:bbb -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)

        mocked_copy.assert_called_with('source:aaa', 'dest:bbb', max_tries=3)
        assert mocked_facade.return_value.status.call_count == 1
        # NEW, only once:
        mocked_facade.return_value.status.reset_mock()
        status_list = [{'status': 'NEW', 'id': 1}] * 50
        mocked_facade.return_value.status.side_effect = status_list
        args.func(args)
        assert mocked_facade.return_value.status.call_count == 1

    #    @mock.patch.object(MockTransferClientFacade, 'list')
    #    @mock.patch.object(MockTransferClientFacade, 'output')
    #

    @mock.patch('pdm.CLI.user_subcommand.SiteClient')
    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    def test_list(self, mocked_facade, mock_sleep, mock_site_client):
        """ test if possible extra keys have been removed from keywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        # list_dicts = \
        #    [{u'is_directory': True, u'name': u'bin\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1356236545, u'size': 24576, u'groupid': u'0', u'permissions': u'dr-xr-xr-x'},
        #     {u'is_directory': True, u'name': u'etc\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1456236545, u'size': 6, u'groupid': u'0', u'permissions': u'drwxr-xr-x'},
        #     {u'is_directory': True, u'name': u'games\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1356236545, u'size': 6, u'groupid': u'0', u'permissions': u'drwxr-xr-x'},
        #     {u'is_directory': True, u'name': u'include\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1556236545, u'size': 23, u'groupid': u'0', u'permissions': u'drwxr-xr-x'},
        #     {u'is_directory': True, u'name': u'lib\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1576236545, u'size': 8192, u'groupid': u'0', u'permissions': u'dr-xr-xr-x'}]

        # phase 2 Listing
        list_dicts = \
            {"gsiftp://gfe02.grid.hep.ph.ic.ac.uk/pnfs/hep.ph.ic.ac.uk/data/mice/martynia/":
                 [{"st_ctime": 0, "st_mtime": 1525967829, "st_gid": 20032, "name": "test", "st_nlink": 1, "st_ino": 0,
                   "st_dev": 0, "st_size": 512, "st_mode": 16877, "st_uid": 103200, "st_atime": 0}],
             "gsiftp://gfe02.grid.hep.ph.ic.ac.uk/pnfs/hep.ph.ic.ac.uk/data/mice/martynia/test":
                 [{"st_ctime": 0, "st_mtime": 1340722948, "st_gid": 20032, "name": "200mb-test-file-mice.bin",
                   "st_nlink": 1, "st_ino": 0, "st_dev": 0, "st_size": 209715200, "st_mode": 33184, "st_uid": 103200,
                   "st_atime": 0},
                  {"st_ctime": 0, "st_mtime": 1525169517, "st_gid": 20032, "name": "data_copy_100MB", "st_nlink": 1,
                   "st_ino": 0, "st_dev": 0, "st_size": 104857600, "st_mode": 33188, "st_uid": 103200, "st_atime": 0},
                  {"st_ctime": 0, "st_mtime": 1526474895, "st_gid": 20032, "name": "pdm", "st_nlink": 1, "st_ino": 0,
                   "st_dev": 0, "st_size": 512, "st_mode": 16877, "st_uid": 103200, "st_atime": 0}],
             "gsiftp://gfe02.grid.hep.ph.ic.ac.uk/pnfs/hep.ph.ic.ac.uk/data/mice/martynia/test/pdm":
                 [{"st_ctime": 0, "st_mtime": 1526474898, "st_gid": 20032, "name": "data_copy_100MB", "st_nlink": 1,
                   "st_ino": 0, "st_dev": 0, "st_size": 104857600, "st_mode": 33188, "st_uid": 103200, "st_atime": 0},
                  {"st_ctime": 0, "st_mtime": 1526474895, "st_gid": 20032, "name": "data_copy_500MB", "st_nlink": 1,
                   "st_ino": 0, "st_dev": 0, "st_size": 524288000, "st_mode": 33188, "st_uid": 103200, "st_atime": 0}]}

        mock_site_client.return_value = mock_site_client
        mock_site_client.get_sites = mock.MagicMock(return_value=[{'site_name': 'source', 'site_id': 1}])
        mocked_facade.return_value = mock.MagicMock()
        mocked_facade.split_site_path = mock.MagicMock()  # static, so no return_value
        mocked_facade.split_site_path.return_value = ('source', 'aaa')

        mocked_facade.return_value.status.return_value = {'status': 'DONE', 'id': 1}
        # top level only:
        mocked_list = mocked_facade.return_value.list
        mocked_list.return_value = {'status': 'DONE', 'id': 1}
        mocked_output = mocked_facade.return_value.output
        mocked_output.return_value = [{  # listing is the element 0 of the list
                                         'listing': list_dicts}]
        args = self._parser.parse_args('list source  -m 3 -t  {}'.format(self._tmp_file.name).split())
        args.func(args)

        mocked_output.assert_called_with(1)
        mocked_list.assert_called_with('source', max_tries=3, depth=0)

        mocked_output.reset_mock()
        mocked_list.reset_mock()
        mocked_list.return_value = {'status': 'NEW', 'id': 1}
        args = self._parser.parse_args('list source  -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mocked_list.call_count == 1
        assert mocked_facade.return_value.status.call_count == 2  # one at the beginning and then get the 'DONE'
        assert mocked_output.called

        mocked_output.reset_mock()
        mocked_list.reset_mock()
        mocked_list.return_value = None
        args = self._parser.parse_args('list source  -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mocked_list.call_count == 1  # immediate failure, no such site
        assert not mocked_output.called

        mocked_output.reset_mock()
        mocked_list.reset_mock()
        mocked_facade.return_value.status.reset_mock()
        mocked_list.return_value = {'status': 'NEW', 'id': 1}
        status_list = [{'status': 'NEW', 'id': 1}] * 50
        mocked_facade.return_value.status.side_effect = status_list
        # keep list return value, timeout the status
        args = self._parser.parse_args('list source  -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mocked_list.call_count == 1
        assert mocked_facade.return_value.status.call_count == 50
        assert not mocked_output.called

    @mock.patch('pdm.CLI.user_subcommand.SiteClient')
    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    def test_remove(self, mocked_facade, mock_sleep, mock_site_client):
        """ test if possible extra keys have been removed from keywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        # protocol switch is -s !!!

        mock_site_client.return_value = mock_site_client
        mock_site_client.get_sites = mock.MagicMock(return_value=[{'site_name': 'test_site', 'site_id': 1}])
        mocked_facade.return_value = mock.MagicMock()
        mocked_facade.split_site_path = mock.MagicMock()  # static, so no return_value
        mocked_facade.split_site_path.return_value = ('test_site', 'aaa')

        args = self._parser.parse_args('remove test_site:aaa -s gsiftp -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)

        # mock_remove.assert_called_with('source', max_tries=3, protocol='gsiftp')
        mocked_facade.return_value.remove.assert_called_with('test_site:aaa', max_tries=3, protocol='gsiftp')
        assert mocked_facade.return_value.status.call_count == 1

        mocked_facade.return_value.status.reset_mock()
        status_list = [{'status': 'NEW', 'id': 1}] * 50
        mocked_facade.return_value.status.side_effect = status_list
        args.func(args)
        assert mocked_facade.return_value.status.call_count == 1
        # block
        mocked_facade.return_value.status.reset_mock()
        status_list = [{'status': 'NEW', 'id': 1}] * 50
        mocked_facade.return_value.status.side_effect = status_list
        args = self._parser.parse_args('remove source  -m 3 -b -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mocked_facade.return_value.status.call_count == 50

    @mock.patch('pdm.CLI.user_subcommand.SiteClient')
    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    def test_rename(self, mocked_facade, mock_sleep, mock_site_client):
        mock_site_client.return_value = mock_site_client
        mock_site_client.get_sites = mock.MagicMock(return_value=[{'site_name': 'test_site', 'site_id': 1}])
        mocked_facade.return_value = mock.MagicMock()
        mocked_facade.split_site_path = mock.MagicMock()  # static, so no return_value
        mocked_facade.split_site_path.return_value = ('test_site', 'aaa')
        # protocol switch is -s !!!
        args = self._parser.parse_args(
            'rename test_site:aaa :bbb -s gsiftp -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)

        mocked_facade.return_value.rename.assert_called_with('test_site:aaa', ':bbb', max_tries=3, protocol='gsiftp')
        assert mocked_facade.return_value.status.call_count == 1  # block resolves immediately

    @mock.patch('pdm.CLI.user_subcommand.SiteClient')
    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    def test_mkdir(self, mocked_facade, mock_sleep, mock_site_client):
        mock_site_client.return_value = mock_site_client
        mock_site_client.get_sites = mock.MagicMock(return_value=[{'site_name': 'site', 'site_id': 1}])
        mocked_facade.return_value = mock.MagicMock()
        mocked_facade.split_site_path = mock.MagicMock()  # static, so no return_value
        mocked_facade.split_site_path.return_value = ('site', '/path/to/file')

        mocked_facade.return_value.status.return_value = {'status': 'DONE', 'id': 1}

        # protocol swittch is -s !!!
        args = self._parser.parse_args(
            'mkdir site:/path/to/file -s gsiftp -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)

        mocked_facade.return_value.mkdir.assert_called_with('site:/path/to/file', max_tries=3, protocol='gsiftp')
        assert mocked_facade.return_value.status.call_count == 1  # block resolves immediately

    @mock.patch('pdm.CLI.user_subcommand.SiteClient')
    def test_add_site(self, mock_site_client):
        args = self._parser.parse_args('addsite test_site just_a_test_site'
                                       ' -t {} -e host:9876 -a myproxy_host:9876'.format(self._tmp_file.name).split())
        args.func(args)
        assert mock_site_client.called
        mock_site_client.return_value.add_site. \
            assert_called_with(
            {'auth_type': 0, 'site_name': 'test_site', 'def_path': '/~', 'auth_uri': 'myproxy_host:9876',
             'site_desc': 'just_a_test_site', 'public': False, 'endpoints': ['host:9876']})

        # user provides certificates, file not found
        mock_site_client.reset_mock()
        args = self._parser.parse_args('addsite test_site just_a_test_site'
                                       ' -t {} -u {} -e host:9876 -a myproxy_host:9876'
                                       .format(self._tmp_file.name, 'nonexisting.file').split())
        args.func(args)
        assert not mock_site_client.called

        mock_site_client.reset_mock()
        args = self._parser.parse_args('addsite test_site just_a_test_site'
                                       ' -t {} -s {} -e host:9876 -a myproxy_host:9876'
                                       .format(self._tmp_file.name, 'nonexisting.file').split())
        args.func(args)
        assert not mock_site_client.called

        # user provides service certificates, file OK
        mock_site_client.reset_mock()
        _tmp_file = tempfile.NamedTemporaryFile(dir='/tmp')
        fake_cert = 'BEGIN_FAKE_CERTghsgshhgkxxxEND_FAKE_CERT'
        _tmp_file.write(fake_cert)
        _tmp_file.flush()
        args = self._parser.parse_args('addsite test_site just_a_test_site'
                                       ' -t {} -s {} -e host:9876 -a myproxy_host:9876'
                                       .format(self._tmp_file.name, _tmp_file.name).split())
        args.func(args)
        assert mock_site_client.called
        mock_site_client.return_value.add_site. \
            assert_called_with(
            {'auth_type': 0, 'site_name': 'test_site', 'def_path': '/~', 'auth_uri': 'myproxy_host:9876',
             'site_desc': 'just_a_test_site', 'public': False, 'endpoints': ['host:9876'],
             'service_ca_cert': fake_cert})
        # same for user CA cert
        args = self._parser.parse_args('addsite test_site just_a_test_site'
                                       ' -t {} -u {} -e host:9876 -a myproxy_host:9876'
                                       .format(self._tmp_file.name, _tmp_file.name).split())
        args.func(args)
        assert mock_site_client.called
        mock_site_client.return_value.add_site. \
            assert_called_with(
            {'auth_type': 0, 'site_name': 'test_site', 'def_path': '/~', 'auth_uri': 'myproxy_host:9876',
             'site_desc': 'just_a_test_site', 'public': False, 'endpoints': ['host:9876'],
             'user_ca_cert': fake_cert})

    @mock.patch('pdm.CLI.user_subcommand.SiteClient')
    def test_del_site(self, mock_site_client):
        mock_site_client.return_value = mock_site_client
        mock_site_client.get_sites = mock.MagicMock(return_value=[{'site_name': 'test_site', 'site_id': 1}])

        args = self._parser.parse_args('delsite test_site -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mock_site_client.called
        assert mock_site_client.get_sites.called
        # mock_site_client.return_value.get_sites.return_value=[{'site_name':'test_site', 'site_id': 1}]
        mock_site_client.del_site.assert_called_with(1)

        # non existing site
        mock_site_client.reset_mock()
        mock_site_client.return_value = mock_site_client
        mock_site_client.get_sites = mock.MagicMock(return_value=[{'site_name': 'test_site', 'site_id': 1}])
        args = self._parser.parse_args('delsite test_site1 -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mock_site_client.called
        assert mock_site_client.get_sites.called
        assert not mock_site_client.del_site.called
