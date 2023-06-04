from loader import logger


class User:
    """
     Класс пользователя бота.
        Вспомогательный класс для удобства работы с ботом и БД
        Инстансы создаются для каждого пользователя отдельно
    """

    users = dict()

    def __init__(self, user_id) -> None:
        """
        Инициализация объекта с уникальным ID из чата
        :param user_id: str - user id
        """
        """ Команда поиска """
        self.command = None
        """ Общие параметры querystring """
        self.city_id = None
        self.city_name = None
        self.cities = None
        self.page_size = None
        self.check_in = None
        self.check_out = None
        self.days_delta: int = 0
        self.sort_order = None

        """ Вывод фото и их количество (если True) """
        self.display_photos: bool = False
        self.amount_photos: int = 0

        """ Для команды /bestdeal """
        self.min_price = None
        self.max_price = None
        self.distance = None
        self.landmarklds: str = "Центр города"

        """ Константы """
        self.locale: str = "ru_RU"
        self.currency: str = "RUB"

        """ Для ДБ """
        self.timestamp = None
        self.db_hotels = None
        self.db_urls = None

        """ Флаг возможности отправлять сообщение """
        self.command_status = True

        User.add_user(user_id, self)

    @staticmethod
    @logger.catch
    def get_user(user_id: str):
        """
        Основной метод обращения к классу
        :param user_id: str - user id
        :return: экземпляр User
        """
        if User.users.get(user_id) is None:
            new_user = User(user_id)
            return new_user
        return User.users.get(user_id)

    @classmethod
    def add_user(cls, user_id: str, user) -> None:
        """
        Добавляет нового пользователя в словарь users
        :param user_id: str - user id
        :param user: экземпляр User
        :return: None
        """
        cls.users[user_id] = user

    @classmethod
    def del_user(cls, user_id: str) -> None:
        """
        Удаляет пользователя из словаря users
        :param user_id: str - user id
        :return: None
        """
        cls.users.pop(user_id)

    def print_attr(self) -> None:
        """
        Отладочная функция. Выводит в консоль все параметры объекта.
        :return: None
        """
        logger.debug(
            f'self.command = {self.command}\n'
            f'self.city_id = {self.city_id}\n'
            f'self.city_name = {self.city_name}\n'
            f'self.page_size = {self.page_size}\n'
            f'self.check_in = {self.check_in}\n'
            f'self.check_out = {self.check_out}\n'
            f'self.days_delta = {self.days_delta}\n'
            f'self.sort_order = {self.sort_order}\n'
            f'self.display_photos = {self.display_photos}\n'
            f'self.amount_photos = {self.amount_photos}\n'
            f'self.min_price = {self.min_price}\n'
            f'self.max_price = {self.max_price}\n'
            f'self.distance = {self.distance}\n'
            f'self.locale = {self.locale}\n'
            f'self.currency = {self.currency}\n'
            f'self.timestamp = {self.timestamp}\n'
            f'self.db_hotels = {self.db_hotels}\n'
            f'self.db_urls = {self.db_urls}'
            )
