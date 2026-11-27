class PDFServiceError(Exception):
    def __init__(self, message: str, client_message: str):
        super().__init__(message)
        self.message = message
        self.client_message = client_message


class PermanentError(PDFServiceError):
    def __init__(self, message: str, client_message: str = "Couldn't process a message"):
        super().__init__(message, client_message)
