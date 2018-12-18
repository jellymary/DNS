from io import BytesIO, StringIO

from message.flags import Opcode, RCode
from auxiliary import Auxiliary as Aux


class Header:
    def __init__(self,
                 id: bytes,
                 qr: bool = False,#query=0 OR response=1
                 opcode: Opcode = Opcode.QUERY,
                 aa: bool = False,
                 tc: bool = False,
                 rd: bool = False,
                 ra: bool = False,
                 reserved: str = '000',
                 rcode: RCode = RCode.NO_ERROR,
                 qdcount: int = 0,
                 ancount: int = 0,
                 nscount: int = 0,
                 arcount: int = 0
                 ):
        self.id = id
        self.qr = qr
        self.op_code = opcode
        self.aa = aa
        self.tc = tc
        self.rd = rd
        self.ra = ra
        self.reserved = reserved
        self.r_code = rcode
        self.qd_count = qdcount
        self.an_count = ancount
        self.ns_count = nscount
        self.ar_count = arcount

    @staticmethod
    def parse(raw_data: bytes, start: int):
        data = raw_data[start:]
        length = 0
        with BytesIO(data) as stream:
            id = stream.read(2)
            length += 2
            with StringIO(Aux.bytes_to_bits(stream.read(2))) as bits:
                qr = bool(int(bits.read(1)))
                opcode = Opcode(int(bits.read(4), 2))
                aa = bool(int(bits.read(1)))
                tc = bool(int(bits.read(1)))
                rd = bool(int(bits.read(1)))
                ra = bool(int(bits.read(1)))
                reserved = bits.read(3)
                rcode = RCode(int(bits.read(4), 2))
            length += 2
            qdcount = int.from_bytes(stream.read(2), 'big')
            length += 2
            ancount = int.from_bytes(stream.read(2), 'big')
            length += 2
            nscount = int.from_bytes(stream.read(2), 'big')
            length += 2
            arcount = int.from_bytes(stream.read(2), 'big')
            length += 2
        return Header(id=id, qr=qr, opcode=opcode,
                      aa=aa, tc=tc, rd=rd, ra=ra, rcode=rcode,
                      qdcount=qdcount, ancount=ancount, nscount=nscount, arcount=arcount), length

    def to_bytes(self) -> bytes:
        flags = Aux.flags_to_bits(self.qr, self.aa, self.tc, self.rd, self.ra)
        return self.id + int(flags[:1] + Aux.int_to_bits(self.op_code.value, 4) + flags[1:] +
                             self.reserved + Aux.int_to_bits(self.r_code, 4), 2).to_bytes(2, 'big') + \
               self.qd_count.to_bytes(2, 'big') + \
               self.an_count.to_bytes(2, 'big') + \
               self.ns_count.to_bytes(2, 'big') + \
               self.ar_count.to_bytes(2, 'big')

    def __str__(self):
        fields = {
            "ID": self.id,
            "QR": 'response' if self.qr else 'query',
            "OPCODE": self.op_code.name,
            "Authoritative Answer": self.aa,
            "TrunCation": self.tc,
            "Recursion Desired": self.rd,
            "Recursion Available": self.ra,
            "Response code": self.r_code.name,
            "Questions": self.qd_count,
            "Answer RRs": self.an_count,
            "Authority RRs": self.ns_count,
            "Additional RRs": self.ar_count
        }
        return "\n".join([field + " = {}" for field in fields.keys()]).format(*fields.values())
