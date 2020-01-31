#!/usr/bin/env python
""" Access Control for Flask Wrapper. """

import urllib.parse
from copy import deepcopy
from datetime import datetime
import flask
from flask import abort, current_app, request, session
from pdm.utils.X509 import X509Utils


def set_session_state(logged_in=False):
    """ A helper function for changing the flask session state.
        Must be called from a Flask request context.
        Returns None.
    """
    session['logged_in'] = logged_in


class ACLManager(object):
    """ Access Control List manager for Flask Wrapper.
        Keeps a list of users who are allowed to access resources
        and allows or rejects request based on the presented credentials.
    """

    AUTH_MODE_NONE = 0
    AUTH_MODE_X509 = 1
    AUTH_MODE_TOKEN = 2
    AUTH_MODE_SESSION = 3
    AUTH_MODE_ALLOW_ALL = 4

    def __init__(self, logger):
        """ Create an empty instance of ACLManager (no predfined groups or
            rules. Test mode is disabled by default.
        """
        self.__log = logger
        self.__test_mode = ACLManager.AUTH_MODE_NONE
        self.__test_data = None
        self.__groups = {}
        self.__rules = {}

    def __check_entry(self, entry, allow_group):
        """ Checks an entry is in a valid format and expands groups.
            If groups are allowed, then inputting a group entry will
            result in the expanded group entries on the output.
            entry - The entry string to check.
            allow_group - Boolean, on whether to allow group names.
            Raises a ValueError if it isn't valid.
            Returns a list of entries.
            Each returned entry is a tuple of (auth_mode, auth_data).
        """
        if entry == "TOKEN":
            return [(ACLManager.AUTH_MODE_TOKEN, None)]
        elif entry == "CERT":
            return [(ACLManager.AUTH_MODE_X509, None)]
        elif entry == "SESSION":
            return [(ACLManager.AUTH_MODE_SESSION, None)]
        elif entry == "ALL":
            return [(ACLManager.AUTH_MODE_ALLOW_ALL, None)]
        elif entry.startswith("CERT:"):
            raw_dn = entry.split(':', 1)[1]
            if not "=" in raw_dn:
                raise ValueError("Bad CERT DN in ACL rule: '%s'" % entry)
            return [(ACLManager.AUTH_MODE_X509,
                     X509Utils.normalise_dn(raw_dn))]
        elif allow_group and entry.startswith("@"):
            group_name = entry[1:]
            if not group_name in self.__groups:
                raise ValueError("Unrecognised group used in ACL rule: %s" % \
                                 group_name)
            return deepcopy(self.__groups[group_name])
        raise ValueError("Invalid auth entry '%s'." % entry)

    def add_group_entry(self, group_name, entry):
        """ Adds an entry to a group, if the group doesn't exist it will be
            created, otherwise it will be appeneded. Note that groups can't
            currently be nested.
        """
        entries = self.__check_entry(entry, False)
        if not group_name in self.__groups:
            self.__groups[group_name] = entries
        else:
            self.__groups[group_name].extend(entries)

    def add_rule(self, res_path, entry):
        """ Adds a rule for a specific resource path. The entry can either
            be an existing group or a normal entry value.
        """
        if not '%' in res_path:
            res_path = "%s%%GET" % res_path
        if res_path in self.__rules:
            raise ValueError("Duplicate auth rule for path '%s'." % res_path)
        self.__rules[res_path] = self.__check_entry(entry, True)

    def test_mode(self, auth_mode, auth_data=None):
        """ Enabled test mode, where the authentication info is pre-set for
            all requests. This should not be used in production.
        """
        self.__test_mode = auth_mode
        self.__test_data = auth_data

    @staticmethod
    def __get_real_request_auth():
        """ Fills the details of the presented credentials into the
            request object.
        """
        # Cert auth
        if 'Ssl-Client-Verify' in request.headers \
            and 'Ssl-Client-S-Dn' in request.headers:
            # Request has client cert
            if request.headers['Ssl-Client-Verify'] == 'SUCCESS':
                raw_dn = request.headers['Ssl-Client-S-Dn']
                request.dn = X509Utils.normalise_dn(raw_dn)
        # Token Auth
        if 'X-Token' in request.headers:
            raw_token = request.headers['X-Token']
            try:
                token_value = current_app.token_svc.check(raw_token)
                # Check if this looks like a standard token with an expiry value
                if isinstance(token_value, dict):
                    if 'expiry' in token_value:
                        exp_str = token_value['expiry']
                        exp_value = datetime.strptime(exp_str, '%Y-%m-%dT%H:%M:%S.%f')
                        if exp_value < datetime.utcnow():
                            # Token has already expired
                            current_app.log.info("Request %s token has expired (at %s)",
                                                 request.uuid, exp_str)
                            return "403 Expired Token", 403
                request.token = token_value
                request.raw_token = raw_token
                request.token_ok = True
            except ValueError:
                # Token decoding failed, it is probably corrupt or has been
                # tampered with.
                current_app.log.info("Request %s token validation failed.",
                                     request.uuid)
                return "403 Invalid Token", 403
        if 'logged_in' in session:
            if session['logged_in']:
                request.session_ok = True

    def __get_fake_request_auth(self):
        """ Fills the request object with te test (fake) authentication
            details.
        """
        if self.__test_mode == ACLManager.AUTH_MODE_X509:
            request.dn = X509Utils.normalise_dn(self.__test_data)
        elif self.__test_mode == ACLManager.AUTH_MODE_TOKEN:
            request.token = self.__test_data
            request.raw_token = self.__test_data
            request.token_ok = True
        elif self.__test_mode == ACLManager.AUTH_MODE_SESSION:
            request.session_ok = True

    @staticmethod
    def __matches_rules(rules):
        """ Checks the current request against a list of expanded rules.
            If the request matches any of the rules, True is returned.
            False is returned if no rules match the current request creds.
        """
        for rule in rules:
            rule_mode, rule_data = rule
            if rule_mode == ACLManager.AUTH_MODE_TOKEN:
                if request.token_ok:
                    return True
            elif rule_mode == ACLManager.AUTH_MODE_X509:
                if rule_data is not None:
                    if rule_data == request.dn:
                        return True
                else:
                    if request.dn:
                        return True
            elif rule_mode == ACLManager.AUTH_MODE_SESSION:
                if request.session_ok:
                    return True
            elif rule_mode == ACLManager.AUTH_MODE_ALLOW_ALL:
                return True
        return False

    @staticmethod
    def __match_path(req_detail, rule_detail):
        """ Checks whether a request path matches a rule path.
            The rule path can contiain wildcards * or ?.
            Although the * wildcard can only be in the last position.
            Returns True if the rule_detail pattern matches req_detail.
        """
        req_path, req_method = req_detail.split('%')
        rule_path, rule_method = rule_detail.split('%')
        if req_method != rule_method:
            return False # Wrong method
        req_parts = req_path.split('/')
        rule_parts = rule_path.split('/')
        # If the request path is shorter than the rule, then it
        # can't possibly match
        if len(req_parts) < len(rule_parts):
            return False
        # If the rule ends in a wildcard, ignore all bits of the
        # request path that match the wildcard
        if rule_parts[-1] == '*':
            rule_parts = rule_parts[0:-1]
            req_parts = req_parts[0:len(rule_parts)]
        # If the request is longer than the rule (considering *),
        # the request can't match
        if len(req_parts) > len(rule_parts):
            return False
        # Now check each segment of the path to match either
        # directly or by wildcard
        for part_num in range(0, len(rule_parts)):
            req_part = req_parts[part_num]
            rule_part = rule_parts[part_num]
            if rule_part == '?':
                continue
            if req_part != rule_part:
                return False
        # Everything matched, so the rule matches the request
        return True

    @staticmethod
    def __do_abort():
        """ Aborts the current request due to access denied.
            If the export provided a redir value for access denied,
            the client will be redirected, otherwise a 403 will be
            returned.
        """
        # Check whether this endpoint has a special redirect
        if request.endpoint:
            if request.endpoint in current_app.view_functions:
                ep_func = current_app.view_functions[request.endpoint]
                if ep_func:
                    redir_url = getattr(ep_func, 'export_redir', None)
                    if redir_url:
                        orig_path = urllib.parse.quote(request.path, safe='')
                        real_redir = redir_url % {'return_to': orig_path}
                        abort(flask.redirect(real_redir))
        abort(403)

    def __check_acl(self):
        """ Checks the request object authentication details against the ACL
            list for the requested resource.
            Raises a Flask 403 abort if access should be denied.
        """
        # Work out the request URI
        real_path = request.path
        # Strip a trailing slash, as long as it isn't the only char
        if real_path.endswith('/') and len(real_path) > 1:
            real_path = real_path[:-1]
        real_path = "%s%%%s" % (real_path, request.method)
        # Now check the auth rules for this path
        if real_path in self.__rules:
            if self.__matches_rules(self.__rules[real_path]):
                # The request matches => Access allowed
                return
            self.__log.info("Request %s denied (Failed to match specific rule).",
                            request.uuid)
            self.__do_abort()
        # No specific rule for this path, try generic rules
        did_match = False
        for rule_path in self.__rules.keys():
            if self.__match_path(real_path, rule_path):
                did_match = True
                if self.__matches_rules(self.__rules[rule_path]):
                    # Access allowed via a generic rule
                    return
        reason = "no matching auth rule"
        if did_match:
            reason = "all wildcard rules denied access"
        # No rule matches => request denied
        self.__log.info("Request %s denied (%s).",
                        request.uuid, reason)
        self.__do_abort()

    def check_request(self):
        """ Gets the current flask request object and checks it against the
            configured rule set.
        """
        # We use '%' to seperate out the method from the rest of the request
        # We simply don't support requests that contain a % in the URI from
        # the client.
        if '%' in request.path:
            abort(404)
        request.dn = None
        request.token = None
        request.raw_token = None
        request.token_ok = False
        request.session_ok = False
        if self.__test_mode == ACLManager.AUTH_MODE_NONE:
            self.__get_real_request_auth()
            self.__check_acl()
        else:
            self.__get_fake_request_auth()
            # ACLs aren't actually checked in test mode
