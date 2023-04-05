import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Any, NoReturn, Optional

import requests
import telegram
from dotenv import load_dotenv

import messages
from exceptions import (
    APIEndpointAccessError,
    APIResponseWrongFormat,
    BotSendMessageError,
    MissingTokensError,
)

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD: int = 600
ENDPOINT: str = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS: dict[str:str] = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS: dict[str:str] = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

RESPONSE_DATE: str = "current_date"
RESPONSE_HOMEWORKS: str = "homeworks"
HOMEWORK_NAME: str = "homework_name"
HOMEWORK_STATUS: str = "status"


def check_tokens() -> NoReturn:
    """Проверка наличия необходимых переменных окружения."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="проверки наличия переменных окружения check_tokens"
        )
    )
    TOKENS: dict[str: Optional[str]] = {
        "PRACTICUM_TOKEN": PRACTICUM_TOKEN,
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }

    if not all(TOKENS.values()):
        # формируем список отсутствующих токенов для вывода в логи
        missed_tokens: list[str] = [k for k, v in TOKENS.items() if v is None]
        message_text: str = messages.LOG_TOKENS_NOT_FOUND.format(
            tokens=", ".join(missed_tokens)
        )
        logging.critical(message_text)
        raise MissingTokensError(message_text)


def send_message(bot: telegram.Bot, message: str) -> NoReturn:
    """Отправка сообщения message от имени бота bot."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="отправки сообщения send_message"
        )
    )
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        message_text: str = messages.LOG_MESSAGE_SENT_ERROR.format(
            error=error, message=message
        )
        logging.error(message_text)
        raise BotSendMessageError(message_text)

    else:
        logging.debug(messages.LOG_MESSAGE_SENT.format(message=message))


def get_api_answer(timestamp: int) -> Any:
    """API запрос статуса домашних работ, начиная с даты timestamp."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="get_api_answer() API запрос статуса домашних работ"
        )
    )
    params: dict[str:int] = {"from_date": timestamp}
    request_params: dict = {
        "url": ENDPOINT,
        "headers": HEADERS,
        "params": params,
    }
    logging.debug(messages.LOG_API_REQUEST_PARAMS.format(**request_params))
    try:
        response: requests.Response = requests.get(**request_params)
    except requests.RequestException as error:
        message_text: str = messages.LOG_ENDPOINT_ACCESS_ERROR.format(
            message=error, endpoint=ENDPOINT
        )
        raise APIEndpointAccessError(message_text)

    if response.status_code != HTTPStatus.OK:
        message_text: str = messages.LOG_ENDPOINT_BAD_STATUS.format(
            endpoint=ENDPOINT, status=response.status_code
        )
        raise APIEndpointAccessError(message_text)
    return response.json()


def check_response(response: requests.Response) -> Optional[dict]:
    """Анализ ответа response на соответствие ожидаемому формату."""
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="check_response() анализ формата ответа."
        )
    )

    response_keys: dict[str:type] = {
        RESPONSE_HOMEWORKS: list,
        RESPONSE_DATE: int,
    }
    if not isinstance(response, dict):
        raise APIResponseWrongFormat(messages.LOG_RESPONSE_WRONG_FORMAT)

    for key, type_name in response_keys.items():
        response_key: Any = response.get(key)
        if response_key is None:
            message_text: str = messages.LOG_RESPONSE_KEY_NOT_FOUND(key=key)
            raise APIResponseWrongFormat(message_text)
        if not isinstance(response_key, type_name):
            message_text: str = messages.LOG_RESPONSE_KEY_WRONG_TYPE(
                key=key, type_name=type_name
            )
            raise APIResponseWrongFormat(message_text)
    homeworks: Optional[list[dict]] = response.get(RESPONSE_HOMEWORKS)
    if not homeworks:
        logging.debug(messages.LOG_RESPONSE_NO_HOMEWORKS)
        return None
    return homeworks[0]


def parse_status(homework: Optional[dict]) -> str:
    """Анализ статуса домашней работы."""
    if homework is None:
        return None
    logging.debug(
        messages.LOG_FUNCTION_START.format(
            function_info="parse_status() анализ статуса домашней работы."
        )
    )
    homework_name: str = homework.get(HOMEWORK_NAME)
    if not homework_name:
        message_text = messages.LOG_RESPONSE_KEY_NOT_FOUND.format(
            key=HOMEWORK_NAME
        )
        raise APIResponseWrongFormat(message_text)

    homework_status: str = homework.get(HOMEWORK_STATUS)
    if not homework_status:
        message_text = messages.LOG_RESPONSE_KEY_NOT_FOUND.format(
            key=HOMEWORK_STATUS
        )
        raise APIResponseWrongFormat(message_text)
    if homework_status not in HOMEWORK_VERDICTS:
        message_text: str = messages.LOG_HOMEWORK_WRONG_STATUS.format(
            status=homework_status
        )
        raise APIResponseWrongFormat(message_text)

    message_text: str = messages.HOMEWORK_STATUS_CHANGED.format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS.get(homework_status),
    )
    return message_text


def main():
    """Основная логика работы бота."""
    logging.info(messages.LOG_BOT_START)
    try:
        check_tokens()
    except MissingTokensError as error:
        logging.exception(error)
        sys.exit(1)

    bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())
    last_sent_error_message: str = ""
    last_homework_status_message: str = ""

    while True:
        try:
            response: requests.Response = get_api_answer(timestamp)
            homework_status: str = check_response(response)
            timestamp: int = response.get(RESPONSE_DATE, timestamp)
            homework_status_message: str = parse_status(homework_status)
            if homework_status_message and (
                homework_status_message != last_homework_status_message
            ):
                send_message(bot, str(homework_status_message))
                last_homework_status_message = homework_status_message

        except BotSendMessageError:
            pass  # logged in send_message
        except (APIEndpointAccessError, APIResponseWrongFormat) as error:
            error_str: str = str(error)
            logging.exception(error)
            if error_str != last_sent_error_message:
                send_message(bot, str(error_str))
                last_sent_error_message = error_str
        except Exception as error:
            message: str = messages.LOG_UNKNOWN_ERROR.format(error=error)
            logging.error(message)
            logging.exception(error)
        finally:
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
