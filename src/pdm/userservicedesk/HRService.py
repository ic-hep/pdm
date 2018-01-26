#!/usr/bin/env python
__author__ = 'martynia'

import flask
from flask import request, abort
from pdm.framework.FlaskWrapper import export, export_ext, startup, db_model, jsonify
from pdm.framework.Database import from_json
import pdm.userservicedesk.models


@export_ext("/users/api/v1.0")
@db_model(pdm.userservicedesk.models.UserModel)
class HRService(object):

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
                'password' : user.password,
                'date_created': user.date_created,
                'date_modified': user.date_modified
            }
            results.append(obj)
        response = jsonify(results)
        response.status_code = 200
        return response

    @staticmethod
    @export_ext("users/<string:username>")
    def get_user(username):
        """
        Get user by username.
        :param username: username
        :return: json response with user data or 404 if the user does not exist
        """

        User = request.db.tables.User
        user = User.query.filter_by(username=username).first()
        if not user:
            # Raise an HTTPException with a 404 not found status code
            abort(404)

        result = [{
            'id': user.id,
            'username' : user.username,
            'name': user.name,
            'surname' : user.surname,
            'state' : user.state,
            #'dn' : user.dn,
            'email' : user.email,
            'password' : user.password,
            'date_created': user.date_created,
            'date_modified': user.date_modified
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
        print request.json
        User = request.db.tables.User
        user = User(username = request.json['username'], name =request.json['name'], surname = request.json['surname'],
                    email = request.json["email"], state = 0, password = request.json['password'])
        user.save()
        response = jsonify([{
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'surname': user.surname,
            'state' : user.state,
            #'dn' : user.dn,
            'email' : user.email,
            'password' :user.password,
            'date_created': user.date_created,
            'date_modified': user.date_modified
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

        user.save()

        response = jsonify([{
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'surname': user.surname,
            'state' : user.state,
            #'dn' : user.dn,
            'email' : user.email,
            'password' :user.password,
            'date_created': user.date_created,
            'date_modified': user.date_modified
        }])
        response.status_code = 200
        return response

    @staticmethod
    @export_ext("users/<string:username>", ["PUT"])
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
        user.delete()

        response = jsonify([{
            'message': "user %s deleted successfully" % (user.username,)
        }])

        response.status_code = 200
        return response