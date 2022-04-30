import logging

from flask import jsonify, request
from flask_restful import reqparse, abort, Resource
from .users import User
from . import db_session


class UsersResource(Resource):
    def put(self, user_id):
        abort_if_user_not_found(user_id)

        session = db_session.create_session()
        user = session.query(User).get(user_id)
        user.id_shopping_lst = request.json["id_shopping_lst"]
        session.commit()
        return jsonify({"success": "OK"})


class UsersListResource(Resource):
    def get(self):
        session = db_session.create_session()
        users = session.query(User).all()
        return jsonify({"users": [item.to_dict(only=("id", "username", "id_shopping_lst")) for item in users]})

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("username", required=True)
        parser.add_argument("email", required=True)
        args = parser.parse_args()
        session = db_session.create_session()
        cur_user = session.query(User).filter(User.email == args["email"]).first()
        if cur_user is not None and args["email"] == cur_user.email:
            abort_user_found()
        user = User()
        user.username = args["username"]
        user.email = args["email"]
        session.add(user)
        session.commit()
        return jsonify({"success": "OK"})


def abort_user_found():
    logging.error(abort(406, message=f"User already exists. Change email"))


def abort_if_user_not_found(user_id):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        logging.error(abort(404, message=f"User with id {user_id} not found"))