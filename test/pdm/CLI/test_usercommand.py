import mock
import unittest
import argparse
import tempfile
from pdm.CLI.user_subcommand import UserCommand


from pdm.userservicedesk.TransferClientFacade import MockTransferClientFacade

class TestUsercommand(unittest.TestCase):

    #@mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    def setUp(self):

        #self._mocked_facade = mocked_facade
        #self._mocked_facade.return_value = MockTransferClientFacade("anything")

        self._parser = argparse.ArgumentParser()
        subparsers = self._parser.add_subparsers()
        UserCommand(subparsers)
        self._tmp_file =  tempfile.NamedTemporaryFile(dir='/tmp')
        self._tmp_file.write("Fake_token")
        self._tmp_file.flush()

    def tearDown(self):
        self._tmp_file.close()

    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    @mock.patch.object(MockTransferClientFacade, 'copy')
    def test_copy(self, mock_copy, mocked_facade, mock_sleep):
        """ test if possible extra keys have been removed fromkeywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        mocked_facade.return_value = MockTransferClientFacade("anything")
        mocked_facade.return_value.status = mock.MagicMock()
        mocked_facade.return_value.status.return_value = {'status':'DONE', 'id': 1}

        args = self._parser.parse_args('copy source dest -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)

        mock_copy.assert_called_with('source', 'dest', max_tries=3)
        assert mocked_facade.return_value.status.call_count == 1
        # NEW, only once:
        mocked_facade.return_value.status.reset_mock()
        status_list = [{'status':'NEW', 'id': 1}]*50
        mocked_facade.return_value.status.side_effect = status_list
        args.func(args)
        assert mocked_facade.return_value.status.call_count == 1

    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    @mock.patch.object(MockTransferClientFacade, 'list')
    @mock.patch.object(MockTransferClientFacade, 'output')
    def test_list(self, mock_output, mock_list, mocked_facade, mock_sleep):
        """ test if possible extra keys have been removed from keywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        #list_dicts = \
        #    [{u'is_directory': True, u'name': u'bin\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1356236545, u'size': 24576, u'groupid': u'0', u'permissions': u'dr-xr-xr-x'},
        #     {u'is_directory': True, u'name': u'etc\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1456236545, u'size': 6, u'groupid': u'0', u'permissions': u'drwxr-xr-x'},
        #     {u'is_directory': True, u'name': u'games\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1356236545, u'size': 6, u'groupid': u'0', u'permissions': u'drwxr-xr-x'},
        #     {u'is_directory': True, u'name': u'include\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1556236545, u'size': 23, u'groupid': u'0', u'permissions': u'drwxr-xr-x'},
        #     {u'is_directory': True, u'name': u'lib\t', u'userid': u'0', u'nlinks': 1, u'datestamp': 1576236545, u'size': 8192, u'groupid': u'0', u'permissions': u'dr-xr-xr-x'}]

        # phase 2 Listing (capital L !)
        list_dicts = \
        {"gsiftp://gfe02.grid.hep.ph.ic.ac.uk/pnfs/hep.ph.ic.ac.uk/data/mice/martynia/":
             [{"st_ctime": 0, "st_mtime": 1525967829, "st_gid": 20032, "name": "test", "st_nlink": 1, "st_ino": 0, "st_dev": 0, "st_size": 512, "st_mode": 16877, "st_uid": 103200, "st_atime": 0}],
         "gsiftp://gfe02.grid.hep.ph.ic.ac.uk/pnfs/hep.ph.ic.ac.uk/data/mice/martynia/test":
             [{"st_ctime": 0, "st_mtime": 1340722948, "st_gid": 20032, "name": "200mb-test-file-mice.bin", "st_nlink": 1, "st_ino": 0, "st_dev": 0, "st_size": 209715200, "st_mode": 33184, "st_uid": 103200, "st_atime": 0},
              {"st_ctime": 0, "st_mtime": 1525169517, "st_gid": 20032, "name": "data_copy_100MB", "st_nlink": 1, "st_ino": 0, "st_dev": 0, "st_size": 104857600, "st_mode": 33188, "st_uid": 103200, "st_atime": 0},
              {"st_ctime": 0, "st_mtime": 1526474895, "st_gid": 20032, "name": "pdm", "st_nlink": 1, "st_ino": 0, "st_dev": 0, "st_size": 512, "st_mode": 16877, "st_uid": 103200, "st_atime": 0}],
         "gsiftp://gfe02.grid.hep.ph.ic.ac.uk/pnfs/hep.ph.ic.ac.uk/data/mice/martynia/test/pdm":
             [{"st_ctime": 0, "st_mtime": 1526474898, "st_gid": 20032, "name": "data_copy_100MB", "st_nlink": 1, "st_ino": 0, "st_dev": 0, "st_size": 104857600, "st_mode": 33188, "st_uid": 103200, "st_atime": 0},
              {"st_ctime": 0, "st_mtime": 1526474895, "st_gid": 20032, "name": "data_copy_500MB", "st_nlink": 1, "st_ino": 0, "st_dev": 0, "st_size": 524288000, "st_mode": 33188, "st_uid": 103200, "st_atime": 0}]}

        mocked_facade.return_value = MockTransferClientFacade("anything")
        mocked_facade.return_value.status = mock.MagicMock()
        mock_list.return_value={'status':'DONE', 'id': 1}
        mocked_facade.return_value.status.return_value = {'status':'DONE', 'id': 1}
        # top level only:
        mock_output.return_value = {'Listing':list_dicts} #['gsiftp://gfe02.grid.hep.ph.ic.ac.uk/pnfs/hep.ph.ic.ac.uk/data/mice/martynia/test']}
        args = self._parser.parse_args('list source  -m 3 -t  {}'.format(self._tmp_file.name).split())
        args.func(args)
        mock_output.assert_called_with(1)
        mock_list.assert_called_with('source', max_tries=3)
        assert False

        mock_output.reset_mock()
        mock_list.reset_mock()
        mock_list.return_value={'status':'NEW', 'id': 1}
        args = self._parser.parse_args('list source  -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mock_list.call_count == 1
        assert mocked_facade.return_value.status.call_count == 2 # one at the beginning and then get the 'DONE'
        assert mock_output.called

        mock_output.reset_mock()
        mock_list.reset_mock()
        mock_list.return_value = None
        args = self._parser.parse_args('list source  -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mock_list.call_count == 1  # immediate failure, no such site
        assert not mock_output.called

        mock_output.reset_mock()
        mock_list.reset_mock()
        mocked_facade.return_value.status.reset_mock()
        mock_list.return_value={'status':'NEW', 'id': 1}
        status_list = [{'status':'NEW', 'id': 1}]*50
        mocked_facade.return_value.status.side_effect = status_list
        # keep list return value, timeout the status
        args = self._parser.parse_args('list source  -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mock_list.call_count == 1
        assert mocked_facade.return_value.status.call_count == 50
        assert not mock_output.called

    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    @mock.patch.object(MockTransferClientFacade, 'remove')
    def test_remove(self, mock_remove, mocked_facade, mock_sleep):
        """ test if possible extra keys have been removed from keywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        mocked_facade.return_value = MockTransferClientFacade("anything")
        mocked_facade.return_value.status = mock.MagicMock()
        mocked_facade.return_value.status.return_value = {'status':'DONE', 'id': 1}
        # protocol swittch is -s !!!
        args = self._parser.parse_args('remove source -s gsiftp -m 3 -t {}'.format(self._tmp_file.name).split())
        args.func(args)

        mock_remove.assert_called_with('source', max_tries=3, protocol='gsiftp')
        assert mocked_facade.return_value.status.call_count == 1

        mocked_facade.return_value.status.reset_mock()
        status_list = [{'status':'NEW', 'id': 1}]*50
        mocked_facade.return_value.status.side_effect = status_list
        args.func(args)
        assert mocked_facade.return_value.status.call_count == 1
        #block
        mocked_facade.return_value.status.reset_mock()
        status_list = [{'status':'NEW', 'id': 1}]*50
        mocked_facade.return_value.status.side_effect = status_list
        args = self._parser.parse_args('remove source  -m 3 -b -t {}'.format(self._tmp_file.name).split())
        args.func(args)
        assert mocked_facade.return_value.status.call_count == 50
