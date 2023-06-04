from loader import bot, app, logger
from handlers import sc_start, Union, history_save_time, show_history, clear_history, patch
from user_class import User


@bot.message_handler(commands=['start'])
def start(message: Union) -> None:
    """ Стартовая команда бота. Выводит приветствие в чат """
    User.get_user(message.chat.id)
    bot.send_message(message.chat.id, f'Привет {message.chat.first_name}!\n'
                                      f'Я помогу с поиском отеля! Можете мне довериться, я в этом шарю!\n'
                                      f'Чтобы начать, введите любую из команд ниже:\n'
                                      f'/lowprice - Вывести топ самых дешёвых отелей в городе;\n'
                                      f'/highprice - Вывести топ самых дорогих отелей в городе;\n'
                                      f'/bestdeal - Вывести топ отелей, наиболее подходящих по цене и расположению;\n'
                                      f'/history - Показать историю поиска')


@bot.message_handler(commands=['help'])
def help_msg(message: Union) -> None:
    """ Вспомогательная команда бота. Идентична команде /start """
    User.get_user(message.chat.id)
    bot.send_message(message.chat.id, f'Я бот-поисковик отелей!\n '
                                      f'Просто введи любую из команд ниже и следуй инструкциям:\n'
                                      f'/lowprice - Вывести топ самых дешёвых отелей в городе\n'
                                      f'/highprice - Вывести топ самых дорогих отелей в городе\n'
                                      f'/bestdeal - Вывести топ отелей, наиболее подходящих по цене и расположению;\n'
                                      f'/history - Показать историю поиска')


@bot.message_handler(commands=['lowprice'])
def lowprice(message: Union) -> None:
    """ Запускает сценарий вывода в чат с пользователем результатов поиска отелей в выбранной им локации
        и записывает команду в аттрибут экземпляра user (user.command).
        Пользователь может управлять датами приезда / отъезда, количеством отображаемых результатов, наличием
        и количеством фотографий к ним

        Сортировка результатов: по возрастанию цены (user.sort_order) присваивается по умолчанию """
    user = User.get_user(message.chat.id)
    user.command, user.sort_order = message.text, "PRICE"
    history_save_time(message)
    sc_start(message)


@bot.message_handler(commands=['highprice'])
def highprice(message: Union) -> None:
    """ То же, что и /lowprice, но с другой сортировкой

        Сортировка результатов: по убыванию цены (user.sort_order) присваивается по умолчанию """
    user = User.get_user(message.chat.id)
    user.command, user.sort_order = message.text, "PRICE_HIGHEST_FIRST"
    history_save_time(message)
    sc_start(message)


@bot.message_handler(commands=['bestdeal'])
def bestdeal(message: Union) -> None:
    """ То же, что и /lowprice, но с возможностью выбора диапазона цен и радиуса поиска

        Сортировка результатов: по расстоянию от центра (user.sort_order) присваивается по умолчанию """
    user = User.get_user(message.chat.id)
    user.command, user.sort_order = message.text, 'DISTANCE_FROM_LANDMARK'
    history_save_time(message)
    sc_start(message)


@bot.message_handler(commands=['history'])
def history(message: Union) -> None:
    """ Заглушка для команды /history """
    user_id = message.chat.id
    show_history(message, user_id)


@bot.message_handler(commands=['clearhistory'])
def clearhistory(message: Union) -> None:
    """ Очистка истории пользователя """
    user_id = message.chat.id
    clear_history(user_id)


@bot.message_handler(content_types=['text'])
def patch_message(message: Union) -> None:
    """ Заглушка для случайного/неверного ввода """
    user_id = message.chat.id
    patch(user_id)


def start_bot() -> None:
    """ Автоматически перезапускает бота в случае падения с ошибкой """
    while True:
        try:
            app.run()
            # bot.remove_webhook()
            # bot.infinity_polling()
        except Exception as er:
            logger.error(er)
            continue


if __name__ == '__main__':
    start_bot()
