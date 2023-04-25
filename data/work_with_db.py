import sqlalchemy
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from .db_session import SqlAlchemyBase
import datetime


'''
scope = ['https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
name = 'GameTrade: keys'
sheet = client.create(name)
sheet.share('fedotovkirill4000@gmail.com', perm_type='user', role='writer')
'''


class Order(SqlAlchemyBase, UserMixin, SerializerMixin):    # заказ см. пояснительную записку
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    time_transaction = Column(sqlalchemy.DateTime,
                              default=datetime.datetime.now)
    total = Column(Integer)
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship('ShopClient', back_populates='orders')


class ShopClient(SqlAlchemyBase, UserMixin, SerializerMixin):   # клиент магазина см. пояснительную записку
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    hashed_password = Column(String)
    orders = relationship('Order', back_populates='client')

    def set_password(self, password):   # смена пароля
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):  # проверка пароля
        return check_password_hash(self.hashed_password, password)


class Game(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'games'    # класс игра см. пояснительную записку
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Integer)
    picture = Column(String)
    description = Column(String)

    def get_key(self):   # получение и удаление ключа из google таблицы при отправке заказа
        scope = ['https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name("mysite/data/credentials.json", scope)
        client = gspread.authorize(credentials)
        sheet = client.open('GameTrade: keys').sheet1
        data = sheet.get_all_values()
        keys = data[sheet.find(str(self.id)).row - 1][1:]
        if keys[0] != '':
            sheet.update_cell(sheet.find(str(self.id)).row, int(sheet.find(keys[-1]).col), '')
            return keys[-1]
        else:
            print('No current keys')
            return None

    def get_data(self):  # получение информации из google-таблицы для проверки наличия ключа
        scope = ['https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name("mysite/data/credentials.json", scope)
        client = gspread.authorize(credentials)
        sheet = client.open('GameTrade: keys').sheet1
        data = sheet.get_all_values()
        return data
