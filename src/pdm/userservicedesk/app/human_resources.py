""" user administration interface """
__author__ = 'martynia'

from pdm.userservicedesk.app.models import User

from flask import request, jsonify, abort

def manage(app):

    @app.route('/users/api/v1.0/users', methods=['GET'])
    def get_users():
        """ Get all registered users """
        # GET
        users = User.get_all()
        results = []

        for user in users:
            obj = {
                'id': user.id,
                'username' : user.username,
                'name': user.name,
                'surname' : user.surname,
                'state' : user.state,
                'dn' : user.dn,
                'email' : user.email,
                'password' : user.password,
                'date_created': user.date_created,
                'date_modified': user.date_modified
            }
            results.append(obj)
        response = jsonify(results)
        response.status_code = 200
        return response

    @app.route('/users/api/v1.0/users/<string:username>', methods=['GET'])
    def get_user(username):
        """
        Get user by username.
        :param username: username
        :return: json response with user data or 404 if the user does not exist
        """
        user = User.query.filter_by(username=username).first()
        if not user:
            # Raise an HTTPException with a 404 not found status code
            abort(404)
#########
        #{k:v for k, v in user.__dict__.iteritems() if k in user.__table__.columns}

#########
        result = [{
            'id': user.id,
            'username' : user.username,
            'name': user.name,
            'surname' : user.surname,
            'state' : user.state,
            'dn' : user.dn,
            'email' : user.email,
            'password' : user.password,
            'date_created': user.date_created,
            'date_modified': user.date_modified
        }]
        response = jsonify(result)
        response.status_code = 200
        return response

    @app.route('/users/api/v1.0/users', methods=['POST'])
    def add_user():
        """
        Add a new user.
        :return: json document with added user data.
        """
        print request.json
        user = User(username = request.json['username'], name =request.json['name'], surname = request.json['surname'],
                    email = request.json["email"], state = request.json['state'], dn = request.json['dn'], password = request.json['password'])
        user.save()
        response = jsonify([{
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'surname': user.surname,
            'state' : user.state,
            'dn' : user.dn,
            'email' : user.email,
            'password' :user.password,
            'date_created': user.date_created,
            'date_modified': user.date_modified
        }])
        response.status_code = 201
        return response

    @app.route('/users/api/v1.0/users/<string:username>', methods=['PUT'])
    def update_user(username):
        """
        Update an existing user.
        :param username: username of the user to be updated
        :return: json doc of the updated user or 404 if the user does not exist
        """
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
            'dn' : user.dn,
            'email' : user.email,
            'password' :user.password,
            'date_created': user.date_created,
            'date_modified': user.date_modified
        }])
        response.status_code = 200
        return response

    @app.route('/users/api/v1.0/users/<string:username>', methods=['DELETE'])
    def delete_user(username):
        """
        Delete a user
        :param username: a username of an existing user
        :return: code 200 if successful, 404 if the user does not exist
        """
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

    return app
