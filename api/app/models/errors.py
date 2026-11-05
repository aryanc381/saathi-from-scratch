"""Responsible for the error that routes raise when a request cannot be served."""


# An expected API error: the HTTP status, a short code and a message for the client.
class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
