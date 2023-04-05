LOG_BOT_START: str = "Программа бота запущена."
LOG_FUNCTION_START: str = "Запуск функции {function_info}"
LOG_TOKENS_NOT_FOUND: str = (
    "Отсутствуют обязательные переменные окружения {tokens}"
)
LOG_MESSAGE_SENT: str = 'Сообщение отправлено: "{message}"'
LOG_MESSAGE_SENT_ERROR: str = (
    'Ошибка "{error}" при отправке сообщения :\n' '"{message}"'
)
LOG_ENDPOINT_ACCESS_ERROR: str = (
    'Ошибка доступа к ендпойнту "{endpoint}"\n {message} '
)
LOG_ENDPOINT_BAD_STATUS: str = (
    'Ошибка доступа к ендпойнту "{endpoint}": Статус ответа {status} '
)
LOG_RESPONSE_WRONG_FORMAT: str = (
    'Ошибка формата ответа.'
)
LOG_RESPONSE_KEY_NOT_FOUND: str = (
    'Ошибка формата ответа: не найден ключ "{key}"'
)
LOG_RESPONSE_KEY_WRONG_TYPE: str = (
    'Ошибка формата ответа: тип ключа "{key}"'
    ' не соответствует ожидаемому {type}'
)
LOG_RESPONSE_NO_HOMEWORKS: str = (
    'Ответ не содержит ни одной записи о домашней работе.'
)
LOG_HOMEWORK_WRONG_STATUS: str = (
    'Неизвестный статус "{status}" выполнения домашней работы.'
)
HOMEWORK_STATUS_CHANGED: str = (
    'Изменился статус проверки работы "{homework_name}". {verdict}'
)
LOG_UNKNOWN_ERROR: str = (
    'Сбой в работе программы: {error}'
)
LOG_API_REQUEST_PARAMS: str = (
    'Отправка запроса: url={url}, headers={headers}, params={params}'
)
