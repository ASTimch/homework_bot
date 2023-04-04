import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import messages
from exceptions import (
    APIEndpointAccessError,
    APIResponseWrongFormat,
    BotSendMessageError,
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

RESPONSE_DATE = "current_date"
RESPONSE_HOMEWORKS = "homeworks"
HOMEWORK_NAME = "homework_name"
HOMEWORK_STATUS = "status"


def check_tokens():
    """Проверка наличия необходимых переменных окружения."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="проверки наличия переменных окружения check_tokens"
        )
    )
    TOKENS = {
        "PRACTICUM_TOKEN": PRACTICUM_TOKEN,
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }
    missed_tokens = [k for k, v in TOKENS.items() if v is None]
    if missed_tokens:
        message_text = messages.LOG_TOKENS_NOT_FOUND.format(
            tokens=", ".join(missed_tokens)
        )
        logging.critical(message_text)
        raise ValueError(message_text)


def send_message(bot, message):
    """Отправка сообщения message от имени бота bot."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="отправки сообщения send_message"
        )
    )
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        message_text = messages.LOG_MESSAGE_SENT_ERROR.format(
            error=error, message=message
        )
        logging.error(message_text)
        raise BotSendMessageError(message_text)

    else:
        logging.debug(messages.LOG_MESSAGE_SENT.format(message=message))


def get_api_answer(timestamp):
    """API запрос статуса домашних работ, начиная с даты timestamp."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="get_api_answer() API запрос статуса домашних работ"
        )
    )
    params = {"from_date": timestamp}

    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        message_text = messages.LOG_ENDPOINT_ACCESS_ERROR.format(
            message=error, endpoint=ENDPOINT
        )
        raise APIEndpointAccessError(message_text)

    if response.status_code != HTTPStatus.OK:
        message_text = messages.LOG_ENDPOINT_BAD_STATUS.format(
            endpoint=ENDPOINT, status=response.status_code
        )
        raise APIEndpointAccessError(message_text)
    return response.json()


def check_response(response):
    """Анализ ответа response на соответствие ожидаемому формату."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="check_response() анализ формата ответа."
        )
    )

    response_keys = {RESPONSE_HOMEWORKS: list, RESPONSE_DATE: int}
    if not isinstance(response, dict):
        raise APIResponseWrongFormat(messages.LOG_RESPONSE_WRONG_FORMAT)

    for key, type_name in response_keys.items():
        response_key = response.get(key)
        if response_key is None:
            message_text = messages.LOG_RESPONSE_KEY_NOT_FOUND(key=key)
            raise APIResponseWrongFormat(message_text)
        if not isinstance(response_key, type_name):
            message_text = messages.LOG_RESPONSE_KEY_WRONG_TYPE(
                key=key, type_name=type_name
            )
            raise APIResponseWrongFormat(message_text)
    homeworks = response.get(RESPONSE_HOMEWORKS)
    if not homeworks:
        logging.debug(messages.LOG_RESPONSE_NO_HOMEWORKS)
        return None
    return homeworks[0]


def parse_status(homework):
    """Анализ статуса домашней работы."""
    if homework is None:
        return None
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="parse_status() анализ статуса домашней работы."
        )
    )
    homework_name = homework.get(HOMEWORK_NAME)
    if not homework_name:
        message_text = messages.LOG_RESPONSE_KEY_NOT_FOUND.format(
            key=HOMEWORK_NAME
        )
        raise APIResponseWrongFormat(message_text)

    homework_status = homework.get(HOMEWORK_STATUS)
    if not homework_status:
        message_text = messages.LOG_RESPONSE_KEY_NOT_FOUND.format(
            key=HOMEWORK_STATUS
        )
        raise APIResponseWrongFormat(message_text)
    if homework_status not in HOMEWORK_VERDICTS:
        message_text = messages.LOG_HOMEWORK_WRONG_STATUS.format(
            status=homework_status
        )
        raise APIResponseWrongFormat(message_text)

    message_text = messages.HOMEWORK_STATUS_CHANGED.format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS.get(homework_status),
    )
    return message_text


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_sent_error_message = ""
    last_homework_status_message = ""

    while True:
        try:
            response = get_api_answer(timestamp)
            homework_status = check_response(response)
            timestamp = response.get(RESPONSE_DATE, timestamp)
            homework_status_message = parse_status(homework_status)
            if (
                homework_status_message
                and homework_status_message != last_homework_status_message
            ):
                send_message(bot, str(homework_status_message))
                last_homework_status_message = homework_status_message

        except BotSendMessageError:
            pass  # logged in send_message
        except (APIEndpointAccessError, APIResponseWrongFormat) as error:
            error_str = str(error)
            logging.exception(error)
            if error_str != last_sent_error_message:
                send_message(bot, str(error_str))
                last_sent_error_message = error_str
        except Exception as error:
            message = messages.LOG_UNKNOWN_ERROR.format(error=error)
            logging.error(message)
            logging.exception(error)

        time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    file_handler = logging.FileHandler(
        filename="homework.log", mode="a", encoding="utf-8"
    )
    logging.basicConfig(
        format="%(asctime)s: %(name)s [%(levelname)s] %(message)s",
        level=logging.DEBUG,
        handlers=[file_handler, logging.StreamHandler(stream=sys.stdout)],
    )
    main()
