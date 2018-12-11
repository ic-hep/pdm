#!/usr/bin/env python
"""
User Interface Service
"""

import sys
import os
import logging
import json
import time
import datetime
import smtplib
import socket
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from enum import IntEnum

from sqlalchemy import func
from flask import request, abort, current_app
from pdm.framework.FlaskWrapper import jsonify
from pdm.framework.Decorators import export, export_ext, db_model, startup
from pdm.utils.hashing import hash_pass, check_hash
from pdm.framework.Tokens import TokenService
import pdm.userservicedesk.models
from HRUtils import HRUtils
from pdm.site.SiteClient import SiteClient

class HRServiceUserState(IntEnum):
    """
    User State enumeration.
    """
    REGISTERED = 0
    VERIFIED = 1
    DISABLED = -1


@export_ext("/users/api/v1.0")
@db_model(pdm.userservicedesk.models.UserModel)
class HRService(object):
    """
    User Interface RESTful Web Service class.

    """
    _logger = logging.getLogger(__name__)

    @staticmethod
    @startup
    def load_userconfig(config):
        """ Configure the HRService application.
            Gets the key needed to contact the Credential Service
        """
        current_app.pwd_len = config.pop("pswd_length", 8)
        # token validity period struct (from: HH:MM:SS)
        try:
            time_struct = time.strptime(config.pop("token_validity", "12:00:00"), "%H:%M:%S")
            current_app.token_duration = datetime.timedelta(hours=time_struct.tm_hour,
                                                            minutes=time_struct.tm_min,
                                                            seconds=time_struct.tm_sec)
        except ValueError as v_err:
            HRService._logger.error(" Token lifetime provided in the config "
                                    "file has wrong format %s. Aborting.", v_err)
            raise ValueError("Token lifetime incorrect format %s" % v_err)

        # verification email:
        current_app.token_url = config.pop("token_url", "https://localhost:5443/web/verify")
        current_app.smtp_server = config.pop("SMTP_server", None)
        if current_app.smtp_server is None:
            HRService._logger.error(" Mail server not provided in the config. Aborting")
            raise ValueError(" Mail server not provided in the config. Aborting")

        current_app.smtp_server_port = config.pop("SMTP_server_port", None)
        current_app.smtp_server_login = config.pop("SMTP_server_login", None)
        current_app.mail_display_from = config.pop("display_from_address", None)
        current_app.smtp_server_pwd = config.pop("SMTP_server_pwd", None)
        current_app.mail_subject = config.pop("mail_subject", None)
        current_app.mail_expiry = config.pop("mail_expiry", "12:00:00")
        current_app.smtp_server_startTLS = config.pop('SMTP_startTLS', 'REQUIRED')
        current_app.smtp_server_login_req = config.pop('SMTP_login_req', 'REQUIRED')

        current_app.verification_url = \
            config.pop("verification_url",
                       "https://pdm.grid.hep.ph.ic.ac.uk:5443/web/verify")
        current_app.mail_token_secret = config.pop("mail_token_secret")
        current_app.mail_token_duration = config.pop("mail_token_validity", '24:00:00')
        #
        current_app.token_service = TokenService(current_app.mail_token_secret)
        # site client
        current_app.site_client = SiteClient()

    @staticmethod
    @export
    def hello():
        """
        Ping-like method.

        :return: nice greeting ;-)
        """
        return jsonify('User Service Desk at your service !\n')

    @staticmethod
    @export_ext("users/self")
    def get_user():
        """
        Get user own self based on user_id from the token passed in.

        :return: json response with user data or 404 if the user does not exist
        """

        user_id = HRService.check_token()

        User = request.db.tables.User
        # user by id from the token
        user = User.query.filter_by(id=user_id).first()

        if not user:
            # Raise an HTTPException with a 404 not found status code
            HRService._logger.error("GET: requested user for id %s doesn't exist ", user_id)
            abort(404)

        response = jsonify(user)
        response.status_code = 200
        return response

    @staticmethod
    @export_ext("users", ["POST"])
    def add_user():
        """
        Add a new user.

        :return: json document with added user data. An HTTPException with a
                 403 status code is thrown when the user already exists. User
                 email address and a password are obligatory (404 is emitted
                 otherwise).
        """
        data = json.loads(request.data)

        if not 'email' in data:
            HRService._logger.error("add user request:no email supplied")
            abort(400)

        if not 'password' in data:
            HRService._logger.error("add user request:no password supplied")
            abort(400)

        if not HRService.check_passwd(data['password']):
            return "Password supplied is too short (lower character limit is %d)" \
                   % current_app.pwd_len, 400

        data['password'] = hash_pass(data['password'])

        User = request.db.tables.User
        data.pop('last_login', None)
        data.pop('date_created', None)
        data.pop('date_modified', func.current_timestamp())
        data.pop('state', 0)
        # user = User.from_json(json.dumps(data))
        user = User(**data)
        db = request.db

        try:
            # user.save(db)
            db.session.add(user)
            user_id = db.session.query(User.id).filter_by(email=data['email']).scalar()
            # email the user
            HRService.email_user(user.email)
            HRService._logger.info("user: %s: verification email sent. ", user.email)
            db.session.commit()
        except RuntimeError as r_error:
            db.session.rollback()
            HRService._logger.error("Runtime error when trying to send an email\n: %s", r_error)
            HRService._logger.error("User %s not added.", user.email)
            abort(500, 'The server could not send the verification email.')
        except Exception:
            HRService._logger.error("Failed to add user: %s ", sys.exc_info())
            db.session.rollback()
            abort(403)  # 500 ?

        # dict
        response = jsonify(user)
        response.status_code = 201
        return response

    @staticmethod
    @export_ext("verify", ["POST"])
    def verify_user():
        """
        Verify users' email address. Data posted is a token which has to ve verified and unpacked.
        The email address contained in the token is compared with the email stored in the DB.
        User state is changed to 1 (verified) if successful.
        :return:
        """

        data = json.loads(request.data)
        HRService._logger.info("Data received for validation: %s", data)
        try:
            mtoken = data['mailtoken']
            current_app.token_service.check(mtoken)
            HRService._logger.info("Mailer token verified OK")
            # token checked for integrity, check if not expired
            if HRUtils.is_token_expired_insecure(mtoken):
                HRService._logger.error("Email verification token expired.")
                abort(400, "Bad token or already verified")
            username = HRUtils.get_token_username_insecure(mtoken)
            HRService.update_user_status(username, HRServiceUserState.VERIFIED)
            response = jsonify([{'Verified': 'OK'}])
            response.status_code = 201
            return response
        except ValueError as ve:
            HRService._logger.error("Mailer token integrity verification failed (%s)", ve)
            abort(400, "Bad token or already verified")
        return None

    @staticmethod
    def update_user_status(username, status, flag=False):
        """
        Update user status in the db.
        :param username: user email address
        :param status: new status
        :param flag: if True update to the same status is allowed.
        :return: None
        """
        HRService._logger.info("Updating user %s status to %d", username, status)

        User = request.db.tables.User
        user = User.query.filter_by(email=username).first()
        if not user:
            # Raise an HTTPException with a 403 not found status code
            HRService._logger.error("Updating user status: requested user for id %s doesn't exist ",
                                    username)
            abort(400)
        if user.state == status and not flag:
            HRService._logger.error("User already verified.")
            abort(400, ' Invalid token or already verified')
        user.state = status

        try:
            request.db.session.add(user)
            request.db.session.commit()
            HRService._logger.info("User status updated successfully for user %s ", username)
        except:
            HRService._logger.error("Failed to update user %s status %s ",
                                    username, sys.exc_info())
            request.db.session.rollback()
            abort(500)

    @staticmethod
    @export_ext("passwd", ["PUT"])
    def change_password():
        """
        Method to change user password. Requite old password, new password and a valid token.

        :return: response object containing user name, surname and date modified
        """
        HRService._logger.info("password change request ...")
        user_id = HRService.check_token()
        db = request.db
        if user_id:
            HRService._logger.info("... for user id =  %d ", user_id)
            User = request.db.tables.User
            data = json.loads(request.data)
            if not 'newpasswd' in data:
                HRService._logger.error("add user request:no new password supplied")
                abort(400)
            if not 'passwd' in data:
                HRService._logger.error("add user request:no old password supplied")
                abort(400)

            password = data['passwd']
            newpasswd = data['newpasswd']

            if not (password and newpasswd \
                            and HRService.check_passwd(password) \
                            and HRService.check_passwd(newpasswd)):
                HRService._logger.error("passwd change request:" \
                                        "null password and/or new password, supplied: %s  ",
                                        request.json)
                return "Null password and/or new password " \
                       "or password supplied is too short (lower character limit is %d)" \
                       % current_app.pwd_len, 400

                # user by id from the token
            user = User.query.filter_by(id=user_id).first()

            if not user:
                # Raise an HTTPException with a 403 not found status code
                HRService._logger.error("GET: requested user for id %s doesn't exist ", user_id)
                abort(403)

        # OK, got the user matching the token, now verify the old passwd:
        email = user.email
        if check_hash(user.password, password):

            if check_hash(user.password, newpasswd):
                HRService._logger.error("Password update FAILED for user %s (same password)",
                                        email)
                abort(400)

            user.password = hash_pass(newpasswd)
            user.date_modified = func.current_timestamp()
            # User update
            try:
                db.session.add(user)
                db.session.commit()
                HRService._logger.info("Password updated successfully for user %s ", email)
            except Exception:
                HRService._logger.error("Failed to change passwd: %s or post to the CS",
                                        sys.exc_info())
                db.session.rollback()
                abort(500)

        else:
            HRService._logger.error("Password update FAILED for user %s (wrong password)", email)
            abort(403)

        response = jsonify(user)
        response.status_code = 200
        return response

    @staticmethod
    @export_ext("users/self", ["DELETE"])
    def delete_user():
        """
        Delete a user. The user can only delete himself.

        :return: response object with code 200 if successful, 404 if the user does not exist
        """

        user_id = HRService.check_token()
        # exception thrown if no user_id

        db = request.db
        User = request.db.tables.User
        user = User.query.filter_by(id=user_id).first()

        if not user:
            # Raise an HTTPException with a 404 not found status code
            HRService._logger.error("GET: requested user for id %s doesn't exist ", user_id)
            abort(404)

        try:
            db.session.delete(user)
            current_app.site_client.set_token(request.raw_token)
            current_app.site_client.del_user(user_id)
            db.session.commit()
            HRService._logger.info(" User %s deleted successfully", user_id)
        except Exception:
            db.session.rollback()
            HRService._logger.error(" Failed to delete a user %s (%s)", user_id, sys.exc_info())
            abort(500)

        response = jsonify([{
            'message': "user %s deleted successfully" % (user.email,)
        }])

        response.status_code = 200
        return response

    @staticmethod
    @export_ext("login", ["POST"])
    def get_token():
        """
        User login procedure.

        :return: token
        """

        # empty request ?
        if not request.data:
            HRService._logger.error("login request:no data supplied (emty request)")
            abort(400)

        try:
            data = json.loads(request.data)
        except ValueError as verror:
            HRService._logger.error("login request exception:%s", str(verror))
            abort(400)

        if not ('email' in data and 'passwd' in data):
            HRService._logger.error("login request:no password or email supplied")
            abort(400)

        HRService._logger.info("login request %s ", data['email'])
        passwd = data['passwd']
        if not (passwd and HRService.check_passwd(passwd)):
            HRService._logger.error("login request:None password supplied or too weak")
            abort(400)

        db = request.db
        User = request.db.tables.User
        user = User.query.filter_by(email=data['email']).first()

        if not user:
            HRService._logger.error("login request:user %s doesn't exist ", data['email'])
            abort(403)

        user_id = user.id
        if not check_hash(user.password, passwd):
            HRService._logger.info("login request for %s failed (wrong password) ", data['email'])
            abort(403)
            # check if user account is verified
        if user.state != HRServiceUserState.VERIFIED:
            HRService._logger.error("User login  FAILED for user %s "
                                    "(unverified, password correct)", user.email)
            abort(401, 'USER_UNVERIFIED_LOGIN')
        # issue a token and return it to the client
        expiry = datetime.datetime.utcnow() + current_app.token_duration
        plain = {'id': user_id, 'expiry': expiry.isoformat(), 'email': user.email}
        HRService._logger.info("login request accepted for %s", data['email'])
        token = request.token_svc.issue(plain)
        try:
            user.last_login = func.current_timestamp()
            db.session.add(user)
            db.session.commit()
        except:
            db.session.rollback()
            HRService._logger.error("login request:cooudn't update user %s last login field",
                                    data['email'])
            abort(500)

        return jsonify(token)

    @staticmethod
    def check_passwd(passwd):
        """
        Very basic password check.

        :param passwd:  password to be checked.
        :return: True of False
        """
        if len(passwd) < current_app.pwd_len:
            HRService._logger.error("Password too short %d (lower limit = %d)",
                                    len(passwd), current_app.pwd_len)
            return False

        return True

    @staticmethod
    def check_token():
        """
        Token validity helper. Check token integrity and expiry date. Emit 403 if the check fails.

        :return: user id from the token.
        """
        isoformat = '%Y-%m-%dT%H:%M:%S.%f'
        if request.token_ok:
            expiry_iso = request.token.get('expiry')
            if not expiry_iso:
                HRService._logger.error("Token does not contain expiry information")
                abort(500)
            if datetime.datetime.strptime(expiry_iso, isoformat) < datetime.datetime.utcnow():
                HRService._logger.error("Token expired on %s", expiry_iso)
                abort(403)
            user_id = request.token['id']
        else:
            user_id = None
            HRService._logger.error("Token invalid (%s)", request.token)
            abort(403)

        return user_id

    @staticmethod
    def get_token_userid(token):
        """
        Get the value of the 'key' part of the token to be used to contact the CS
        The token holds internally:
        id: user id
        expiry: expiry info (to be decided)
        key: hashed key (from pdm.utils.hashing.hash_pass()).

        :param   token: encrypted token
        :return: the value of the 'key' field of the token dictionary
        """
        unpacked_user_token = TokenService.unpack(token)
        userid = unpacked_user_token.get('id', None)
        return userid

    @staticmethod
    def email_user(to_address):
        """
        Send an email to a user identified by to_address. Raises a RuntimeError if
        unsuccessful.

        :param to_address: user email
        :return: None
        """
        expiry = datetime.datetime.utcnow() + current_app.token_duration
        plain = {'expiry': expiry.isoformat(), 'email': to_address}
        HRService._logger.info("login request accepted for %s", to_address)
        token = current_app.token_service.issue(plain)
        HRService._logger.info("email verification token issued for %s, (expires on %s)",
                               to_address, expiry.isoformat())
        HRService._logger.info("Token:%s", token)

        HRService.compose_and_send(to_address, token)

    @staticmethod
    def compose_and_send(to_address, mail_token):
        """
        Compose the email. Initialise the SMTP server, login and send the email.
        Raises a RuntimeError if any of the email preparation and sending steps fail.

        :param to_address: mail recipient address
        :param mail_token: a url with a token included in the email body.
        :return: None
        """

        fromaddr = current_app.smtp_server_login  # this has to be a routable host
        smtp_server = current_app.smtp_server
        smtp_port = current_app.smtp_server_port
        smtp_server_pwd = current_app.smtp_server_pwd
        toaddr = to_address
        msg = MIMEMultipart()
        msg['From'] = current_app.mail_display_from
        msg['To'] = to_address
        msg['Subject'] = current_app.mail_subject

        body = os.path.join(current_app.verification_url, mail_token)
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
        except smtplib.SMTPException as smtp_e:
            HRService._logger.error("SMTP error %s", smtp_e)
            raise RuntimeError(smtp_e)
        except socket.error as se:
            HRService._logger.error("smtplib socket error %s", se)
            raise RuntimeError(se)

        if current_app.smtp_server_startTLS != 'OFF':
            try:
                server.starttls()
            except smtplib.SMTPException as smtp_e:
                # will continue w/o TLS, if optional
                HRService._check_server_requirements(current_app.smtp_server_startTLS, smtp_e)

            try:
                server.login(fromaddr, smtp_server_pwd)
            except smtplib.SMTPException as smtp_e:
                # will continue w/o login, if optional
                HRService._check_server_requirements(current_app.smtp_server_login_req, smtp_e)

        text = msg.as_string()
        try:
            server.sendmail(fromaddr, toaddr, text)
        except smtplib.SMTPException as smtp_e:
            HRService._logger.error("%s, SMTP sendmail error:", smtp_e)
            raise RuntimeError(smtp_e)
        server.quit()

    @staticmethod
    def _check_server_requirements(flag, smtp_e):
        if flag == 'OPTIONAL':
            HRService._logger.info("%s, SMTP %s OPTIONAL, continue...", smtp_e, flag)
        else:
            HRService._logger.error("%s, SMTP %s REQUIRED ", smtp_e, flag)
            raise RuntimeError(smtp_e)


            ### Quarantine below this line.
            ### Code which might be cosidered in the future version of the service

            # @staticmethod
            # @export_ext("users")
            # def get_users():
            #     """ Get all registered users (NOT for a regular user!)"""
            #     # GET
            #     User = request.db.tables.User
            #     users = User.get_all()
            #     results = []
            #
            #     for user in users:
            #         obj = {
            #             'id': user.id,
            #             'username' : user.username,
            #             'name': user.name,
            #             'surname' : user.surname,
            #             'state' : user.state,
            #             #'dn' : user.dn,
            #             'email' : user.email,
            #             #'password' : user.password,
            #             'date_created': str(user.date_created),
            #             'date_modified': str(user.date_modified)
            #         }
            #         results.append(obj)
            #     response = jsonify(results)
            #     response.status_code = 200
            #     return response
            #
            # @staticmethod
            # @export_ext("users/<string:username>", ["PUT"])
            # def update_user(username):
            #     """
            #     Update an existing user. NOT for a regular user !
            #     :param username: username of the user to be updated
            #     :return: json doc of the updated user or 404 if the user does not exist
            #     """
            #
            #     User = request.db.tables.User
            #     user = User.query.filter_by(username=username).first()
            #     if not user:
            #         # Raise an HTTPException with a 404 not found status code
            #         abort(404)
            #     print request.json
            #
            #     for key, value in request.json.iteritems():
            #         if key not in ['id','userid','date_created','date_modified','email']:
            #             setattr(user, key, value)
            #
            #     db = request.db
            #     user.save(db)
            #
            #     response = jsonify([{
            #         'id': user.id,
            #         'name': user.name,
            #         'username': user.username,
            #         'surname': user.surname,
            #         'state' : user.state,
            #         #'dn' : user.dn,
            #         'email' : user.email,
            #         #'password' :user.password,
            #         'date_created': str(user.date_created),
            #         'date_modified': str(user.date_modified)
            #     }])
            #     response.status_code = 200
            #     return response
