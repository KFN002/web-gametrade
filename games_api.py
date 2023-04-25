import os.path
import pathlib

import flask
from flask import jsonify, request
from data import db_session
from data.work_with_db import Game

blueprint = flask.Blueprint(
    'game_api',
    __name__,
    template_folder='templates'
)


@blueprint.route('/api/delete_game', methods=['DELETE', 'GET'])   # api удаления игры по id
def delete_game():     # http://127.0.0.1:5000/api/delete_game?password=29AF622358&id=43
    if request.args.get('password') == '29AF622358':
        db_sess = db_session.create_session()
        game = db_sess.query(Game).filter(Game.id == int(request.args.get('id'))).first()  # получние игры по id
        if not game:
            return jsonify({'ERROR': 'No such game found!'})
        db_sess.delete(game)   # удаление игры
        db_sess.commit()
        return jsonify({'SUCCESS': 'Game has been deleted from the website!'})
    return jsonify({'ERROR': 'Wrong or invalid password'})


@blueprint.route('/api/reset_game', methods=['GET', 'POST'])  # api восстановления игры после окончания ключей
def reset_game():  # http://127.0.0.1:5000/api/reset_game?password=29AF622358&name=RD2&price=99&image=ac7.jpg&info=wef
    if request.args.get('password') == '29AF622358':  # проверка пароля
        db_sess = db_session.create_session()
        description = request.args.get('info')
        while '_' in description:
            description.replace('_', ' ')
        picture = f"/static/img/{request.args.get('image').strip()}"   # путь до фото
        if os.path.exists(picture[1:]):   # создание игры
            game = Game(
                name=request.args.get('name'),
                price=int(request.args.get('price').strip()),
                picture=picture,
                description=description
            )
            db_sess.add(game)
            db_sess.commit()
        else:
            return jsonify({'ERROR': 'No photo error'})
    else:
        return jsonify({'ERROR': 'Wrong or invalid password'})
    return jsonify({'OK': 'Game added'})
