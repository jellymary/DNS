from enum import IntEnum


class Type(IntEnum):
    A = 1
    NS = 2
    CNAME = 5
    SOA = 6
    PTR = 12
    MX = 15
    AAAA = 28


class Class(IntEnum):
    IN = 1
    CS = 2
    CH = 3
    HS = 4


class Opcode(IntEnum):
    QUERY = 0
    IQUERY = 1
    STATUS = 2


class RCode(IntEnum):
    NO_ERROR = 0
    FORMAT_ERROR = 1
    SERVER_FAILURE = 2
    NAME_ERROR = 3
    NOT_IMPLEMENTED = 4
    REFUSED = 5
