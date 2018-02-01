#!/usr/bin/env python
__author__ = 'martynia'

import flask
from flask import request, abort
from pdm.framework.FlaskWrapper import export, export_ext, startup, db_model, jsonify
import pdm.userservicedesk.models
import logging


@export_ext("/users/api/v1.0")
@db_model(pdm.userservicedesk.models.UserModel)
class HRService(object):

    _logger = logging.getLogger(__name__)

    @staticmethod
    @export
    def hello():
        return jsonify('User Service Desk at your service !\n')

    @staticmethod
    @export_ext("users")
    def get_users():
        """ Get all registered users """
        # GET
        User = request.db.tables.User
        users = User.get_all()
        results = []

        for user in users:
            obj = {
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
            }
            results.append(obj)
        response = jsonify(results)
        response.status_code = 200
        return response

#
#    @staticmethod
#    @export_ext("users/<string:username>")
#    def get_user(username):
    @staticmethod
    @export_ext("users/self")
    def get_user():
        """
        Get user own self based on id from the token passed in.
        :return: json response with user data or 404 if the user does not exist
        """

        if  request.token_ok:
            id = request.token[5:]
        else:
            abort(403)

        User = request.db.tables.User
        # user by id from the token
        user = User.query.filter_by(id=id).first()

        if not user:
            # Raise an HTTPException with a 404 not found status code
            HRService._logger.error("GET: requested user for id %s doesn't not exist ", id)
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
        #print request.json
        print 'server side: ', request.data
        User = request.db.tables.User
        user = User.from_json(request.data)
        #user = User(username = request.json['username'], name =request.json['name'], surname = request.json['surname'],
        #            email = request.json["email"], state = 0, password = request.json['password'])
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
    @export_ext("users/<string:username>", ["PUT"])
    def update_user(username):
        """
        Update an existing user.
        :param username: username of the user to be updated
        :return: json doc of the updated user or 404 if the user does not exist
        """

        User = request.db.tables.User
        user = User.query.filter_by(username=username).first()
        if not user:
            # Raise an HTTPException with a 404 not found status code
            abort(404)
        print request.json

        for key, value in request.json.iteritems():
            if key not in ['id','userid','date_created','date_modified']:
                setattr(user, key, value)

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
        response.status_code = 200
        return response

    @staticmethod
    @export_ext("users/<string:username>", ["DELETE"])
    def delete_user(username):
        """
        Delete a user
        :param username: a username of an existing user
        :return: code 200 if successful, 404 if the user does not exist
        """
        User = request.db.tables.User
        user = User.query.filter_by(username=username).first()

        if not user:
            # Raise an HTTPException with a 404 not found status code
            abort(404)

        db = request.db
        user.delete(db)

        response = jsonify([{
            'message': "user %s deleted successfully" % (user.username,)
        }])

        response.status_code = 200
        return response

    @staticmethod
    @export_ext("login", ["POST"])
    def get_token():
        HRService._logger.info("login request %s ", request.json)
        passwd = request.json['passwd']
        if not (passwd and HRService.check_passwd()):
            HRService._logger.error("login request:no password supplied: %s  ", request.json)
            abort(403)

        User = request.db.tables.User
        if  request.json['username']:
            user = User.query.filter_by(username=request.json['username']).first()
        elif request.json['email']:
            user = User.query.filter_by(email=request.json['email']).first()
        else:
            HRService._logger.error("login request:no username or email provided: %s  ", request.json)
            abort(403)

        if not user:
            HRService._logger.error("login request:user %s doesn't not exist ", request.json)
            abort(403)

        id = user.id
        if passwd != user.password:
            HRService._logger.info("login request %s failed (wrong password) ", request.json)
            abort(403)
        plain = "User_%s" %id
        HRService._logger.info("login request %s accepted ", request.json)
        token = request.token_svc.issue(plain)
        return jsonify(token)

    @staticmethod
    @export
    def verify_token():
        if request.token_ok:
            print "Token OK! (%s)" % request.token
            res = "Token OK! (%s)" % request.token
        else:
            res = "Token Missing!"
        return jsonify(res)

    @staticmethod
    def check_passwd():
        return True