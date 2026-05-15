class FileNotExistsError(Exception):
    pass


class FileTooLargeError(Exception):
    description = "{message}"

    def __init__(self, message: str = "File is too large"):
        self.message = message
        super().__init__(message)


class UnsupportedFileTypeError(Exception):
    pass


class BlockedFileExtensionError(Exception):
    description = "File extension '{extension}' is not allowed for security reasons"

    def __init__(self, extension: str = ""):
        self.extension = extension
        super().__init__(f"File extension '{extension}' is not allowed for security reasons")
