from enum import Enum, auto


class RPCStatus(Enum):
    OK = auto()
    BAD_REQUEST = auto()
    UNAUTHORIZED = auto()