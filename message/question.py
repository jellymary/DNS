from typing import Callable
from io import BytesIO

from message.flags import Type, Class


class Question:
    def __init__(self,
                 qname: str,
                 qtype: Type = Type.A,
                 qclass: Class = Class.IN
                 ):
        self.qname = qname
        self.qtype = qtype
        self.qclass = qclass

    @staticmethod
    def parse(raw_data: bytes, start: int, name_parser):
        qname, length = name_parser(raw_data, start)
        data = raw_data[start + length:]
        with BytesIO(data) as data_stream:
            qtype = Type(int.from_bytes(data_stream.read(2), 'big'))
            length += 2
            qclass = Class(int.from_bytes(data_stream.read(2), 'big'))
            length += 2
        return Question(qname, qtype, qclass), length

    def to_bytes(self, name_to_bytes: Callable[[str], bytes]) -> bytes:
        return name_to_bytes(self.qname) + \
               self.qtype.value.to_bytes(2, 'big') + \
               self.qclass.value.to_bytes(2, 'big')

    def __str__(self):
        return "{} {} {}".format(self.qname, self.qtype.name, self.qclass.name)
