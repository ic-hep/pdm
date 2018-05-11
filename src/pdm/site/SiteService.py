#!/usr/bin/env python
""" Site service module. """

import re
import json
import datetime
from flask import current_app, request, abort
from sqlalchemy.exc import IntegrityError
from pdm.framework.FlaskWrapper import jsonify
from pdm.framework.Decorators import db_model, export_ext, startup, startup_test
from pdm.site.SiteDB import SiteDBModel
from pdm.userservicedesk.HRService import HRService
from pdm.utils.db import managed_session
from pdm.utils.config import getConfig
from pdm.utils.myproxy import MyProxyUtils
from pdm.utils.X509 import X509Utils

@export_ext('/site/api/v1.0')
@db_model(SiteDBModel)
class SiteService(object):
    """ Site service. """

    @staticmethod
    def get_current_uid():
        """ A helper function to return the user ID of the current
            request.
        """
        # TODO: Find a better way to access the token
        return request.token['id']

    URI_FORMAT = re.compile(r'^[a-z][a-z0-9.-]+:[0-9]+$')

    @staticmethod
    def check_uri(uri):
        """ Checks that a URI appears to be in hostname:port format.
            Returns True if it looks OK, False otherwise.
        """
        lower_uri = uri.lower()
        if not SiteService.URI_FORMAT.match(lower_uri):
            return False
        return True

    @staticmethod
    @startup
    def setup_security(conf):
        """ Load the security settings from the config dict. """
        current_app.cadir = conf.pop('cadir', None)
        current_app.vo_list = []
        current_app.myproxy_bin = conf.pop('myproxy_bin', None)
        vomses = conf.pop('vomses', None)
        current_app.vomses = vomses
        if vomses:
            current_app.vo_list = MyProxyUtils.load_voms_list(vomses)

    @staticmethod
    @export_ext("service")
    def get_service():
        """ Returns core service data.
            At the moment this mainly means the central service CA cert.
        """
        log = current_app.log
        ca_data = None
        client_conf = getConfig("client")
        ca_cert = client_conf.get("cafile", None)
        if ca_cert:
            try:
                with open(ca_cert, "r") as ca_fd:
                    ca_data = ca_fd.read()
            except Exception as err:
                log.error("Failed to read cafile for service endpoint: %s",
                          str(err))
        # Get the user endpoint
        ep_conf = getConfig("endpoints")
        user_ep = ep_conf.get("users", None)
        # Build output dictionary
        res = {}
        if ca_data:
            res["central_ca"] = ca_data
        if user_ep:
            res["user_ep"] = user_ep
        if current_app.vo_list:
            res["vos"] = current_app.vo_list
        return jsonify(res)

    @staticmethod
    @export_ext("site")
    def get_site_list():
        """ Get a list of all sites, although actually only returns
            entires that the user can see (public + self-owned).
        """
        log = current_app.log
        db = request.db
        user_id = SiteService.get_current_uid()
        Site = db.tables.Site
        site_list = []
        sites = Site.query.all()
        for site_entry in sites:
            # Ensure user can only see the correct sites
            is_owner = False
            is_visible = False
            if site_entry.site_owner == user_id:
                is_owner = True
                is_visible = True
            elif site_entry.public:
                is_visible = True
            if not is_visible:
                continue
            # Build the output object
            cur_site = {"is_owner": is_owner,
                        "public": site_entry.public}
            for key in ("site_id", "site_name", "site_desc", "def_path"):
                cur_site[key] = getattr(site_entry, key)
            site_list.append(cur_site)
        log.info("Found %u sites for user id %u.", len(site_list), user_id)
        return jsonify(site_list)

    @staticmethod
    @export_ext("site/<int:site_id>")
    def get_site(site_id):
        """ Gets the full details for a given site ID.
            Returns 404 if the site doesn't exist or if the user
            isn't allowed to view this site.
        """
        log = current_app.log
        db = request.db
        user_id = SiteService.get_current_uid()
        Site = db.tables.Site
        site = Site.query.filter_by(site_id=site_id).first_or_404()
        is_owner = (site.site_owner == user_id)
        if not (site.public or is_owner):
            log.warn("User %u failed to get site %u details (no permission).",
                     user_id, site_id)
            abort(404) # User isn't allowed to see this site
        log.info("User %u got details of site %u (%s).", user_id, site_id,
                 site.site_name)
        # Add the endpoint info
        endpoints = []
        for ep_info in site.endpoints:
            endpoints.append(ep_info.ep_uri)
        # Prepare the output data
        dict_out = dict(site)
        dict_out["is_owner"] = is_owner
        dict_out["endpoints"] = endpoints
        return jsonify(dict_out)

    # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
    @staticmethod
    @export_ext("site", ["POST"])
    def add_site():
        """ Add a site in the database. """
        log = current_app.log
        db = request.db
        Site = db.tables.Site
        Endpoint = db.tables.Endpoint
        site_data = {}
        endpoints = []
        try:
            if not request.data:
                return "Missing POST data", 400
            raw_site_data = json.loads(request.data)
            # Required fields
            for key in ('site_name', 'site_desc',
                        'auth_type', 'auth_uri',
                        'public', 'def_path'):
                raw_val = raw_site_data.get(key, None)
                if raw_val is None:
                    return "Required field %s missing" % key, 400
                site_data[key] = raw_val
            # Optional fields
            for key in ('user_ca_cert', 'service_ca_cert'):
                raw_val = raw_site_data.get(key, None)
                if raw_val:
                    site_data[key] = raw_val
            # Check the auth types
            if site_data["auth_type"] not in (0, 1):
                log.warn("Unable to add site: Invalid auth_type (%s)",
                         site_data["auth_type"])
                return "Invalid auth_type.", 400
            if not SiteService.check_uri(site_data["auth_uri"]):
                log.warn("Unable to add site: Invalid auth_uri (%s)",
                         site_data["auth_uri"])
                return "Invalid auth_uri.", 400
            # Extra fields
            site_data["site_owner"] = SiteService.get_current_uid()
            # Endpoints
            raw_eps = raw_site_data.get('endpoints', [])
            for raw_ep in raw_eps:
                if not SiteService.check_uri(raw_ep):
                    log.warn("Unable to add site: Bad endpoint (%s)", raw_ep)
                    return "Invalid endpoint format.", 400
            endpoints.extend(raw_eps)
        except Exception as err:
            log.warn("POST data error from client: %s", str(err))
            return "Malformed POST data", 400
        # Now actually try to create the site
        new_site = Site(**site_data)
        try:
            with managed_session(request) as session:
                session.add(new_site)
                session.flush() # Ensure new_site gets an ID
                site_id = new_site.site_id
                # Also create the endpoints
                for ep_uri in endpoints:
                    session.add(Endpoint(site_id=site_id, ep_uri=ep_uri))
        except IntegrityError:
            # site_name is probably not unique
            log.info("Failed to add new non-unique site %s.",
                     new_site.site_name)
            return "site_name is not unique", 409
        except Exception as err:
            # Some kind of other database error?
            log.error("Failed to add new site %s (%s).",
                      site_data['site_name'], str(err))
            return "Failed to add site to DB", 500
        log.info("Added site %s with %u endpoints (ID %u).",
                 new_site.site_name, len(endpoints), new_site.site_id)
        return jsonify(new_site.site_id)

    @staticmethod
    @export_ext("site/<int:site_id>", ["DELETE"])
    def del_site(site_id):
        """ Delete a site (including all endpoints). """
        log = current_app.log
        db = request.db
        Site = db.tables.Site
        user_id = SiteService.get_current_uid()
        # By adding the owner to the query, we prevent a user
        # deleting anything but their own sites
        site = Site.query.filter_by(site_id=site_id,
                                    site_owner=user_id).first_or_404()
        with managed_session(request,
                             message="Database error while deleting site",
                             http_error_code=500) as session:
            session.delete(site)
        log.info("Deleted site ID %u.", site_id)
        return ""

    @staticmethod
    @export_ext("endpoint/<int:site_id>")
    def get_endpoints(site_id):
        """ Get a list of all endpoints at a given site_id.
            Designed for cert auth.
        """
        db = request.db
        Site = db.tables.Site
        site = Site.query.filter_by(site_id=site_id).first_or_404()
        endpoints = []
        for ep_info in site.endpoints:
            endpoints.append(ep_info.ep_uri)
        return jsonify(endpoints)

    @staticmethod
    @export_ext("user/<int:user_id>", ["DELETE"])
    def del_user(user_id):
        """ Deletes all sites owned by the given user.
            User ID must match the supplied token.
            This also clears the cred cache of any entries for the user.
        """
        log = current_app.log
        db = request.db
        Site = db.tables.Site
        Cred = db.tables.Cred
        auth_user_id = SiteService.get_current_uid()
        # Check the user is deleting their own items
        if auth_user_id != user_id:
            log.warn("User %u tried to delete sites belonging to user %u.",
                     auth_user_id, user_id)
            abort(404)
        sites = Site.query.filter_by(site_owner=auth_user_id).all()
        num_sites = len(sites)
        creds = Cred.query.filter_by(cred_owner=auth_user_id).all()
        num_creds = len(creds)
        with managed_session(request,
                             message="Database error while deleting sites",
                             http_error_code=500) as session:
            for cred in creds:
                session.delete(cred)
            for site in sites:
                session.delete(site)
        log.info("Deleted all sites for user %u (%u sites, %u creds deleted).",
                 auth_user_id, num_sites, num_creds)
        return ""

    @staticmethod
    @export_ext("session/<int:site_id>")
    def get_session_info(site_id):
        """ Get the session info for the current user at a given site. """
        log = current_app.log
        db = request.db
        Cred = db.tables.Cred
        user_id = SiteService.get_current_uid()
        cred = Cred.query.filter_by(cred_owner=user_id,
                                    site_id=site_id).first()
        res = {'ok': False}
        if cred:
            res['username'] = cred.cred_username
            res['expiry'] = cred.cred_expiry
            if cred.cred_expiry > datetime.datetime.utcnow():
                res['ok'] = True
        log.info("Fetched info for user %u at site %u.", user_id, site_id)
        return jsonify(res)

    # pylint: disable=too-many-locals
    @staticmethod
    @export_ext("session/<int:site_id>", ["POST"])
    def logon_session(site_id):
        """ Create a session for the current user at a given site. """
        log = current_app.log
        db = request.db
        Site = db.tables.Site
        Cred = db.tables.Cred
        user_id = SiteService.get_current_uid()
        # Decode POST data
        if not request.data:
            log.warn("Missing post data for logon.")
            return "Missing POST data", 400
        cred_data = json.loads(request.data)
        username = cred_data.get("username", None)
        password = cred_data.get("password", None)
        lifetime = cred_data.get("lifetime", None)
        vo_name = cred_data.get("vo", None)
        if not username or not password or not lifetime:
            log.warn("Missing post field in logon.")
            return "Required field missing", 400
        # Check user can see the site
        site = Site.query.filter_by(site_id=site_id).first_or_404()
        is_owner = (site.site_owner == user_id)
        if not (is_owner or site.public):
            log.warn("User %u tried to login to site %u (access denied).",
                     user_id, site_id)
            abort(404) # This user can't see the requested site
        # Check the site auth configuration
        if site.auth_type == 1:
            # VOMS login
            if not vo_name:
                log.warn("User %u did not specify required VO name for site %u",
                         user_id, site_id)
                return "VO required", 400
            if not vo_name in current_app.vo_list:
                log.warn("User %u requested unknown VO '%s' for login to site %u.",
                         user_id, vo_name, site_id)
                return "Unknown VO name", 400
        # Process the different possible CA info combinations
        ca_info = None
        if site.user_ca_cert or site.service_ca_cert:
            ca_info = []
            if site.user_ca_cert:
                ca_info.append(site.user_ca_cert)
            if site.service_ca_cert:
                ca_info.append(site.service_ca_cert)
        elif current_app.cadir:
            ca_info = current_app.cadir
        # Actually run the myproxy command
        try:
            proxy = MyProxyUtils.logon(site.auth_uri, username, password,
                                       ca_info, vo_name, lifetime,
                                       myproxy_bin=current_app.myproxy_bin,
                                       vomses=current_app.vomses,
                                       log=log)
        except Exception as err:
            log.error("Failed to login user: %s", str(err))
            return "Login failed: %s" % str(err), 400
        new_cred = Cred(cred_owner=user_id,
                        site_id=site_id,
                        cred_username=username,
                        cred_expiry=X509Utils.get_cert_expiry(proxy),
                        cred_value=proxy)
        with managed_session(request,
                             message="Database error while storing proxy",
                             http_error_code=500) as session:
            session.add(new_cred)
        return ""

    @staticmethod
    @export_ext("session/<int:site_id>", ["DELETE"])
    def logoff_session(site_id):
        """ Delete a session for the current user at a given site. """
        log = current_app.log
        db = request.db
        Cred = db.tables.Cred
        user_id = SiteService.get_current_uid()
        cred = Cred.query.filter_by(cred_owner=user_id,
                                    site_id=site_id).first()
        if cred:
            with managed_session(request,
                                 message="Database error while deleting creds",
                                 http_error_code=500) as session:
                session.delete(cred)
        log.info("Deleted session for user %u at site %u.", user_id, site_id)
        return ""

    @staticmethod
    @export_ext("cred/<int:site_id>/<int:user_id>")
    def get_cred(site_id, user_id):
        """ Get a credential for a user at a specific site. """
        log = current_app.log
        db = request.db
        Cred = db.tables.Cred
        cred = Cred.query.filter_by(cred_owner=user_id,
                                    site_id=site_id).first_or_404()
        log.info("Fetched cred for user %u at site %u.", user_id, site_id)
        return jsonify(cred.cred_value)

    @staticmethod
    @startup_test
    def test_data():
        """ Register test data if DB is empty. """
        db = current_app.db
        Site = db.tables.Site
        Endpoint = db.tables.Endpoint
        if Site.query.count():
            return # DB not empty
        entries = [
            Site(site_id=1,
                 site_name='Site1',
                 site_desc='First Test Site',
                 site_owner=1,
                 user_ca_cert='USERCERT1',
                 service_ca_cert='',
                 auth_type=0,
                 auth_uri='localhost:49998',
                 public=False,
                 def_path='/~'),
            Site(site_id=2,
                 site_name='Site2',
                 site_desc='Second Test Site',
                 site_owner=123,
                 user_ca_cert='USERCERT2',
                 service_ca_cert='SERVICECERT2',
                 auth_type=0,
                 auth_uri='localhost:49998',
                 public=True,
                 def_path='/project'),
            Endpoint(ep_id=1,
                     site_id=1,
                     ep_uri='localhost:49999'),
            Endpoint(ep_id=2,
                     site_id=1,
                     ep_uri='localhost2:49999'),
            Endpoint(ep_id=3,
                     site_id=2,
                     ep_uri='localhost:50000'),
            Endpoint(ep_id=4,
                     site_id=2,
                     ep_uri='localhost2:50000'),
            Site(site_id=3,
                 site_name='CloudSite1',
                 site_desc='Testing site in cloud (1)',
                 site_owner=1,
                 user_ca_cert=TEST_HOST_CA,
                 service_ca_cert=UK_ESCIENCE_CA,
                 auth_type=0,
                 auth_uri='pdmtest1.grid.hep.ph.ic.ac.uk:49998',
                 public=True,
                 def_path='/~'),
            Endpoint(ep_id=5,
                     site_id=3,
                     ep_uri='pdmtest1.grid.hep.ph.ic.ac.uk:49999'),
            Site(site_id=4,
                 site_name='CloudSite2',
                 site_desc='Testing site in cloud (2)',
                 site_owner=1,
                 user_ca_cert=TEST_HOST_CA,
                 service_ca_cert=UK_ESCIENCE_CA,
                 auth_type=0,
                 auth_uri='pdmtest2.grid.hep.ph.ic.ac.uk:49998',
                 public=True,
                 def_path='/~'),
            Endpoint(ep_id=6,
                     site_id=4,
                     ep_uri='pdmtest2.grid.hep.ph.ic.ac.uk:49999'),
            Site(site_id=5,
                 site_name='UKI-LT2-IC-HEP',
                 site_desc='Imperial College GridPP Site',
                 site_owner=0,
                 user_ca_cert=None,
                 service_ca_cert=None,
                 auth_type=1,
                 auth_uri='myproxy.grid.hep.ph.ic.ac.uk:7512',
                 public=True,
                 def_path='/pnfs/hep.ph.ic.ac.uk/data'),
            Endpoint(ep_id=7,
                     site_id=5,
                     ep_uri='gfe02.grid.hep.ph.ic.ac.uk:2811'),
            Site(site_id=6,
                 site_name='NERSC DTN',
                 site_desc='NERSC DTN Service',
                 site_owner=0,
                 user_ca_cert=None,
                 service_ca_cert=None,
                 auth_type=0,
                 auth_uri='myproxy.grid.hep.ph.ic.ac.uk:7512',
                 public=True,
                 def_path='/~'),
            Endpoint(ep_id=8,
                     site_id=6,
                     ep_uri='dtn01.nersc.gov:2811'),
        ]
        for entry in entries:
            db.session.add(entry)
        db.session.commit()

UK_ESCIENCE_CA = """-----BEGIN CERTIFICATE-----
MIIDwzCCAqugAwIBAgICASMwDQYJKoZIhvcNAQELBQAwVDELMAkGA1UEBhMCVUsx
FTATBgNVBAoTDGVTY2llbmNlUm9vdDESMBAGA1UECxMJQXV0aG9yaXR5MRowGAYD
VQQDExFVSyBlLVNjaWVuY2UgUm9vdDAeFw0xMTA2MTgxMzAwMDBaFw0yNzEwMzAw
OTAwMDBaMFMxCzAJBgNVBAYTAlVLMRMwEQYDVQQKEwplU2NpZW5jZUNBMRIwEAYD
VQQLEwlBdXRob3JpdHkxGzAZBgNVBAMTElVLIGUtU2NpZW5jZSBDQSAyQjCCASIw
DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKkLgb2eIcly4LZfj0Rf5F7s+HE/
6Tvpf4jsKkm7qs33y3EEudCbcPwQKjS2MgytPv+8xpEPHqy/hqTseNlZ6oJgc+V8
xlJ+0iws882Ca8a9ZJ/iGQH9UzXU4q35ArN3cbwoWAAvMvzZ6hUV86fAAQ1AueQN
6h7/tnfYfaUMiB4PNxucmouMHDJGmYzl47FtlLeHUr2c4m/oWSG5pADIvGFpWFHj
NIw8/x4n97w5/ks0tc/8/5Q6xzUfCX/VfqciQCvKcui2J5MBhUlBDLenzwqvUytB
4XAwX/pRcKmnFEYwoc9OKGExNx9tn9RjQYJAC/KLb44Jqno9l0eRxu3uw4sCAwEA
AaOBnzCBnDAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBBjAdBgNVHQ4E
FgQUEqW/kZ9/4q9qXAny4vpZ4Dbh81UwHwYDVR0jBBgwFoAUXvgbSKZ3ayk8LgBT
Mytjont+k8AwOQYDVR0fBDIwMDAuoCygKoYoaHR0cDovL2NybC5jYS5uZ3MuYWMu
dWsvY3JsL3Jvb3QtY3JsLmRlcjANBgkqhkiG9w0BAQsFAAOCAQEArd5TFOo9SzGW
0+KrAdzzf60zh4Wy//vZz4tgt7NeDbNpz2TZROBAClSu7oLPiruzgnhNP/Vxeu0s
pI41wRQsh0DVxhM+9ZFOskH+OdmHzKagoejvHh6Jt8WNN0eBLzN8Bvsue7ImJPaY
cf/Qj1ZTBhaRHcMsLNnqak3un/P+uLPxqSuxVKMtC8es/jqosS4czJ3dgs1hgFy9
nPQiwuIyf3OJ9eifAOGXk9Nlpha9C54zhc+hAkSLnpx/FhPjwLgpwDRgDJud6otH
15x3qZqXNx7xbYfeHaM1R1HMEjfVdzKCTY4zsqNEGPEF/0nUQSFk6KQVz0/ugNmI
9qoDx3FeEg==
-----END CERTIFICATE-----"""

TEST_HOST_CA = """-----BEGIN CERTIFICATE-----
MIIC+zCCAeOgAwIBAgIBATANBgkqhkiG9w0BAQsFADAfMQswCQYDVQQGEwJYWDEQ
MA4GA1UECwwHVGVzdCBDQTAeFw0xODAzMjIxMDI4MDZaFw0yODAzMTkxMDI4MDZa
MB8xCzAJBgNVBAYTAlhYMRAwDgYDVQQLDAdUZXN0IENBMIIBIjANBgkqhkiG9w0B
AQEFAAOCAQ8AMIIBCgKCAQEA/NuTJhxN/de9TA8Qswu2fgWnNBxVf9lVLbXDgL6K
1mohzxYBtG4tIWO2XED6Sm6E0wQgU6LlpZHWQG+Y16NPxR1F2n76VKeaMOnQljt4
TqHZbYlvoRfnXvclKAAxiJqYk7B6LUT7fjCPxxZxFYkohab/ttJcXK4Xu3IRDdZv
sI1oJdCZttxZOUhu4+vBgb1N8Njt6v6BYxHybi3RC7Y7Guyyrk/09k4Gf2yvqd7g
upZ26CqxRpazozr8LPAnmNFj3C1KzBNFR1MxIpYB+2jcdToI7a8uqP6JiyPtP94o
qmCmAI09wTcWAEtGqwDROKf0xcfke04rw1xVMvfUJ81+xQIDAQABo0IwQDAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBQ03TGsgDiOPNI9AUyX6VMy2dRTIDAOBgNV
HQ8BAf8EBAMCAQYwDQYJKoZIhvcNAQELBQADggEBACnRkmnpls8vcUhL+OAmzhwt
xKO9yQiDgRNICZBBXpHl/g3SZZ1aR8NJxfXW7Z0fZV0OTrCgOIT6L6QfzN2Q52ot
PPBdxKpTplWcI/pcx8LSYeDXc5E/X4IdeeksEcSTcxAqnAvWJpGsFpJqsiwMOVGe
QzMGtONjzZjacXlOmuZwHuPFL2Z5iLl8z38yPwUzQuv72UKa7w39fafx4ufOG8GT
1h9GEWwMiFLyuVI4wDaa9/qxhxHcmGxjNFK0+3AtiwIQGfG4fdtgSgIC+fzvoGmZ
mg7aHC1OCuhBmSRXtuezPvftl2yzoUUhSg75/UleQ0zCWSJkJyjIXf/m1jz5HJA=
-----END CERTIFICATE-----"""
