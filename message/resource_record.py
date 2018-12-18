from typing import Callable, Tuple
from io import BytesIO

from message.flags import Type, Class


class ResourceRecord:
    def __init__(self,
                 name: str,
                 rtype: Type,
                 rclass: Class,
                 ttl: int,
                 rdata: str
                 ):
        self.name = name
        self.rtype = rtype
        self.rclass = rclass
        self.ttl = ttl
        self.rdata = rdata

    @staticmethod
    def create(name: str,
               ttl: int,
               rdata: str,
               rtype: Type = Type.A,
               rclass: Class = Class.IN):
        return ResourceRecord(name, rtype, rclass, ttl, rdata)

    @staticmethod
    def parse(raw_data: bytes,
              start: int,
              name_parser: Callable[[bytes, int], Tuple[str, int]]
              ):
        name, length = name_parser(raw_data, start)
        data = raw_data[start + length:]
        with BytesIO(data) as data_stream:
            rtype = Type(int.from_bytes(data_stream.read(2), 'big'))
            length += 2
            rclass = Class(int.from_bytes(data_stream.read(2), 'big'))
            length += 2
            ttl = int.from_bytes(data_stream.read(4), 'big')
            length += 4
            rd_length = int.from_bytes(data_stream.read(2), 'big')
            length += 2
        try:
            rdata = ResourceRecord._parse_data(name_parser, raw_data, start + length, rd_length, rtype, rclass)
        except NotImplementedError:
            rdata = None
        length += rd_length
        return ResourceRecord(name, rtype, rclass, ttl, rdata), length

    @staticmethod
    def _parse_data(name_parser: Callable[[bytes, int], Tuple[str, int]],
                    data: bytes,
                    start: int,
                    length: int,
                    rr_type: Type,
                    rr_class: Class
                    ) -> str:
        if rr_class != Class.IN:
            raise NotImplementedError('Parsing data of class {} is not implemented'.format(rr_class.name))
        if rr_type == Type.A:
            ip_address = data[start: start + length]
            return '.'.join([str(byte) for byte in ip_address])
        elif rr_type == Type.NS:
            name, name_length = name_parser(data, start)
            if length != name_length:
                raise ValueError('Something went wrong')
            return name
        elif rr_type == Type.AAAA:
            parts = []
            with BytesIO(data[start: start + length]) as ip_address:
                for i in range(length // 2):
                    parts.append(ip_address.read(2).hex())
            return ':'.join(parts)
        else:
            raise NotImplementedError('Parsing data of type {} is not implemented'.format(rr_type.name))

    def to_bytes(self, name_to_bytes) -> bytes:
        encoded_data = self._data_to_bytes(name_to_bytes)
        rdlength = len(encoded_data)
        return name_to_bytes(self.name) + \
               self.rtype.value.to_bytes(2, 'big') + \
               self.rclass.value.to_bytes(2, 'big') + \
               self.ttl.to_bytes(4, 'big') + \
               rdlength.to_bytes(2, 'big') + \
               encoded_data

    def _data_to_bytes(self, name_to_bytes) -> bytes:
        if self.rclass != Class.IN:
            raise NotImplementedError()
        if self.rtype == Type.A:
            result = b''
            parts = self.rdata.split('.')
            for part in parts:
                result += int(part).to_bytes(1, 'big')
            return result
        if self.rtype == Type.NS:
            return name_to_bytes(self.rdata)
        raise NotImplementedError()

    def __str__(self):
        return '{} {} {} {} {}'.format(self.name, self.rtype.name, self.rclass.name, self.ttl, self.rdata)
