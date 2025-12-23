
import socket
import ssl

hostname = 'api.deepseek.com'
context = ssl.create_default_context()

try:
    with socket.create_connection((hostname, 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            print(f"SSL handshake bem sucedido com {hostname}")
            print(f"Versao: {ssock.version()}")
            print(f"Cipher: {ssock.cipher()}")
except Exception as e:
    print(f"Falha na conexao SSL: {e}")
