import json

import requests
import logging
import sqlite3
from flask_restful import Api
from flask import render_template, Flask, request, redirect, make_response
from data import db_session
from forms.user_registration_form import UserRegistrationForm
from forms.user_login_form import UserLoginForm
from data.users import User
from data import users_resources
from config import *

logging.basicConfig(filename="total.log", level=logging.INFO)
with open("total.log", "w"):
    pass
app = Flask(__name__)
app.config["SECRET_KEY"] = "elmir"
api = Api(app)
api.add_resource(users_resources.UsersResource, "/api/users/<int:user_id>")
api.add_resource(users_resources.UsersListResource, "/api/users")


@app.route("/", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/<int:page>", methods=["GET", "POST"])
def index(page):
    games = get_games(page)
    games_discount_price = list(map(lambda x: get_item_discount_price(x[0]), games))
    logging.error(request.cookies.get("authorized"))

    if int(request.cookies.get("authorized", "0")) and request.cookies.get("authorized") is not None and \
            request.cookies.get("user_id") is not None:
        return redirect(f"/authorized")
    elif request.cookies.get("authorized") is None or request.cookies.get("user_id") is not None:
        res = make_response(render_template("index.html", authorized=0, games_data=[games, games_discount_price],
                                            page=page, GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE))
        res.set_cookie("authorized", str(0), max_age=60 * 60 * 24 * 7)
        return res

    return render_template("index.html", authorized=0, games_data=[games, games_discount_price], page=page,
                           GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)


@app.route("/authorized", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/authorized/<int:page>", methods=["GET", "POST"])
def authorized_user_index(page):
    logging.warning(f"{request.cookies.get('authorized', 'no')}, {request.cookies.get('user_id', 'no')}")
    games = get_games(page)
    games_discount_price = list(map(lambda x: get_item_discount_price(x[0]), games))
    logging.warning(get_user(int(request.cookies.get("user_id"))))
    return render_template("index.html", authorized=1, games_data=[games, games_discount_price],
                           user=get_user(int(request.cookies.get("user_id"))), page=page,
                           GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)


@app.route("/registration", methods=["GET", "POST"])
def registration():
    user_form = UserRegistrationForm()
    try:
        if request.method == "POST":
            if user_form.validate_on_submit():
                logging.warning(f"""{user_form.username.data}, {user_form.email.data.lower()}, 
{user_form.password.data}, {user_form.password_again.data}""")
                if user_form.password.data != user_form.password_again.data:
                    raise ValueError()
                status_code = requests.post(f"{request.url[:request.url.find('/registration')]}/api/users",
                                            json={"username": user_form.username.data,
                                                  "email": user_form.email.data.lower()}).status_code
                if status_code == 200:
                    db_sess = db_session.create_session()
                    user = db_sess.query(User).filter(User.email == user_form.email.data.lower()).first()
                    user.set_hashed_password(user_form.password.data)
                    db_sess.commit()
                    logging.warning(user.id)
                    res = make_response(redirect(f"/authorized"))
                    res.set_cookie("authorized", str(1), max_age=60 * 60 * 24 * 7)
                    res.set_cookie("user_id", str(user.id), max_age=60 * 60 * 24 * 7)
                    return res
    except ValueError as error_name:
        logging.error(str(error_name))
    return render_template("registration.html", user_form=user_form)


@app.route("/login", methods=["GET", "POST"])
def login():
    user_form = UserLoginForm()
    try:
        if request.method == "POST":
            db_sess = db_session.create_session()
            logging.warning(user_form.email.data.lower())
            user = db_sess.query(User).filter(User.email == user_form.email.data.lower()).first()
            logging.warning(user)
            if user is None or not user.check_password(user_form.password.data):
                raise ConnectionError()
            res = make_response(redirect("/authorized"))
            res.set_cookie("authorized", str(1), max_age=60 * 60 * 24 * 7)
            res.set_cookie("user_id", str(user.id), max_age=60 * 60 * 24 * 7)
            return res
    except ConnectionError as error_name:
        logging.error(str(error_name))
    return render_template("login.html", user_form=user_form)


@app.route("/sign_out", methods=["GET", "POST"])
def sign_out():
    res = make_response(redirect("/"))
    res.set_cookie("authorized", "None", max_age=0)
    res.set_cookie("user_id", "None", max_age=0)
    return res


@app.route("/game/<int:game_id>", methods=["GET", "POST"])
def game_tab(game_id):
    if request.method == "POST":
        user_id = request.cookies.get("user_id", "None")
        if user_id != "None":
            db_sess = db_session.create_session()
            user = db_sess.query(User).get(user_id)
            status_code = requests.put(f"{request.url[:request.url.find('/game')]}/api/users/{user_id}",
                                       json={"id_shopping_lst": user.id_shopping_lst + f'{game_id};'})
            logging.warning(user.id_shopping_lst)
            logging.info(f"game_tab {status_code}")
        else:
            logging.warning("user_id in func game tab not found")
        return redirect(f"/authorized")

    game_item = get_game_item(game_id)
    game_item_discount_price = get_item_discount_price(game_id)
    logging.warning(game_item)
    logging.warning(game_item_discount_price)
    logging.warning(game_item_discount_price["prices"])
    user = None
    if request.cookies.get("user_id") is not None:
        user = get_user(int(request.cookies.get("user_id")))
    return render_template("game_tab.html", authorized=int(request.cookies.get("authorized", "0")),
                           game_item=game_item, game_links=json.loads(game_item[6]),
                           min_sys_req=json.loads(game_item[8]), prices=game_item_discount_price["prices"], user=user)


@app.route("/basket", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/basket/<int:page>", methods=["GET", "POST"])
def user_basket(page):
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(request.cookies.get("user_id"))
    if request.method == "POST":
        command, value = request.form.get("activity").split()
        if command == "add_one_el":
            user.id_shopping_lst = user.id_shopping_lst + value + ";"
        elif command == "del_one_el":
            user.id_shopping_lst = user.id_shopping_lst.replace(value + ";", "", 1)
        db_sess.commit()

    if user.id_shopping_lst:
        games = list(map(lambda x: get_game_item(int(x)), user.id_shopping_lst.split(";")[:-1]))
        logging.warning(list(set(games)))

        games = list(map(lambda x: list(x) + [games.count(x)], list(set(games))))
        games_discount_price = list(map(lambda x: get_item_discount_price(x[0]), games))
        total_amount = 0
        for game in games:
            total_amount = total_amount + list(filter(lambda x: x['id'] == game[0],
                                                      games_discount_price))[0]["mn_price"] * game[9]

        return render_template("basket.html", games_data=[games, games_discount_price], total_amount=total_amount,
                               page=page, GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)
    return render_template("basket.html", games_data=[[], []], total_amount=0, page=page,
                           GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)


@app.route("/searching", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/<int:page>/searching", methods=["GET", "POST"])
def searching(page):
    game_name = request.form.get("searching_line").lower()
    games = list(filter(lambda x: game_name.lower() in x[1].lower(), get_games(page)))
    games_discount_price = list(map(lambda x: get_item_discount_price(x[0]), games))
    return render_template("index.html", authorized=0, games_data=[games, games_discount_price], page=page,
                           GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)


@app.route("/authorized/searching", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/authorized/<int:page>/searching", methods=["GET", "POST"])
def authorized_searching(page):
    game_name = request.form.get("searching_line").lower()
    games = list(filter(lambda x: game_name in x[1].lower(), get_games(page)))
    games_discount_price = list(map(lambda x: get_item_discount_price(x[0]), games))
    return render_template("index.html", authorized=1, games_data=[games, games_discount_price],
                           user=get_user(request.cookies.get("user_id")), page=page,
                           GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)


@app.route("/<sort_mode>=<sorting_command>", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/<int:page>/<sort_mode>=<sorting_command>", methods=["GET", "POST"])
def index_with_order(page, sort_mode, sorting_command):
    if int(request.cookies.get("authorized", "0")):
        return redirect(f"/authorized/{sort_mode}={sorting_command}")
    games = sorting_games(page, sort_mode, sorting_command)
    games_discount_price = list(map(lambda x: get_item_discount_price(x[0]), games))
    return render_template("index.html", authorized=0, games_data=[games, games_discount_price], page=page,
                           GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)


@app.route("/authorized/<sort_mode>=<sorting_command>", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/authorized/<int:page>/<sort_mode>=<sorting_command>", methods=["GET", "POST"])
def authorized_user_index_with_order(page, sort_mode, sorting_command):
    games = sorting_games(page, sort_mode, sorting_command)
    games_discount_price = list(map(lambda x: get_item_discount_price(x[0]), games))
    return render_template("index.html", authorized=1, games_data=[games, games_discount_price],
                           user=get_user(request.cookies.get("user_id")), page=page,
                           GAME_CARDS_NUMBER_PER_PAGE=GAME_CARDS_NUMBER_PER_PAGE)


def sorting_games(page, sort_mode, sorting_command):
    games = get_games(page)
    if sort_mode == "order":
        if sorting_command == "price":
            games.sort(key=lambda x: get_item_discount_price(x[0])["mn_price"])
        elif sorting_command == "discount":
            games.sort(key=lambda x: max(get_item_discount_price(x[0])["discount_factor"].values()), reverse=True)
    elif sort_mode == "genre":
        games = list(filter(lambda x: genres_translate_eng_ru[sorting_command] in x[7], games))
    return games


def get_games(page):
    con = sqlite3.connect("db/games_resource.db")
    cur = con.cursor()
    try:
        if isinstance(page, int):
            items_amount = len(cur.execute(f"""SELECT * FROM content""").fetchall())
            games_cont = list(cur.execute(f"""SELECT * FROM content 
            WHERE content.id BETWEEN {(page - 1) * GAME_CARDS_NUMBER_PER_PAGE} AND 
            {min(items_amount, page * GAME_CARDS_NUMBER_PER_PAGE)}""").fetchall())
        else:
            raise ValueError()
        return games_cont
    except ValueError:
        logging.error("Invalid values")


def get_game_item(game_id):
    con = sqlite3.connect("db/games_resource.db")
    cur = con.cursor()
    return cur.execute(f"""SELECT * FROM content WHERE {game_id} == content.id""").fetchone()


def get_user(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(user_id)
    if user is None:
        logging.error(f"User with id {user_id} not found")
    return user


def get_item_discount_price(game_id):
    con = sqlite3.connect("db/games_resource.db")
    cur = con.cursor()
    results = cur.execute(f"""SELECT content.name, discounts_prices.discount_factor, discounts_prices.price 
    FROM content, discounts_prices WHERE {game_id} == discounts_prices.game_id""").fetchone()
    data = {"id": game_id, "name": results[0], "discount_factor": json.loads(results[1]),
            "prices": json.loads(results[2])}
    data["discount_price"] = dict(list(map(lambda x: (x[0], int(int(x[1]) * 1 - (data["discount_factor"][x[0]] / 100))),
                                           list(filter(lambda x: x[1] != -1, data["prices"].items())))))
    data["mn_price"] = min(data["discount_price"].values())
    return data


if __name__ == "__main__":
    db_session.global_init("db/data.db")
    app.run()
