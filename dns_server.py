import os.path
from socket import socket, AF_INET, SOCK_DGRAM, timeout
import time
from typing import List
import json

from message.message_format import Message
from message.flags import RCode
from message.flags import *


class DNSServer:
    ROOT_SERVERS_FILE_NAME = 'root_servers.txt'
    A_RECORDS_CACHE_FILE_NAME = 'a_records_cache.txt'
    NS_RECORDS_CACHE_FILE_NAME = 'ns_records_cache.txt'

    def __init__(self, port: int = 53):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.a_records_cache = {}
        self.ns_records_cache = {}
        try:
            self.sock.bind(('', port))
        except Exception:
            print('Check that the port {} is available'.format(port))
            self.sock.close()

    def start(self) -> None:
        self._load_cache()
        print('LOAD CACHE')
        self._run()

    def _load_cache(self):
        root_servers = self._load(self.ROOT_SERVERS_FILE_NAME)
        if os.path.exists(self.A_RECORDS_CACHE_FILE_NAME):
            self.a_records_cache = self._load(self.A_RECORDS_CACHE_FILE_NAME)
        else:
            for domain_name, ip_address in root_servers.items():
                self.a_records_cache[domain_name] = [[ip_address, -1]]

        if os.path.exists(self.NS_RECORDS_CACHE_FILE_NAME):
            self.ns_records_cache = self._load(self.NS_RECORDS_CACHE_FILE_NAME)
        else:
            self.ns_records_cache[''] = [[name, -1] for name in root_servers]
        self._remove_expired_records()

    @staticmethod
    def _load(file_name: str) -> dict:
        with open(file_name, 'r', encoding='utf-8') as file:
            return json.loads(file.readline())

    def _remove_expired_records(self):
        current_time = time.time()
        for zone_name, ns_time_pairs in self.ns_records_cache.items():
            self.ns_records_cache[zone_name] = [ns_time_pair for ns_time_pair in ns_time_pairs
                                                if ns_time_pair[1] > current_time or ns_time_pair[1] == -1]
        for domain_name, ip_time_pairs in self.a_records_cache.items():
            self.a_records_cache[domain_name] = [ip_time_pair for ip_time_pair in ip_time_pairs
                                                 if ip_time_pair[1] > current_time or ip_time_pair[1] == -1]

    def _run(self) -> None:
        print("DNS SERVER IS RUNNING")
        while True:
            print('*' * 50)
            question, client_address = self.sock.recvfrom(512)
            print("{} SEND QUERY".format(client_address))
            message = Message.parse(question)
            answers = []
            query = message.questions[0]
            r_code, answer_rrs = self._resolve(query)
            answers += answer_rrs
            response = Message.create_response(message.header.id, r_code, message.questions, answers)
            self.sock.sendto(response.to_bytes(), client_address)
            print("RESPONSE SENT TO {}".format(client_address))
            self._dump_cache()

    def _dump_cache(self) -> None:
        with open(self.A_RECORDS_CACHE_FILE_NAME, 'w', encoding='utf-8') as file:
            file.write(json.dumps(self.a_records_cache))
        with open(self.NS_RECORDS_CACHE_FILE_NAME, 'w', encoding='utf-8') as file:
            file.write(json.dumps(self.ns_records_cache))

    def _get_destination_server_names(self, name: str) -> list:
        zone = self._find_domain_name(name, [key for key, value in self.ns_records_cache.items() if len(value) != 0])
        return [ns_time_pair[0] for ns_time_pair in self.ns_records_cache[zone]
                if ns_time_pair[1] > time.time() or ns_time_pair[1] == -1]

    def _resolve(self, query) -> (RCode, list):
        print('-' * 40)
        print("Resolve {}".format(query.qname))
        search_results = self._cache_search(query)
        if search_results:
            records = [Message.create_rr(query, *result) for result in search_results]
            print('Found in cache')
            for record in records:
                print(record)
            print('-' * 40)
            return RCode.NO_ERROR, records

        query_message = Message.create_query(query.qname, query.qtype)
        bytes_query = query_message.to_bytes()
        while True:
            servers = self._get_destination_server_names(query.qname)
            received = False
            for server in servers:
                if received:
                    break
                if server not in self.a_records_cache:
                    server_query = Message.create_question(server, query.qtype)
                    intermediate_r_code, intermediate_response = self._resolve(server_query)
                    if intermediate_r_code != RCode.NO_ERROR:
                        continue
                ip_addresses = [ip_time_pairs[0] for ip_time_pairs in self.a_records_cache[server]
                                if ip_time_pairs[1] > time.time() or ip_time_pairs[1] == -1]
                for ip_address in ip_addresses:
                    self.sock.sendto(bytes_query, (ip_address, 53))
                    print('Query to {} ({})'.format(server, ip_address))
                    answer_received = False
                    self.sock.settimeout(3)
                    try:
                        while not answer_received:
                            raw_response, address = self.sock.recvfrom(512)
                            response = Message.parse(raw_response)
                            if response.header.id == query_message.header.id:
                                answer_received = True
                    except timeout:
                        print('Server {} ({}) is not responding'.format(server, ip_address))
                        continue
                    finally:
                        self.sock.settimeout(None)
                    if response.header.r_code != RCode.NO_ERROR:
                        print('Error {}'.format(response.header.r_code.name))
                        return response.header.r_code, []
                    self.update_cache(response)
                    # print(response, end='\n\n')
                    if response.answer_rrs:
                        for ans_rr in response.answer_rrs:
                            print(ans_rr)
                        print('-' * 40)
                        return RCode.NO_ERROR, response.answer_rrs
                    received = True
                    break
            if not received:
                raise ConnectionError('There may be no Internet connection')

    def _cache_search(self, query):
        if query.qclass != Class.IN:
            raise NotImplementedError('Class {} is not implemented'.format(query.qclass))
        if query.qtype == Type.NS:
            if query.qname in self.ns_records_cache:
                return [ns_time_pair for ns_time_pair in self.ns_records_cache[query.qname]
                        if ns_time_pair[1] > time.time() or ns_time_pair[1] == -1]
        elif query.qtype == Type.A:
            if query.qname in self.a_records_cache:
                return [ip_time_pair for ip_time_pair in self.a_records_cache[query.qname]
                        if ip_time_pair[1] > time.time() or ip_time_pair[1] == -1]
        # else:
        #     raise NotImplementedError('Type {} is not implemented'.format(query.qtype))
        return None

    @staticmethod
    def _find_domain_name(name: str, domain_names: List[str]):
        labels = name.split('.')
        labels.reverse()
        suffix = ''
        best_match = ''
        for label in labels:
            suffix = label + (('.' + suffix) if suffix else '')
            if suffix in domain_names:
                best_match = suffix
        return best_match

    def update_cache(self, response: Message) -> None:
        for rr in response.answer_rrs + response.authority_rrs + response.additional_rrs:
            if rr.rclass != Class.IN:
                raise NotImplementedError('Class {} isn\'t implemented'.format(rr.rclass))
            expiry_time = int(time.time()) + rr.ttl
            if rr.rtype == Type.A:
                if rr.name in self.a_records_cache:
                    is_new_rr = True
                    for ip_time_pair in self.a_records_cache[rr.name]:
                        if rr.rdata == ip_time_pair[0]:
                            ip_time_pair[1] = max(expiry_time, ip_time_pair[1])
                            is_new_rr = False
                            break
                    if is_new_rr:
                        self.a_records_cache[rr.name].append([rr.rdata, expiry_time])
                else:
                    self.a_records_cache[rr.name] = [[rr.rdata, expiry_time]]

            elif rr.rtype == Type.NS:
                if rr.name in self.ns_records_cache:
                    is_new_rr = True
                    for ns_time_pair in self.ns_records_cache[rr.name]:
                        if rr.rdata == ns_time_pair[0]:
                            ns_time_pair[1] = max(expiry_time, ns_time_pair[1])
                            is_new_rr = False
                            break
                    if is_new_rr:
                        self.ns_records_cache[rr.name].append([rr.rdata, expiry_time])
                else:
                    self.ns_records_cache[rr.name] = [[rr.rdata, expiry_time]]

    def print_cache(self):
        print('NS RECORDS CACHE', end='\n\n')
        print('\n'.join(['{}: {}'.format(key, [data[0] for data in value]) for key, value in self.ns_records_cache.items()]), end='\n\n')
        print('A RECORDS CACHE', end='\n\n')
        print('\n'.join(['{}: {}'.format(key, [data[0] for data in value]) for key, value in self.a_records_cache.items()]), end='\n\n')


if __name__ == '__main__':
    DNSServer(port=53).start()
