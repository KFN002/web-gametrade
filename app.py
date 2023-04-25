from flask import Flask, render_template, request, redirect, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data.client_forms import *
import games_api
from data import db_session
import json
from data.work_with_db import ShopClient, Order, Game
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from yoomoney import Quickpay, Client
import datetime
from passwords import *

app = Flask(__name__)
app.config['SECRET_KEY'] = app_password   # секретный ключ из файла passwords
app.register_blueprint(games_api.blueprint)   # подлючение api
login_manager = LoginManager()   # подключение flask_login
login_manager.init_app(app)
db_session.global_init("mysite/db/shop-market.db")   # и# форма логинанициализация бд


@login_manager.user_loader
def load_user(user_id):    # подгрука пользователя из бд
    db_sess = db_session.create_session()
    return db_sess.query(ShopClient).get(user_id)


@app.route('/')
def main_page():    # главная страница
    return render_template('index.html', logged=current_user.is_authenticated)


@app.route('/login', methods=["POST", "GET"])
def login_page():   # страница входа
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(ShopClient).filter(ShopClient.email == form.email.data).first()
        if user and user.check_password(form.password.data):  # получние пароля по почте и сравнение
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login2.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login2.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()   # выход из аккаунта
    return redirect("/")


def to_list(data):   # преобразование из cookie в список: раньше был ast и код был намного лучше, но pythonanywhere
    # он не понравился
    return [i for i in map(lambda x: x.replace('"', '').replace('"', '').replace("'", '').replace("'", ''),
                           data[1:-1].split(', '))]


@app.route('/register', methods=["POST", "GET"])
def register_page():  # страница регистрации
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register2.html',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        # подключение бд и проверка наличия почты там
        if db_sess.query(ShopClient).filter(ShopClient.email == form.email.data).first():
            return render_template('register2.html',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = ShopClient(
            name=form.name.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)   # добавление в бд
        db_sess.commit()
        return redirect('/login')
    return render_template('register2.html', form=form)


@app.route('/forgot-password', methods=["POST", "GET"])
def forgotten_password_page():   # восстановление пароля
    if request.method == 'POST':
        login = gmail
        password = gmail_key   # отправка письма через сервера google
        server = smtplib.SMTP('smtp.gmail.com', 25)
        server.starttls()
        server.login(login, password)
        msg = MIMEMultipart()
        addr_to = request.form.get('email')
        msg['From'] = login
        msg['To'] = addr_to
        msg['Subject'] = 'Восстановление пароля'
        db_sess = db_session.create_session()
        all_emails = map(lambda x: x.email, db_sess.query(ShopClient).all())
        if addr_to in all_emails:
            # отправка идет на почту, указанную в форме: внутри письма ссылка для создания нового пароля
            client = db_sess.query(ShopClient).filter(ShopClient.email == addr_to).first()
            body = f"{client.name.capitalize()}, вот ваша ссылка для восстановления пароля:" \
                   f"http://gametrade.pythonanywhere.com/reset_password?email={addr_to}&id={client.hashed_password}"
            msg.attach(MIMEText(body, 'plain'))
            server.send_message(msg)
            server.quit()  # письмо отправлено
            return redirect('/')  # есть letter.html но мне он показался не нужным
    return render_template('forgot-password.html')


@app.route('/reset_password', methods=["POST", "GET"])
def reset_password():  # страница создания нового пароля
    form = ResetPasswordForm()  # test http://127.0.0.1:5000/reset_password?email=fedotovk24@sch57.ru&id=1
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('reset_password.html',
                                   form=form,
                                   message="Пароли не совпадают")
        else:
            print('Passwords are equal')
            client = request.args.get('email')
            url_client_id = request.args.get('id')   # сравнение параметров переданных в запросе с бд
            db_sess = db_session.create_session()
            if str(url_client_id) == \
                    str(db_sess.query(ShopClient.hashed_password).filter(ShopClient.email == client).first()[0]):
                print('DB client exists')
                client_account = db_sess.query(ShopClient).filter(ShopClient.email == client).first()
                client_account.set_password(form.password.data)
                db_sess.commit()    # смена пароля пользователя
                return redirect('/login')
    return render_template('reset_password.html', form=form)


@app.route('/games', methods=["GET", "POST"])
def show_games():  # каталог
    db_sess = db_session.create_session()
    # начало работы с фильтрами и сортировкой
    data = db_sess.query(Game).order_by(Game.price).all()
    selected_sort = 'poor'
    finder_value = ''
    resp = make_response(render_template('games.html', logged=current_user.is_authenticated, data=data,
                                         selected_sort=selected_sort, finder_value=finder_value))
    if request.method == 'POST':
        name = request.form.get('need')
        if request.form.get('btn_finder') or name:   # работа фильтра  по названию
            data_find = []
            for product in data:
                if name.lower() in product.name.lower():
                    data_find.append(product)
            data = data_find
            finder_value = name
        if request.form.get('sorter') == 'rich':   # работа сортировки
            data = data[::-1]
            selected_sort = 'rich'
        else:
            data = data
            selected_sort = 'poor'
        resp = make_response(render_template('games.html', logged=current_user.is_authenticated, data=data,
                                             selected_sort=selected_sort, finder_value=finder_value))
        if request.form.get('btn'):   # добавление игры в корзину -> cookie
            game = db_sess.query(Game).filter(Game.id == int(request.form.get('btn'))).first()
            if request.cookies.get('cart'):
                cookie_pre_payload = [str(game.id)] + to_list(request.cookies.get('cart'))
            else:
                cookie_pre_payload = [str(game.id)]
            cookie_payload = []   # тк храним список, то я использовал json.dump
            [cookie_payload.append(x) for x in cookie_pre_payload if x not in cookie_payload]
            resp.set_cookie('cart', json.dumps(cookie_payload), max_age=60 * 60 * 24 * 90)
    return resp


@app.route('/profile', methods=["GET", "POST"])
@login_required
def show_profile():  # страница истории заказов
    db_sess = db_session.create_session()
    orders = db_sess.query(Order).all()
    client_orders = []
    for order in orders:   # подгрузка заказов и фильрация по внешнему ключу
        if int(order.client_id) == int(current_user.id):
            client_orders.append(order)
    return render_template('profile.html', orders=client_orders)


@app.route('/cart', methods=["GET", "POST"])
def show_cart():   # корзина
    db_sess = db_session.create_session()
    games = []
    total = 0
    try:
        if request.cookies.get('cart') != '[]' and request.cookies.get('cart'):
            game_ids = filter(lambda x: x != '', to_list(request.cookies.get('cart')))
            for c_id in game_ids:   # работа с cookie: с ast все было намного проще
                game_found = db_sess.query(Game).filter(Game.id == int(c_id)).first()
                games.append(game_found)
                total += int(game_found.price)
            data = games[0].get_data()
            for game in games:   # проверка наличия игры в google-таблице
                if not data[game.id - 1][1]:
                    games.remove(game)
                    total -= int(game.price)
                    resp = make_response(
                        render_template('cart.html', logged=current_user.is_authenticated, games=games, total=total))
                    cookie_payload = to_list(request.cookies.get('cart'))
                    cookie_payload.remove(str(game.id))   # удаление из данных, если игры нет в наличии
                    resp.set_cookie('cart', json.dumps(cookie_payload), max_age=60 * 60 * 24 * 90)
    except Exception:
        pass
    resp = make_response(render_template('cart.html', logged=current_user.is_authenticated, games=games, total=total))
    if request.method == 'POST':
        if not request.form.get('pay_btn'):   # rediect на оплату
            game = db_sess.query(Game).filter(Game.id == int(request.form.get('btn'))).first()
            cookie_payload = to_list(request.cookies.get('cart'))
            if str(game.id) in cookie_payload:
                cookie_payload.remove(str(game.id))
                games.remove(game)
                total -= int(game.price)    # обработка удаления игры из корзины кнопкой
            resp = make_response(
                render_template('cart.html', logged=current_user.is_authenticated, games=games, total=total))
            resp.set_cookie('total', str(total), max_age=60 * 60 * 24 * 90)
            resp.set_cookie('cart', json.dumps(cookie_payload), max_age=60 * 60 * 24 * 90)
        elif request.form.get('pay_btn') and total != 0:
            return redirect(f'/pay?total={total}')
    return resp


@app.route('/recieve_payment', methods=["GET", "POST"])
def get_payment():   # получение оплаты, выдача товара
    token = shop_token
    client = Client(token)
    if current_user.is_authenticated:
        label_eq = current_user.get_id()
    else:
        label_eq = 0
    history = client.operation_history(label=str(label_eq))
    # проверка статуса операции по истории переводов через label
    if len(history.operations) > 0 and history.operations[-1].operation.status == 'success':
        total = request.cookies.get('total')
        db_sess = db_session.create_session()
        game_ids = filter(lambda x: x != '', to_list(request.cookies.get('cart')))
        keys = []
        for game_id in game_ids:
            keys.append(db_sess.query(Game).filter(Game.id == int(game_id)).first().get_key())
        keys = ' '.join(keys)
        if current_user.is_authenticated:
            order = Order(
                time_transaction=datetime.datetime.now(),
                total=int(total),
                client_id=int(current_user.get_id())
            )
            db_sess.add(order)
            db_sess.commit()
            login = gmail   # отправка письма с ключами
            password = gmail_key
            server = smtplib.SMTP('smtp.gmail.com', 25)
            server.starttls()
            server.login(login, password)
            msg = MIMEMultipart()
            client = db_sess.query(ShopClient).filter(ShopClient.id == int(current_user.get_id())).first()
            msg['From'] = login
            msg['To'] = client.email
            msg['Subject'] = 'Покупка GameTrade'
            body = f"{client.name.capitalize()}, вот ваши ключи от игр: {keys}"
            msg.attach(MIMEText(body, 'plain'))
            server.send_message(msg)
            server.quit()
            resp = make_response(redirect('/'))
            resp.set_cookie('total', str(0), max_age=60 * 60 * 24 * 90)
            resp.set_cookie('cart', json.dumps([]), max_age=60 * 60 * 24 * 90)
            return resp
        else:
            # если нет акка, ключи покажут так
            return f'Вот ваши ключи от игр: {keys}.'
    return redirect('/')


@app.route('/pay', methods=["GET", "POST"])
def uoo_money():  # создание ссылки оплаты
    if request.cookies.get('cart') != '[]':
        total = request.args.get('total')
        if current_user.is_authenticated:
            label = current_user.get_id()
        else:
            label = 0
        quickpay = Quickpay(
            receiver="4100118177295897",
            quickpay_form="shop",
            targets="На поддержку сервиса",
            paymentType="SB",
            sum=int(total),
            label=str(label),
        )
        pay_link = quickpay.base_url
        return render_template('pay.html', link=pay_link)
    return redirect('/games')


@app.errorhandler(404)  # обработка 404
def handle_error404(error):
    return render_template('404.html', logged=current_user.is_authenticated)


def main():
    db_session.global_init("db/market-shop.db")
    app.run()


if __name__ == '__main__':
    main()
