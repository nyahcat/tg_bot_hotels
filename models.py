from peewee import Model, CharField, SqliteDatabase


db = SqliteDatabase('history.db')


class UserHistory(Model):
    """
    Класс модели БД для ORM peewee
    """
    user_id = CharField()
    timestamp = CharField()
    command = CharField()
    h_names = CharField()
    h_urls = CharField()

    class Meta:
        database = db
        db_table = 'history'
