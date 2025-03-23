import socket

iso8583_server_ip = "23.33.244.104"
iso8583_port = 5050  

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)  # Set 5-second timeout

try:
    sock.connect((iso8583_server_ip, iso8583_port))
    print("[✅] Connection established!")
    
    # Example ISO 8583 message (modify based on your needs)
    message = b'\x02\x00\x00\x00\x00\x00\x00\x01'  # Sample binary message
    sock.send(message)

    response = sock.recv(1024)
    print(f"Received Response: {response.hex()}")

except socket.timeout:
    print("[❌] Connection timed out!")
except ConnectionRefusedError:
    print("[❌] Connection refused - server is not accepting connections.")
except Exception as e:
    print(f"[❌] Error: {e}")
finally:
    sock.close()
