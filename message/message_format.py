from typing import Tuple, List
from io import BytesIO
from random import randrange
import time

from message.header import Header
from message.question import Question
from message.resource_record import ResourceRecord as RR
from message.flags import RCode, Type
from auxiliary import Auxiliary as Aux


class Message:
    def __init__(self,
                 header: Header,
                 questions: List[Question],
                 answer_rrs: List[RR] = list(),
                 authority_rrs: List[RR] = list(),
                 additional_rrs: List[RR] = list()
                 ):
        self.header = header
        self.questions = questions
        self.answer_rrs = answer_rrs
        self.authority_rrs = authority_rrs
        self.additional_rrs = additional_rrs

    @staticmethod
    def create_query(name: str,
                     qtype: Type,
                     id: bytes = randrange(2**16).to_bytes(2, 'big'),
                     ):
        header = Header(id, qr=False, qdcount=1)
        questions = [Question(name, qtype)]
        return Message(header, questions)

    @staticmethod
    def create_response(id: bytes, r_code: RCode, questions, answer_rrs):
        header = Header(id, qr=True, rd=True, ra=True, rcode=r_code, qdcount=len(questions), ancount=len(answer_rrs))
        return Message(header, questions, answer_rrs)

    @staticmethod
    def parse(data: bytes):
        data_length = 0
        header, length = Header.parse(data, 0)
        data_length += length

        questions = []
        for i in range(header.qd_count):
            question, length = Question.parse(data, data_length, Message._parse_name)
            data_length += length
            questions.append(question)

        rrs = []
        for i in range(header.an_count + header.ns_count + header.ar_count):
            rr, length = RR.parse(data, data_length, Message._parse_name)
            data_length += length
            rrs.append(rr)

        answer_rrs = rrs[:header.an_count]
        authority_rrs = rrs[header.an_count: header.an_count + header.ns_count]
        additional_rrs = rrs[header.an_count + header.ns_count:]

        return Message(header, questions, answer_rrs, authority_rrs, additional_rrs)

    @staticmethod
    def _parse_name(raw_data: bytes, start: int) -> Tuple[str, int]:
        name_length = 0
        data = raw_data[start:]
        with BytesIO(data) as data_stream:
            labels = []
            end = False
            while not end:
                byte = Aux.bytes_to_bits(data_stream.read(1))
                name_length += 1
                if byte[:2] == '00':
                    label_length = int(byte[2:], 2)
                    if label_length == 0:
                        break
                    labels.append(data_stream.read(label_length).decode())
                    name_length += label_length
                elif byte[:2] == '11':
                    second_byte = Aux.bytes_to_bits(data_stream.read(1))
                    name_length += 1
                    offset = int(byte[2:] + second_byte, 2)
                    pointer_name, pointer_length = Message._parse_name(raw_data, offset)
                    labels.append(pointer_name)
                    end = True
                else:
                    raise NotImplementedError('the flag {} in domain name isn\'t implemented'.format(byte[:2]))
        return '.'.join(labels), name_length

    def to_bytes(self) -> bytes:
        return self.header.to_bytes() + \
               b''.join([question.to_bytes(Message._name_to_bytes) for question in self.questions]) + \
               b''.join([rr.to_bytes(Message._name_to_bytes)
                         for rr in self.answer_rrs + self.authority_rrs + self.additional_rrs])

    @staticmethod
    def _name_to_bytes(name: str) -> bytes:
        result = b''
        labels = name.split('.')
        for label in labels:
            result += len(label).to_bytes(1, 'big')
            result += bytes(label, 'utf-8')
        return result + (0).to_bytes(1, 'big')

    @staticmethod
    def create_rr(query: Question, data: str, expiry_time: int):
        ttl = (expiry_time - int(time.time())) if expiry_time != -1 else 60*60*24
        return RR.create(query.qname, ttl=ttl, rdata=data, rtype=query.qtype)

    @staticmethod
    def create_question(name: str, qtype: Type):
        return Question(name, qtype)

    def __str__(self):
        parts = [
            ['HEADER', str(self.header)],
            ['QUESTIONS', *[str(question) for question in self.questions]],
            ['ANSWER RRs', *[str(answer) for answer in self.answer_rrs]],
            ['AUTHORITY RRs', *[str(auth_rr) for auth_rr in self.authority_rrs]],
            ['ADDITIONAL RRs', *[str(add_rr) for add_rr in self.additional_rrs]]
        ]
        return '\n'.join(['\n'.join(part) + '\n' for part in parts])
