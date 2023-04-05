class MissingTokensError(ValueError):
    """Exception: necessary tokens missing."""

    pass


class APIEndpointAccessError(Exception):
    """Exception: endpoint access error."""

    pass


class APIResponseWrongFormat(TypeError):
    """Exception: response format error."""

    pass


class BotSendMessageError(Exception):
    """Exception: sending bot message error."""

    pass
