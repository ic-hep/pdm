#!/usr/bin/env python
"""
User Interface Service
"""

import sys
import logging
import json
from flask import request, abort
from pdm.framework.FlaskWrapper import export, export_ext, db_model, jsonify
from pdm.utils.hashing import hash_pass, check_hash
import pdm.userservicedesk.models
from sqlalchemy import func

@export_ext("/users/api/v1.0")
@db_model(pdm.userservicedesk.models.UserModel)
class HRService(object):
    """
    User Interface RESTful Web Service class.

    """
    _logger = logging.getLogger(__name__)

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
            HRService._logger.error("GET: requested user for id %s doesn't not exist ", user_id)
            abort(404)

        result = [{
            # 'id': user.id,
            'name': user.name,
            'surname': user.surname,
            'state': user.state,
            # 'dn' : user.dn,
            'email': user.email,
            # 'password' : user.password,
            'last_login': str(user.last_login),
            'date_created': str(user.date_created),
            'date_modified': str(user.date_modified)
        }]
        response = jsonify(result)
        response.status_code = 200
        return response

    @staticmethod
    @export_ext("users", ["POST"])
    def add_user():
        """
        Add a new user.
        :return: json document with added user data. An HTTPException with a 403 status code is
        thrown when the user already exists. User email address and a password are obligatory (404 is
        emitted otherwise).
        """
        data = json.loads(request.data)

        if not 'email' in data:
            HRService._logger.error("add user request:no email supplied")
            abort(404)

        if not 'password' in data:
            HRService._logger.error("add user request:no password supplied")
            abort(404)

        if not HRService.check_passwd(data['password']):
            abort(404)

        data['password'] = hash_pass(data['password'])

        User = request.db.tables.User
        user = User.from_json(json.dumps(data))

        db = request.db
        try:
            user.save(db)
        except Exception:
            HRService._logger.error("Failed to add user: %s ", sys.exc_info())
            abort(403)
        response = jsonify([{
            'id': user.id,
            'name': user.name,
            # 'username': user.username,
            'surname': user.surname,
            'state': user.state,
            # 'dn' : user.dn,
            'email': user.email,
            # 'password' :user.password,
            'date_created': str(user.date_created),
            'date_modified': str(user.date_modified)
        }])
        response.status_code = 201
        return response

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
                abort(403)
            if not 'passwd' in data:
                HRService._logger.error("add user request:no old password supplied")
                abort(403)

            password = data['passwd']
            newpasswd = data['newpasswd']

            if not (password and newpasswd and HRService.check_passwd(password) and HRService.check_passwd(newpasswd)):
                HRService._logger.error("passwd change request:null password and/or new password, supplied: %s  ",
                                        request.json)
                abort(403)

                # user by id from the token
            user = User.query.filter_by(id=user_id).first()

            if not user:
                # Raise an HTTPException with a 404 not found status code
                HRService._logger.error("GET: requested user for id %s doesn't exist ", user_id)
                abort(404)

        # OK, got the user matching the token, now verify the old passwd:
        email = user.email
        if check_hash(user.password, password):

            if check_hash(user.password, newpasswd):
                HRService._logger.error("Password update FAILED for user %s (same password)", email)
                abort(403)

            user.password = hash_pass(newpasswd)
            user.last_login = func.current_timestamp()
            user.save(db)
            HRService._logger.info("Password updated successfully for user %s ", email)
        else:
            HRService._logger.error("Password update FAILED for user %s (wrong password)", email)
            abort(403)

        response = jsonify([{
            'email': user.email,
            'name': user.name,
            'surname': user.surname,
            'last_login': str(user.last_login),
            'date_modified': str(user.date_modified)}])
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
        db = request.db

        if user_id:
            User = request.db.tables.User
            user = User.query.filter_by(id=user_id).first()

        if not user:
            # Raise an HTTPException with a 404 not found status code
            HRService._logger.error("GET: requested user for id %s doesn't exist ", user_id)
            abort(404)

        user.delete(db)

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
        data = json.loads(request.data)

        if not ('email' in data and 'passwd' in data):
            HRService._logger.error("login request:no password or email supplied")
            abort(404)

        HRService._logger.info("login request %s ", data['email'])
        passwd = data['passwd']
        if not (passwd and HRService.check_passwd(passwd)):
            HRService._logger.error("login request:None password supplied or too weak")
            abort(403)

        User = request.db.tables.User
        user = User.query.filter_by(email=data['email']).first()

        if not user:
            HRService._logger.error("login request:user %s doesn't exist ", data['email'])
            abort(403)

        user_id = user.id
        if not check_hash(user.password, passwd):
            HRService._logger.info("login request for %s failed (wrong password) ", data['email'])
            abort(403)
        plain = "User_%s" % user_id
        HRService._logger.info("login request accepted for %s", data['email'])
        token = request.token_svc.issue(plain)
        return jsonify(token)

    # @staticmethod
    # @export
    # def verify_token():
    #     if request.token_ok:
    #         print "Token OK! (%s)" % request.token
    #         res = "Token OK! (%s)" % request.token
    #     else:
    #         res = "Token Missing!"
    #     return jsonify(res)

    @staticmethod
    def check_passwd(passwd):
        """
        (Very) basic password check
        :param passwd:
        :return: True of False
        """
        if len(passwd) < 8:
            return False

        return True

    @staticmethod
    def check_token():
        """
        Token validity helper
        :return: user id from the token or None.
        """

        if request.token_ok:
            user_id = request.token[5:]
        else:
            user_id = None
            HRService._logger.error("Token invalid (%s)", request.token)
            abort(403)

        return user_id

        ### Quarantine below this line. Code which might be cosidered in the future version of the interface

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
