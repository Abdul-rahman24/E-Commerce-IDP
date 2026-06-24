class AppError(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundError(AppError):
    def __init__(self, message="Resource not found"):
        super().__init__(message, 404)

class BadRequestError(AppError):
    def __init__(self, message="Bad request"):
        super().__init__(message, 400)

class ConflictError(AppError):
    def __init__(self, message="Resource already exists"):
        super().__init__(message, 409)

class DatabaseError(AppError):
    def __init__(self, message="Database operation failed"):
        super().__init__(message, 500)