import sys
import unittest
import logging

import unittest.mock as mock

from pdm.workqueue.scripts import stdout_dump_helper


class TestGFAL2Helper(unittest.TestCase):
    def setUp(self):
        pass

    @mock.patch('logging.Logger')
    @mock.patch('sys.stdout.flush')
    @mock.patch('json.dump')
    @mock.patch('sys.stdout.write')
    def test_write_and_flush(self, mock_write, mock_jsond, mock_flush, mock_logger):
        stdout_dump_helper.dump_and_flush({'Reason': 'Serious problem', 'Code': 1, 'id': 1})
        mock_write.assert_called_with('\n')
        mock_jsond.assert_called_with({'Reason': 'Serious problem', 'Code': 1, 'id': 1}, sys.stdout)
        assert mock_flush.called

        # mock_logger.return_value = mock.MagicMock
        args = [3]
        stdout_dump_helper.dump_and_flush({'Reason': 'Serious problem', 'Code': 1, 'id': 1}, mock_logger,
                                          'Serious problem: type:%d', logging.INFO, *args)
        mock_logger.log.assert_called_with(logging.INFO, 'Serious problem: type:%d', *args)
