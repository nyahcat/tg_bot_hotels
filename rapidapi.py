from loader import headers, city_finder_url, hotels_finder_url, photos_finder_url, logger
from user_class import User
import requests
from requests.exceptions import ConnectTimeout
import re
from typing import Dict, Union, List, Any, Optional, Iterator, Tuple
import random


__all__ = ["re", "Tuple", "Dict", "List", "Optional", "Any", "Union", "Iterator", "get_city", "get_hotel_data"]


def request_to_api(url: str, r_headers: Dict[str, str], querystring: Dict[str, str]) -> str:
    """
    Запрос к rapidapi с установленными параметрами
    :param url: str - url запроса
    :param r_headers: Dict[str] - заголовки
    :param querystring: Dict[str] - параметры запроса
    :return: str - текст ответа
    """
    try:
        response = requests.get(url=url, headers=r_headers, params=querystring, timeout=15)
        if response.status_code == requests.codes.ok:
            logger.success(f'response {url} OK ')
            return response.text
    except ConnectTimeout as er:
        logger.exception(er)
        return str(er)
    except Exception as exc:
        logger.exception(exc)
        return str(exc)


@logger.catch
def get_city(ask_message: str) -> Union[str, Dict[str, str], None]:
    """
    Поиск по ответу с помощью RegExp необходимых значений (имя города, ID города)
    :param ask_message: str - текст сообщения пользователя
    :return: Union[str, Dict[str, str], None] - словарь с городами и их ID
    """
    logger.info(f'user message: {ask_message}')
    try:
        response: str = request_to_api(url=city_finder_url, r_headers=headers,
                                       querystring={"query": ask_message, "locale": "ru_RU", "currency": "RUB"})
    except ConnectTimeout as er:
        logger.exception(er)
        return str(er)
    except Exception as exc:
        logger.exception(exc)
        return str(exc)

    suggest_name: List[List[str]] = re.findall(r'"(CITY)".*?"name":"(.*?)"', response)
    suggest_id: List[List[str]] = re.findall(r'"destinationId":"(\d*?)".*?"(CITY)"', response)
    re_res = zip(suggest_name, suggest_id)
    result = dict()
    for city_name, location_id in re_res:
        result[location_id[0]] = city_name[1]
    if result:
        return result
    else:
        return None


@logger.catch
def get_hotel_data(querystring: Dict[str, str], user_id: str) -> Union[Iterator, str, None]:
    """
    Поиск по ответу с помощью RegExp необходимых данных о результатах поиска (название, адрес,
    расстояние до центра, цена за период, цена за день, ID отеля и url-ы фото (если выбраны пользователем).
    :param querystring: Dict[str, str] - параметры запроса;
    :param user_id: str - user id;
    :return: Iterator - zip-объект с упорядоченными данными результатов поиска.
    """
    user = User.get_user(user_id=user_id)
    try:
        response = request_to_api(url=hotels_finder_url, r_headers=headers, querystring=querystring)
        if response:
            logger.info(f'response from api:\n{response}')
    except ConnectTimeout as er:
        logger.exception(er)
        return str(er)

    h_ratings: List[str] = re.findall(r'starRating":(\d\.\d)', response)
    h_names: List[str] = re.findall(r'name":"(.*?)"', response)
    h_addresses: List[str] = re.findall(r'streetAddress":"(.*?)"', response)
    h_distances: List[str] = re.findall(r'Центр.*?","distance":"(\d+,*\d*.+?)"', response)
    h_prices_period: List[str] = re.findall(r'exactCurrent":(\d+\.*\d*)', response)
    h_prices_day: List[str] = [f'{float(price)/user.days_delta:.2f}' for price in h_prices_period]
    h_id_list: List[str] = re.findall(r'id":(\d+),"name"', response)

    logger.info('re.findall main data OK')
    pre_result = zip(
            h_ratings, h_names, h_addresses, h_distances,
            h_prices_period, h_prices_day, h_id_list
        )
    data_sorted = None
    if user.command == '/bestdeal':
        # [hotel_1[h_rating, h_name, h_address, h_distance, h_price_period, h_price_day, h_id], hotel_2[..., ...], ...]
        data_sorted = hotel_data_analysis(pre_result, user_id)
        h_id_list: List[str] = [hotel[6] for hotel in data_sorted]
        logger.debug(f'data_sorted is ready\n{data_sorted}')

        if not data_sorted:
            return None

    if user.display_photos:
        h_photos_list: List[List[str]] = get_photos_urls(h_id_list, user_id)

        if user.command == '/bestdeal':
            result = zip(data_sorted, h_photos_list)    # ( [data, data, ...], [photo, photo] ), ...
        else:
            result = zip(
                h_ratings, h_names, h_addresses, h_distances,
                h_prices_period, h_prices_day, h_id_list, h_photos_list
            )
    else:
        if user.command == '/bestdeal':
            result = data_sorted
        else:
            result = zip(
                h_ratings, h_names, h_addresses, h_distances,
                h_prices_period, h_prices_day, h_id_list
            )

    user.db_hotels = str(h_names)
    user.db_urls = str([f'https://ru.hotels.com/ho{h_id}' for h_id in h_id_list])
    if result:
        logger.success('result-object creation success')

    return result


@logger.catch
def get_photos_urls(id_list: List[str], user_id) -> Union[List[List[str]], str]:
    """
    Поиск по ответу с помощью RegExp необходимых url, их преобразование.
    :param id_list: List[str] - список id отелей;
    :param user_id: str - user id;
    :return: Union[List[List[str]], str] - список списков с url-ами фото.
    """
    user = User.get_user(user_id=user_id)
    whole_urls_list = list()
    for i_id in id_list:
        try:
            response = request_to_api(url=photos_finder_url,
                                      r_headers=headers,
                                      querystring={"id": f"{i_id}"})
        except ConnectTimeout as er:
            logger.exception(er)
            return str(er)

        url_iter = re.finditer(r'(https://.*?)_', response)
        hotel_photos_urls = list()
        for _ in range(user.amount_photos):  # Кол-во фотографий, выбрал пользователь

            if hotel_photos_urls:   # Пропуск первой итерации (первое фото - всегда первое с сайта)
                for _ in range(random.randint(1, 5)):
                    next(url_iter)
            photo_url = '{url}z.jpg'.format(url=next(url_iter).group())
            hotel_photos_urls.append(photo_url)
        whole_urls_list.append(hotel_photos_urls)

    if not whole_urls_list:
        logger.error("hotel's photos list is empty")
    elif len(whole_urls_list) == len(id_list):
        logger.success("hotels' photos OK")
    else:
        logger.warning('several photos are missing')
    return whole_urls_list  # [ hotel_1 [photo_1, photo_2], hotel_2 [photo_1, photo_2], ... ]


def hotel_data_analysis(raw_data: Iterator, user_id: str):
    """
    Анализ данных отелей для команды /bestdeal. Отсеивание неподходящих результатов.
    :param raw_data: Iterator - zip-объект с несортированными данными;
    :param user_id: str - user id;
    :return: processed_data: List[List] - список из списков с "правильными" данными.
    """
    user = User.get_user(user_id)
    processed_data = list()
    for hotel in raw_data:
        """ Если в списке уже необходимое количество результатов - выход из цикла """
        if len(processed_data) == eval(user.page_size):
            break

        h_rating, h_name, h_address, h_distance, h_price_period, h_price_day, h_id = \
            hotel[0], hotel[1], hotel[2], hotel[3], hotel[4], hotel[5], hotel[6]

        # logger.debug(f'debug prices {user.min_price} < {h_price_day} < {user.max_price}')

        """ Сравнение значений с параметрами, заданными пользователем """
        normalized_distance = h_distance[0:4].strip()

        if (normalized_distance < user.distance) \
                and (float(user.min_price) < float(h_price_day) < float(user.max_price)):

            processed_data.append([hotel[0], hotel[1], hotel[2], hotel[3], hotel[4], hotel[5], hotel[6]])
            logger.success(f'{hotel[1]} added to processed data')
        else:
            logger.debug(f'{hotel[1]} excluded')
            continue
    # [ hotel_1 [h_rating, h_name, h_address, h_distance, h_price_period, h_price_day, h_id], hotel_2 [..., ...], ...]
    return processed_data
