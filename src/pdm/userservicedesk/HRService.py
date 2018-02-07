#!/usr/bin/env python
__author__ = 'martynia'

from flask import request, abort
from pdm.framework.FlaskWrapper import export, export_ext, startup, db_model, jsonify
import pdm.userservicedesk.models
import logging
import json


@export_ext("/users/api/v1.0")
@db_model(pdm.userservicedesk.models.UserModel)
class HRService(object):

    _logger = logging.getLogger(__name__)

    @staticmethod
    @export
    def hello():
        return jsonify('User Service Desk at your service !\n')



    @staticmethod
    @export_ext("users/self")
    def get_user():
        """
        Get user own self based on user_id from the token passed in.
        :return: json response with user data or 404 if the user does not exist
        """

        if  request.token_ok:
            user_id = request.token[5:]
        else:
            abort(403)

        User = request.db.tables.User
        # user by id from the token
        user = User.query.filter_by(id=user_id).first()

        if not user:
            # Raise an HTTPException with a 404 not found status code
            HRService._logger.error("GET: requested user for id %s doesn't not exist ", user_id)
            abort(404)

        #if not (user.username == username or user.email == username):
        #    # unathorised
        #    HRService._logger.error("GET: user's id %s does not match the username or email %s (other existing users's token supplied)", id, username)
        #    abort(403)

        result = [{
            'id': user.id,
            'username' : user.username,
            'name': user.name,
            'surname' : user.surname,
            'state' : user.state,
            #'dn' : user.dn,
            'email' : user.email,
            #'password' : user.password,
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
        :return: json document with added user data.
        """
        data = json.loads(request.data)
        if not HRService.check_passwd(data['password']):
            abort(404)

        User = request.db.tables.User
        user = User.from_json(request.data)

        db = request.db
        user.save(db)
        response = jsonify([{
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'surname': user.surname,
            'state' : user.state,
            #'dn' : user.dn,
            'email' : user.email,
            #'password' :user.password,
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
        :return: responce object containing user name, surname and date modified
        """
        HRService._logger.info("password change request %s ", request.json)
        user_id = HRService.check_token()
        db = request.db
        if user_id:
            User = request.db.tables.User
            data_dict = json.loads(request.data)
            password = data_dict['passwd']
            newpasswd = data_dict['newpasswd']

            if not (password and newpasswd and HRService.check_passwd(password) and HRService.check_passwd(newpasswd) ):
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
        if user.password == password:

            if user.password == newpasswd:
                HRService._logger.error("Password update FAILED for user %s (same password)", email)
                abort(403)

            user.password = newpasswd
            user.save(db)
            HRService._logger.info("Password updated successfully for user %s ", email)
        else:
            HRService._logger.error("Password update FAILED for user %s (wrong password)", email)
            abort(403)

        response = jsonify([{
            'id': user.id,
            'name': user.name,
            'surname': user.surname,
            'date_modified': str(user.date_modified)}]
        )
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

        id = user.id
        if passwd != user.password:
            HRService._logger.info("login request for %s failed (wrong password) ", data['email'])
            abort(403)
        plain = "User_%s" %id
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
        if len(passwd) < 8:
            return False
        else:
            return True

    @staticmethod
    def check_token():

        if  request.token_ok:
            user_id = request.token[5:]
        else:
            user_id = None
            HRService._logger.error("Token invalid (%s)") % request.token
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