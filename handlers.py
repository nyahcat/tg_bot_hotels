from loader import bot, logger
from models import db
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from rapidapi import *
from telegram_bot_calendar import DetailedTelegramCalendar, static
from user_class import User
from models import UserHistory
from datetime import datetime, date, timedelta


__all__ = ['sc_start', 'Union', 'history_save_time', 'show_history', 'clear_history', 'patch']


def history_save_time(message: Union) -> None:
    """
    Сохранение даты и времени ввода команды для БД
    :param message: Union - Объект сообщения пользователя;
    :return: None.
    """
    user = User.get_user(message.chat.id)
    user.timestamp = datetime.now().strftime('%d.%m.%Y -- %H:%M:%S')
    logger.info(f'{history_save_time.__name__} succeed')


def sc_start(message: Union) -> None:
    """
    Запуск сценария поиска.
    :param message: Union - объект сообщения пользователя;
    :return: None.
    """
    user = User.get_user(message.chat.id)
    if user.command and user.command_status is not False:
        user.command_status = False
        bot.send_message(message.chat.id, 'Напишите город, в котором провести поиск:\n'
                                          '(Например: Москва)')
        bot.register_next_step_handler(message, compare_cities)
    else:
        bot.send_message(message.chat.id, 'Обнаружен незавершенный сценарий поиска!')
        abort_scenario(message.chat.id)


def abort_scenario(user_id: str) -> None:
    """
    Сценарий отмены поиска
    :param user_id: str - ID юзера;
    :return: None.
    """
    logger.debug(f'user {user_id} started abort scenario')
    abort_keyboard = InlineKeyboardMarkup(row_width=2)
    yes_button = InlineKeyboardButton(text='Прервать',
                                      callback_data='sc_abort')
    no_button = InlineKeyboardButton(text='Продолжить сценарий',
                                     callback_data='sc_continue')
    abort_keyboard.add(yes_button, no_button)
    bot.send_message(chat_id=user_id,
                     text='Остановить выполнение текущего сценария?',
                     reply_markup=abort_keyboard)


@bot.callback_query_handler(func=lambda call: 'sc_' in call.data)
def abort_options(call: Union) -> None:
    """
    Обработчик нажатой кнопки в сценарии отмены поиска
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    logger.debug(f'abort options reached')
    logger.debug(f'calldata {call.data}')
    delete_button(call)

    if 'sc_abort' in call.data:
        User.del_user(call.message.chat.id)
        bot.send_message(text='Сценарий поиска остановлен. Введите новую команду для запуска сценария поиска\n'
                              'Введите /help для помощи',
                         chat_id=call.message.chat.id)
        logger.info(f'user {call.message.chat.id} aborted operation')
    elif 'sc_continue' in call.data:
        bot.send_message(text='Пожалуйста, следуйте инструкциям бота',
                         chat_id=call.message.chat.id)
        logger.debug(f'user {call.message.chat.id} continued operation')


def patch(user_id: str) -> None:
    """
    Заглушка для неверного/случайного ввода
    :param user_id: str - ID юзера;
    :return: None.
    """
    user = User.get_user(user_id)
    if user_id in User.users and user.command is not None:
        patch_keyboard = InlineKeyboardMarkup(row_width=1)
        button = InlineKeyboardButton(text='Прервать',
                                      callback_data='sc_abort')
        patch_keyboard.add(button)
        bot.send_message(chat_id=user_id,
                         text='Пожалуйста, не мешайте мне работать :с\n'
                              'Пользуйтесь кнопками и следуйте моим инструкциям.\n'
                              'Я могу прервать поиск, если желаете ',
                         reply_markup=patch_keyboard)
    else:
        bot.send_message(user_id, 'Не понял, что вы имели в виду...🤔\nВведите /help для помощи')


def delete_button(call: Union) -> None:
    """
    Удаление кнопки из сообщения после нажатия
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    bot.edit_message_reply_markup(message_id=call.message.id,
                                  chat_id=call.message.chat.id,
                                  reply_markup=None)


def compare_cities(message: Union) -> None:
    """
    Построение инлайн-клавиатуры с предложенными вариантами пунктов назначения по запросу пользователя.
    :param message: Union - объект сообщения пользователя;
    :return: None.
    """
    try:
        user = User.get_user(message.chat.id)
        user.cities = get_city(ask_message=message.text)
        logger.info(f'get_city returned {user.cities}')
        keyboard = InlineKeyboardMarkup(row_width=len(user.cities))
        for city_id, city_name in user.cities.items():
            callback_str: str = f'::{city_id}'
            if len(callback_str) < 64:  # размер callback_data кнопки должен быть 1-64 байт
                button = InlineKeyboardButton(text=city_name, callback_data=callback_str)
                keyboard.add(button)
            else:
                continue
        bot.send_message(chat_id=message.chat.id,
                         text='Вы ищете:',
                         reply_markup=keyboard)
    except Exception as er:
        logger.error(er)
        bot.send_message(message.chat.id, text='Что-то пошло не так... Попробуйте позже.')


@bot.callback_query_handler(func=lambda call: '::' in call.data)
def callback_city(call: Union) -> None:
    """
    Обработчик нажатия кнопки выбора города для поиска.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    user = User.get_user(call.message.chat.id)
    if call.message:
        user.city_id = re.findall(r'::(\d+)', call.data)[0]
        user.city_name = user.cities.get(user.city_id)
        logger.info(f'callback_city result: {user.city_id}, {user.city_name}')

        next_markup = InlineKeyboardMarkup(row_width=1)
        if user.command == '/bestdeal':
            next_markup.add(InlineKeyboardButton(text='Выбрать цены', callback_data='prices'))
        else:
            next_markup.add(InlineKeyboardButton(text='Выбрать даты', callback_data='date_in'))

        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.id,
                              text=f'Вы выбрали: {user.city_name}',
                              reply_markup=next_markup)


@bot.callback_query_handler(func=lambda call: 'prices' in call.data)
def ask_prices(call: Union) -> None:
    """
    Запрос диапазона цен у пользователя (для команды /bestdeal).
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    delete_button(call)
    user = User.get_user(call.message.chat.id)
    bot.send_message(chat_id=call.message.chat.id,
                     text=f'Введите диапазон желаемой цены в формате "min-max" (в {user.currency}):\n'
                          f'Например: 50-500')
    bot.register_next_step_handler(call.message, set_prices)


def set_prices(message: Union) -> None:
    """
    Установка диапазона цен за номер отелей и их сортировка (min -> max).
    :param message: Union - объект сообщения пользователя;
    :return: None.
    """
    user = User.get_user(message.chat.id)
    if '-' in message.text:
        price_range: List[str] = message.text.split('-')
        price_range.sort(key=lambda item: int(item.strip()))
        if len(price_range) == 2:
            min_price, max_price = price_range[0], price_range[1]
            if min_price.isdigit() and max_price.isdigit():
                next_markup = InlineKeyboardMarkup()
                next_markup.add(InlineKeyboardButton(text='Далее', callback_data='distances'))
                user.min_price, user.max_price = min_price, max_price
                bot.send_message(chat_id=message.chat.id,
                                 text=f'Установлен диапазон цен: {user.min_price}-{user.max_price} {user.currency}',
                                 reply_markup=next_markup)
                logger.success(f'set_prices result: min {user.min_price}, max {user.max_price}')
                return

    bot.send_message(message.chat.id, 'Неверный ввод. Введите корректный диапазон цен (Например: 50-500)')
    logger.warning('set_prices: wrong input')
    bot.register_next_step_handler(message, set_prices)


@bot.callback_query_handler(func=lambda call: 'distances' in call.data)
def ask_distance(call: Union) -> None:
    """
    Запрос максимального расстояния отелей от центра города от пользователя.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    delete_button(call)
    bot.send_message(chat_id=call.message.chat.id,
                     text=f'Введите радиус поиска в километрах от центра (не более 15):\n'
                          f'Например: 0.3 или 2 или 10.5')
    bot.register_next_step_handler(call.message, set_distance)


def set_distance(message: Union) -> None:
    """
    Установка расстояния отелей от центра города.
    :param message: Union - объект сообщения пользователя;
    :return: None
    """
    user = User.get_user(message.chat.id)
    text_msg = message.text
    if text_msg.isdigit():
        if ',' in text_msg:
            text_msg = text_msg.replace(',', '.')
        if 0 <= eval(text_msg) <= 15:
            user.distance = text_msg
            next_markup = InlineKeyboardMarkup()
            next_markup.add(InlineKeyboardButton(text='Далее', callback_data='date_in'))
            bot.send_message(chat_id=message.chat.id,
                             text=f'Установлен радиус поиска в {user.distance} км от центра города',
                             reply_markup=next_markup)
            logger.success(f'set_distance result: {user.distance}')
            return

    bot.send_message(message.chat.id, 'Неверный ввод. Введите корректный радиус в км, например: 0.3 или 2 или 10.5')
    logger.warning('set_distance: wrong input')
    bot.register_next_step_handler(message, set_distance)


@bot.callback_query_handler(func=lambda call: 'date_in' in call.data)
def show_calendar_in(call: Union) -> None:
    """
    Построение инлайн-календаря для даты приезда.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """

    # Форматирование календаря (исходной библиотеки telegram_bot_calendar)
    static.DAYS_OF_WEEK['ru'] = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    delete_button(call)
    calendar, step = DetailedTelegramCalendar(calendar_id=1,
                                              min_date=date.today(),
                                              locale='ru',
                                              max_date=date.today() + timedelta(days=180)).build()
    bot.send_message(chat_id=call.message.chat.id,
                     text=f'Выберите дату заезда:',
                     reply_markup=calendar)


@bot.callback_query_handler(func=lambda call: 'date_out' in call.data)
def show_calendar_out(call: Union) -> None:
    """"
    Построение инлайн-календаря для даты отъезда.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    delete_button(call)
    calendar, step = DetailedTelegramCalendar(calendar_id=2,
                                              min_date=date.today(),
                                              locale='ru',
                                              max_date=date.today() + timedelta(days=365)).build()
    bot.send_message(chat_id=call.message.chat.id,
                     text=f'Выберите дату отъезда:',
                     reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=1))
def calendar_in(call: Union) -> None:
    """
    Построение инлайн-календаря для даты приезда.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    result, key, step = DetailedTelegramCalendar(calendar_id=1,
                                                 min_date=date.today(),
                                                 locale='ru',
                                                 max_date=date.today() + timedelta(days=365)).process(call.data)
    if not result and key:
        bot.edit_message_text(text=f'Выберите дату приезда',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=key)
    elif result:
        user = User.get_user(call.message.chat.id)
        next_markup = InlineKeyboardMarkup()
        next_markup.add(InlineKeyboardButton(text='Выбрать дату отъезда', callback_data='date_out'))
        bot.edit_message_text(text=f'Вы выбрали {result}',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=next_markup)
        user.check_in = result


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=2))
def calendar_out(call: Union) -> None:
    """
    Построение инлайн-календаря для даты отъезда.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    result, key, step = DetailedTelegramCalendar(calendar_id=2,
                                                 min_date=date.today(),
                                                 locale='ru',
                                                 max_date=date.today() + timedelta(days=365)).process(call.data)
    if not result and key:
        bot.edit_message_text(text=f'Выберите дату отъезда',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=key)
    elif result:
        user = User.get_user(call.message.chat.id)
        next_markup = InlineKeyboardMarkup()
        next_markup.add(InlineKeyboardButton(text='Далее', callback_data='page_size'))
        bot.edit_message_text(text=f'Вы выбрали {result}',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=next_markup)
        user.check_out = result
        if dates_check(call.message.chat.id):
            user.days_delta = (user.check_out - user.check_in).days
            user.check_in = user.check_in.strftime('%Y-%m-%d')
            user.check_out = user.check_out.strftime('%Y-%m-%d')


def dates_check(user_id) -> bool:
    """
    Проверка последовательности выбранных дат, исправление в случае необходимости.
    :param user_id: str - user id;
    :return: bool - флаг валидности дат.
    """
    user = User.get_user(user_id)
    if user.check_in > user.check_out:
        user.check_in, user.check_out = user.check_out, user.check_in
        logger.info(f'dates swapped -> in: {user.check_in} out:{user.check_out}')
    return True


@bot.callback_query_handler(func=lambda call: 'page_size' in call.data)
def ask_page_size(call: Union) -> None:
    """
    Запрос количества отображаемых результатов поиска.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    delete_button(call)
    bot.send_message(chat_id=call.message.chat.id,
                     text='Сколько результатов вывести? (не более 10)')
    bot.register_next_step_handler(call.message, set_page_size)


def set_page_size(message: Union) -> None:
    """
    Установка количество отображаемых результатов поиска.
    :param message: Union - объект сообщения пользователя;
    :return: None.
    """
    if message.text.isdigit():
        if 1 <= int(message.text) <= 10:
            user = User.get_user(message.chat.id)
            next_markup = InlineKeyboardMarkup()
            next_markup.add(InlineKeyboardButton(text='Далее', callback_data='display_photo'))
            user.page_size = message.text.strip()
            bot.send_message(chat_id=message.chat.id,
                             text=f'Попробую найти {user.page_size}',
                             reply_markup=next_markup)
            logger.success(f'set_page_size result: {user.page_size}')
            return

    bot.send_message(message.chat.id, 'Неверный ввод. Введите число от 1 до 10 включительно')
    logger.warning('set_page_size: wrong input')
    bot.register_next_step_handler(message, set_page_size)


@bot.callback_query_handler(func=lambda call: 'display_photo' in call.data)
def display_photo(call: Union) -> None:
    """
    Построение клавиатуры вопросу о приложении фотографий к результатам поиска.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    delete_button(call)
    yes_no_markup = InlineKeyboardMarkup()
    yes_no_markup.add(
        InlineKeyboardButton(text='Да', callback_data='btn_yes'),
        InlineKeyboardButton(text='Нет', callback_data='create_request'))
    bot.send_message(chat_id=call.message.chat.id,
                     text='Прикрепить фото к результатам?',
                     reply_markup=yes_no_markup)


@bot.callback_query_handler(func=lambda call: 'btn_yes' in call.data)
def yes_callback(call: Union) -> None:
    """
    Обработчик нажатия кнопки "да" пользователем.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    delete_button(call)
    user = User.get_user(call.message.chat.id)
    user.display_photos = True
    logger.info(f'user {call.message.chat.id} display photos {user.display_photos}')
    ask_amount_photos(call.message)


def ask_amount_photos(message: Union) -> None:
    """
    Запрос количества отображаемых фотографий.
    :param message: Union - объект сообщения пользователя;
    :return: None.
    """
    bot.send_message(chat_id=message.chat.id,
                     text='Сколько фотографий вывести? (Не более 5)')
    bot.register_next_step_handler(message, set_amount_photos)


def set_amount_photos(message: Union) -> None:
    """
    Установка количества прилагаемых фото.
    :param message: Union - объект сообщения пользователя;
    :return: None.
    """
    if message.text.isdigit():
        if 1 <= int(message.text) <= 5:
            user = User.get_user(message.chat.id)
            next_markup = InlineKeyboardMarkup()
            next_markup.add(InlineKeyboardButton(text='Далее', callback_data='create_request'))
            user.amount_photos = int(message.text.strip())
            bot.send_message(chat_id=message.chat.id,
                             text=f'Покажу {user.amount_photos} фото (при наличии)',
                             reply_markup=next_markup)
            logger.success(f'set_amount_photos result: {user.amount_photos}')
            return

    bot.send_message(message.chat.id, 'Неверный ввод. Введите число от 1 до 5 включительно')
    logger.warning('set_amount_photos wrong input')
    bot.register_next_step_handler(message, set_amount_photos)


@bot.callback_query_handler(func=lambda call: call.data == 'create_request')
def create_request(call: Union) -> None:
    """
    Формирование параметров для отправки в параметры запроса к api.
    :param call: Union - объект нажатой кнопки;
    :return: None.
    """
    delete_button(call)
    user = User.get_user(call.message.chat.id)
    querystring: Dict[str] = {
        "destinationId": user.city_id,
        "pageNumber": "1",
        "pageSize": user.page_size,
        "checkIn": user.check_in,
        "checkOut": user.check_out,
        "adults1": "1",
        "sortOrder": user.sort_order,
        "locale": user.locale,
        "currency": user.currency
    }

    if user.command == '/bestdeal':
        querystring["landmarklds"] = user.landmarklds
        querystring["pageSize"] = "25"

    if None in querystring.values():
        logger.error(f'querystring has None value\n{querystring}')
    else:
        bot.send_message(chat_id=call.message.chat.id,
                         text='Параметры поиска заданы, выполняю...')
        logger.info(f'querystring\n{querystring}')
        try:
            request_data = get_hotel_data(querystring, user_id=call.message.chat.id)
            data_sender(request_data, call.message.chat.id)
        except Exception as er:
            logger.exception(er)
            bot.send_message(chat_id=call.message.chat.id,
                             text=f'Что-то пошло не так... Попробуйте позже.')


def data_sender(hotels_data, user_id: str) -> None:
    """
    Отправка сообщений с результатами поиска пользователю и их сохранение в БД.
    :param hotels_data: Optional[Iterator, List] - zip-итератор (или список), содержащий упорядоченные данные от api;
    :param user_id: str - user id;
    :return: None.
    """
    user = User.get_user(user_id)
    if not hotels_data:
        bot.send_message(chat_id=user_id,
                         text='Ничего не нашлось :с\nПопробуйте другие параметры поиска...')
        return

    if user.command == '/bestdeal' and user.display_photos:
        temp = list()
        for hotel in hotels_data:
            temp.append([*hotel[0], hotel[1]])
        hotels_data = temp

    for hotel in hotels_data:
        h_rating, h_name, h_address, h_distance, h_price_period, h_price_day, h_id = \
            hotel[0], hotel[1], hotel[2], hotel[3], hotel[4], hotel[5], hotel[6]

        hotel_message = f'⭐Рейтинг: {h_rating} \n' \
                        f'🏨Название отеля: {h_name}\n'\
                        f'🏙Адрес: {h_address}\n'\
                        f'🛺Расстояние до центра города: {h_distance}\n'\
                        f'💰Цена за {user.days_delta} дней: {h_price_period} {user.currency}\n' \
                        f'💵Цена за день: {h_price_day} {user.currency}\n' \
                        f'🌏[Ссылка на отель](https://ru.hotels.com/ho{h_id}/' \
                        f'?q-check-in={user.check_in}&q-check-out={user.check_out}&q-room-0-adults=1)'
        logger.debug(f'hotel_message == {hotel_message}')
        bot.send_message(chat_id=user_id, text=hotel_message, disable_web_page_preview=True, parse_mode='Markdown')
        if user.display_photos:
            media_group = list()
            list_of_urls = hotel[7]
            for url in list_of_urls:
                media_group.append(InputMediaPhoto(media=url))
            bot.send_media_group(chat_id=user_id, media=media_group)
    logger.success(f'data send to {user_id}')

    """ Сохраняем историю запроса в БД """
    with db:
        UserHistory.create(user_id=user_id,
                           timestamp=user.timestamp,
                           command=user.command,
                           h_names=user.db_hotels,
                           h_urls=user.db_urls)
        logger.info(f'user {user_id} data saved')

    """ Удаляем юзера из словаря текущих запросов """
    User.del_user(user_id)
    logger.info(f'user {user_id} removed from current users')


@logger.catch
def show_history(message: Union, user_id: str) -> None:
    """
    Вывод истории поиска в виде сообщений в чат с пользователем.
    :param message: Union - сообщение;
    :param user_id: str - ID юзера;
    :return: None.
    """
    history_message = str()
    with db:
        if UserHistory.select().where(UserHistory.user_id == user_id):

            # При каждом обращении к history очистка истории
            for item in UserHistory.select().where(UserHistory.user_id == user_id):
                time_strp = datetime.strptime(item.timestamp, '%d.%m.%Y -- %H:%M:%S')
                delta = (datetime.now() - time_strp).days
                # logger.info(f'time delta in db = {delta}')
                if delta > 14:
                    UserHistory.delete_instance(item)
                    logger.info(f'old user data {user_id} removed from db')
                    continue

                history_message += f'Команда поиска: {item.command} \nВремя поиска: {item.timestamp}\n' \
                                   f'История поиска:\n{"="*15}\n'
            hotels_zip = zip(eval(item.h_names), eval(item.h_urls))
            for hotel in hotels_zip:
                history_message += f'[{hotel[0]}]({hotel[1]})\n'

            logger.success(f'history send to {user_id}')

        else:
            history_message += 'Пока ничего нет...'

    bot.send_message(chat_id=message.chat.id,
                     text=history_message,
                     disable_web_page_preview=True,
                     parse_mode='Markdown')


def clear_history(user_id: str) -> None:
    """
    Очистка истории
    :param user_id: str - id юзера
    :return: None.
    """
    with db:
        if UserHistory.select().where(UserHistory.user_id == user_id):
            for item in UserHistory.select().where(UserHistory.user_id == user_id):
                UserHistory.delete_instance(item)
            status = 'История очищена!'
            logger.success(f'history of {user_id} cleared')

        else:
            status = 'Нечего удалять :с'

        bot.send_message(chat_id=user_id,
                         text=status)
