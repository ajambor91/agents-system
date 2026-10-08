"""Public builder flow and real socket exchange tests."""
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path






class PublicContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load the actual package; missing production dependencies must fail visibly.
        global ApplicationConfiguration
        from lib.unix_socket.abstract.models import AbstractSocketConfiguration
        class ApplicationConfiguration(AbstractSocketConfiguration):
            def __init__(self, path, limit=1024):
                self._path = Path(path)
                self._limit = limit

            @property
            def socket_path(self):
                return self._path

            @property
            def connect_timeout(self):
                return 1.0

            @property
            def request_timeout(self):
                return 1.0

            @property
            def maximum_response_bytes(self):
                return self._limit

        global SocketClient, SocketClientBuilder, Request
        global ClientNotConfiguredException, MessageCodec, UnixSocketClient
        global UnixSocketTransport, UnixSocketProtocolException, UnixSocketSerializationException
        from lib.unix_socket.socket_client import SocketClient
        from lib.unix_socket.socket_client_builder import SocketClientBuilder
        from lib.unix_socket.models import Request
        from lib.unix_socket.client import UnixSocketClient
        from lib.unix_socket.codec import MessageCodec
        from lib.unix_socket.transport import UnixSocketTransport
        from lib.unix_socket.exceptions import (
            ClientNotConfiguredException, UnixSocketProtocolException,
            UnixSocketSerializationException,
        )

    def test_configuration_required_and_get_requires_create(self):
        builder = SocketClientBuilder.configure()
        with self.assertRaises(ClientNotConfiguredException):
            builder.get()
        for value in (None, object(), {}):
            with self.assertRaises(TypeError):
                SocketClientBuilder.create(value)
        with self.assertRaises(TypeError):
            SocketClientBuilder.create()

    def test_defaults_and_independent_builders(self):
        configuration = ApplicationConfiguration('/tmp/example.sock')
        first = SocketClientBuilder.create(configuration).get()
        second = SocketClientBuilder.create(configuration=configuration).get()
        self.assertIsInstance(first, SocketClient)
        self.assertIsInstance(first.client, UnixSocketClient)
        self.assertIsInstance(first.codec, MessageCodec)
        self.assertIsInstance(first.transport, UnixSocketTransport)
        self.assertIsNot(first, second)
        self.assertIsNot(first.transport, second.transport)
        self.assertFalse(first.is_connected)

    def test_custom_components_and_facade_delegation(self):
        class Transport(UnixSocketTransport):
            def connect(self, configuration):
                self.configuration = configuration
                self.opened = True
            @property
            def is_connected(self):
                return getattr(self, 'opened', False)
            def exchange(self, frame, *, timeout=None):
                self.last_frame, self.last_timeout = frame, timeout
                return b'{"request_id":"one","successful":true,"result":42}\n'
            def close(self):
                self.opened = False
        class Client(UnixSocketClient):
            pass
        class Codec(MessageCodec):
            pass
        builder = SocketClientBuilder.configure(client=Client, codec=Codec, transport=Transport)
        self.assertIsInstance(builder, SocketClientBuilder)
        configuration = ApplicationConfiguration('/tmp/example.sock')
        facade = builder.create(configuration).get()
        self.assertIs(facade.connect(), facade)
        self.assertIs(facade.transport.configuration, configuration)
        self.assertEqual(facade.message(Request('ping', request_id='one'), timeout=0.5).result, 42)
        self.assertEqual(facade.transport.last_timeout, 0.5)
        with self.assertRaises(RuntimeError):
            builder.create(configuration)
        facade.close()
        self.assertFalse(facade.is_connected)
        with self.assertRaises(TypeError):
            SocketClientBuilder.configure(client=object)

    def test_codec_rejects_invalid_frames_and_data(self):
        codec = MessageCodec()
        for frame in (b'{}', b'{}\n{}\n', b'{}\n', b'{"request_id":"x","successful":false}\n'):
            with self.assertRaises(UnixSocketProtocolException):
                codec.decode_response(frame)
        with self.assertRaises(UnixSocketSerializationException):
            codec.encode_request(Request('ping', {'value': float('nan')}))

    def test_real_socket_partial_reads_and_repeated_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sock'
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.addCleanup(server.close)
            server.settimeout(2.0)
            server.bind(str(path))
            server.listen(1)
            failures = []
            def serve():
                try:
                    connection, _ = server.accept()
                    with connection, connection.makefile('rb') as stream:
                        for _ in range(2):
                            request = json.loads(stream.readline())
                            response = json.dumps({'request_id': request['request_id'], 'successful': True, 'result': request['payload']}).encode() + b'\n'
                            connection.sendall(response[:5])
                            connection.sendall(response[5:])
                except Exception as exc:
                    failures.append(exc)
            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            facade = SocketClientBuilder.create(ApplicationConfiguration(path)).get()
            try:
                facade.connect()
                for number in range(2):
                    self.assertEqual(facade.message(Request('echo', {'number': number})).result, {'number': number})
            finally:
                facade.close()
                server.close()
                thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])

    def test_response_size_limit(self):
        from unittest.mock import Mock
        transport = UnixSocketTransport()
        transport._socket = Mock()
        transport._socket.recv.return_value = b'12345\n'
        transport._configuration = ApplicationConfiguration('/tmp/example.sock', limit=5)
        with self.assertRaises(UnixSocketProtocolException):
            transport.exchange(b'ping\n')
        transport.close()
