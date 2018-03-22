import mock
import unittest
import argparse
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

    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    @mock.patch.object(MockTransferClientFacade, 'copy')
    def test_copy(self, mock_copy, mocked_facade):
        """ test if possible extra keys have been removed fromkeywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        mocked_facade.return_value = MockTransferClientFacade("anything")

        args = self._parser.parse_args('copy source dest -m 3 -t gfsdgfhsgdfh'.split())
        args.func(args)

        mock_copy.assert_called_with('source', 'dest', max_tries=3)

    @mock.patch('pdm.CLI.user_subcommand.sleep')
    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    @mock.patch.object(MockTransferClientFacade, 'list')
    @mock.patch.object(MockTransferClientFacade, 'output')
    def test_list(self, mock_output, mock_list, mocked_facade, mock_sleep):
        """ test if possible extra keys have been removed from keywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        mocked_facade.return_value = MockTransferClientFacade("anything")
        mock_list.return_value={'status':'DONE', 'id': 1}
        mock_output.return_value = {'listing':'/mydit/file.txt'} # not really, OK for now
        args = self._parser.parse_args('list source  -m 3 -t gfsdgfhsgdfh'.split())
        args.func(args)
        mock_output.assert_called_with(1)
        mock_list.assert_called_with('source', max_tries=3)

        mock_output.reset_mock()
        mock_list.reset_mock()
        mock_list.return_value={'status':'NEW', 'id': 1}
        args = self._parser.parse_args('list source  -m 3 -t gfsdgfhsgdfh'.split())
        args.func(args)
        assert mock_list.call_count == 50
        assert not mock_output.called

    @mock.patch('pdm.CLI.user_subcommand.TransferClientFacade')
    @mock.patch.object(MockTransferClientFacade, 'remove')
    def test_remove(self, mock_remove, mocked_facade):
        """ test if possible extra keys have been removed from keywords arguments passed to TransferClientFacade
            Currently: token, func handle and positionals and None dict values
        """
        mocked_facade.return_value = MockTransferClientFacade("anything")

        args = self._parser.parse_args('remove source  -m 3 -t gfsdgfhsgdfh'.split())
        args.func(args)

        mock_remove.assert_called_with('source', max_tries=3)


    def tearDown(self):
        pass