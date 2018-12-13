#!/usr/bin/env python
"""
User Interface Service Utilities
"""

import logging
import datetime
from pdm.framework.Tokens import TokenService


class HRUtils(object):
    """
    Utility class for the HRService. Currently it contains only client side insecure
    token handling methods
    """

    _logger = logging.getLogger(__name__)

    @staticmethod
    def is_token_expired_insecure(token):
        """
        Check whether token is expired. This is an insecure call - it does not verify
        token's integrity.

        :param token: token in
        :return: True if expired or no expiry information;  False otherwise.
        """

        expiry_iso = HRUtils.get_token_expiry_insecure(token)
        return HRUtils.is_date_passed(expiry_iso)

    @staticmethod
    def is_date_passed(expiry_iso):
        """
        Check if date is in the past. None date is treated like one in the past.
        :param expiry_iso: data in ISO format
        :return: True if date is in the past, or if it is None.
        """
        _isoformat = '%Y-%m-%dT%H:%M:%S.%f'
        if expiry_iso:
            if datetime.datetime.strptime(expiry_iso, _isoformat) < \
                    datetime.datetime.utcnow():
                HRUtils._logger.error("Token expired on %s", expiry_iso)
                return True  # expired
            return False  # still valid
        return True  # incomplete

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

    @staticmethod
    def get_token_username_insecure(token):
        """
        Get username from a token.

        :param token:
        :return:
        """
        unpacked_token = TokenService.unpack(token)
        username = unpacked_token.get('email')
        if not username:
            HRUtils._logger.error("Token does not contain user information")
        return username
