
import mock
import unittest
from pdm.cred.CredClient import MockCredClient
from pdm.endpoint.EndpointClient import MockEndpointClient
from pdm.userservicedesk.TransferClientFacade import TransferClientFacade
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.userservicedesk.HRService import HRService
from pdm.cred.CredService import CredService
import pdm.framework.Tokens as Tokens

class TestTransferClient(unittest.TestCase):
    @mock.patch.object(Tokens.TokenService, 'unpack')
    @mock.patch("pdm.userservicedesk.HRService.CredClient")
    @mock.patch("pdm.userservicedesk.TransferClient.CredClient")
    @mock.patch("pdm.userservicedesk.TransferClient.EndpointClient")
    @mock.patch("pdm.workqueue.WorkqueueClient.WorkqueueClient")
    def setUp(self, wq_mock, endp_mock, tc_cred_mock, cred_mock, mocked_unpack):
        cred_mock.return_value = MockCredClient()
        tc_cred_mock.return_value = MockCredClient()
        tc_cred_mock.return_value.set_token = mock.MagicMock()
        endp_mock.return_value = MockEndpointClient()
        endp_mock.return_value.set_token = mock.MagicMock()
        conf = {'CS_secret':'HJGnbfdsV'}
        # HR
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)  # to skip DB auto build
        token = {'id':1, 'expiry':None, 'key': 'unused'}

        self.__service.fake_auth("TOKEN", token)
        # database
        self.__service.build_db()  # build manually
        #
        db = self.__service.test_db()
        self.__service.before_startup(conf)  # to continue startup
        # CS
        self.__csservice = FlaskServer("pdm.cred.CredService")
        self.__csservice.test_mode(CredService, None)  # to skip DB auto build
        #token = {'id':1, 'expiry':None, 'key': 'unused'}

        self.__csservice.fake_auth("TOKEN", token)
        # database
        self.__csservice.build_db()  # build manually
        #
        db = self.__csservice.test_db()
        self.__csservice.before_startup(conf)  # to continue startup

        mocked_unpack.return_value = token
        htoken ='whateverhash'
        self.__client = TransferClientFacade(htoken)
        mocked_unpack.assert_called_with(htoken)
    def test_list(self):
        pass

    def tearDown(self):
        pass


