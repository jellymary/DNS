import unittest

from message.message_format import Message
from message.flags import *
from message.header import Header
from message.question import Question


class TestParsing(unittest.TestCase):

    DATA = b'\xe7\x26\x81\x80\x00\x01' \
           b'\x00\x04\x00\x03\x00\x04\x06\x79\x61\x6e\x64\x65\x78\x02\x72\x75' \
           b'\x00\x00\x01\x00\x01\xc0\x0c\x00\x01\x00\x01\x00\x00\x01\x2a\x00' \
           b'\x04\x4d\x58\x37\x50\xc0\x0c\x00\x01\x00\x01\x00\x00\x01\x2a\x00' \
           b'\x04\x05\xff\xff\x50\xc0\x0c\x00\x01\x00\x01\x00\x00\x01\x2a\x00' \
           b'\x04\x05\xff\xff\x4d\xc0\x0c\x00\x01\x00\x01\x00\x00\x01\x2a\x00' \
           b'\x04\x4d\x58\x37\x4d\xc0\x0c\x00\x02\x00\x01\x00\x00\x9d\x13\x00' \
           b'\x06\x03\x6e\x73\x32\xc0\x0c\xc0\x0c\x00\x02\x00\x01\x00\x00\x9d' \
           b'\x13\x00\x06\x03\x6e\x73\x31\xc0\x0c\xc0\x0c\x00\x02\x00\x01\x00' \
           b'\x00\x9d\x13\x00\x14\x03\x6e\x73\x39\x0a\x7a\x35\x68\x36\x34\x71' \
           b'\x39\x32\x78\x39\x03\x6e\x65\x74\x00\xc0\x79\x00\x01\x00\x01\x00' \
           b'\x04\x64\xe1\x00\x04\xd5\xb4\xc1\x01\xc0\x67\x00\x01\x00\x01\x00' \
           b'\x05\x2f\xa7\x00\x04\x5d\x9e\x86\x01\xc0\x79\x00\x1c\x00\x01\x00' \
           b'\x00\x0d\xba\x00\x10\x2a\x02\x06\xb8\x00\x00\x00\x00\x00\x00\x00' \
           b'\x00\x00\x00\x00\x01\xc0\x67\x00\x1c\x00\x01\x00\x00\x0d\x33\x00' \
           b'\x10\x2a\x02\x06\xb8\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00' \
           b'\x01'

    def test_name_parser_labels_sequence(self):
        name, length = Message._parse_name(self.DATA, 139)
        self.assertEqual(name, 'ns9.z5h64q92x9.net')
        self.assertEqual(length, 20)

    def test_name_parser_pointer(self):
        name, length = Message._parse_name(self.DATA, 27)
        self.assertEqual(name, 'yandex.ru')
        self.assertEqual(length, 2)

    def test_name_parser_labels_and_pointer(self):
        name, length = Message._parse_name(self.DATA, 103)
        self.assertEqual(name, 'ns2.yandex.ru')
        self.assertEqual(length, 6)

    def test_header_parsing(self):
        header, header_length = Header.parse(self.DATA, 0)
        self.assertEqual(header_length, 12)
        self.assertEqual(header.id, b'\xe7\x26')
        self.assertTrue(header.qr)
        self.assertEqual(header.op_code, Opcode.QUERY)
        self.assertFalse(header.aa)
        self.assertFalse(header.tc)
        self.assertTrue(header.rd)
        self.assertTrue(header.ra)
        self.assertEqual(header.r_code, RCode.NO_ERROR)
        self.assertEqual(header.qd_count, 1)
        self.assertEqual(header.an_count, 4)
        self.assertEqual(header.ns_count, 3)
        self.assertEqual(header.ar_count, 4)

    def test_question_parsing(self):
        question, length = Question.parse(self.DATA, 12, Message._parse_name)
        self.assertEqual(question.qname, 'yandex.ru')
        self.assertEqual(question.qclass, Class.IN)
        self.assertEqual(question.qtype, Type.A)

    # def test_parse(self):
    #     message = Message.parse(self.DATA)
    #     print(message)


class TestPackingInBytes(unittest.TestCase):
    def test_query_to_bytes(self):
        expected = b'\xe7\x26\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00' \
                   b'\x06\x79\x61\x6e\x64\x65\x78\x02\x72\x75\x00\x00\x01\x00\x01'
        actual = Message.create_query('yandex.ru', Type.A, id=b'\xe7\x26').to_bytes()
        self.assertEqual(len(expected), len(actual))
        self.assertSequenceEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
