#!/usr/bin/env python
"""
User Interface Service Utilities
"""

import logging
import datetime
from pdm.framework.Tokens import TokenService

class HRUtils(object):
    """
    Utility class for the HRService. Currently it cointains only client side insecure
    token handling methods
    """

    _logger = logging.getLogger(__name__)

    @staticmethod
    def is_token_expired_insecure(token):
        """
        Check whether token is expired. This is an insecure call - it does not verify
        token's integrity.
        :return: True if expired or no expiry information;  False otherwise.
        """
        _isoformat = '%Y-%m-%dT%H:%M:%S.%f'
        expiry_iso = HRUtils.get_token_expiry_insecure(token)

        if expiry_iso:
            if datetime.datetime.strptime(expiry_iso, _isoformat) < \
                    datetime.datetime.utcnow():
                HRUtils._logger.error("Token expired on %s", expiry_iso)
                return True # expired
            return False # still valid
        return True # incomplete

    @staticmethod
    def get_token_expiry_insecure(token):
        """
        Get token expiry date in ISO format, Insecure - token integrity not checked.
        :param token: token in
        :return: ISO of the unpacked token
        """

        unpacked_token = TokenService.unpack(token)
        expiry_iso = unpacked_token.get('expiry')
        if not expiry_iso:
            HRUtils._logger.error("Token does not contain expiry information")
        return expiry_iso
