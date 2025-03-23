import socks
import socket
from iso8583 import ISO8583

from iso8583 import *
# from ISOErrors import *
def connect_through_socks(proxy_host, proxy_port, target_host, target_port):
    """
    Establish a TCP connection to the target via a SOCKS5 proxy.
    """
    s = socks.socksocket()
    # Configure SOCKS5; add username/password if required by your proxy.
    s.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
    s.settimeout(5)
    s.connect((target_host, target_port))
    return s

def build_iso8583_ping():
    """
    Constructs a minimal ISO 8583 'network management request' (MTI 0800).
    Adjust fields as needed for your environment.
    """
    iso = ISO8583()
    iso.set_mti('0800')
    
    # Example fields; adjust for your specific target:
    iso.set_bit(7, '0323081530')   # Field 7: Transmission date/time (MMDDhhmmss)
    iso.set_bit(11, '000001')      # Field 11: System Trace Audit Number (STAN)
    iso.set_bit(70, '001')         # Field 70: Network Management Code (e.g., sign-on)

    # Return the raw packed ISO8583 message as bytes.
    return iso.get_raw_iso()

def send_iso8583_ping(sock):
    """
    Sends the ISO8583 ping message (MTI 0800) and reads the response.
    Assumes a 2-byte length header is required by the server.
    """
    msg_bytes = build_iso8583_ping()
    
    # If the server uses a 2-byte big-endian length header:
    length_prefix = len(msg_bytes).to_bytes(2, byteorder='big')
    
    # Send the complete message.
    sock.sendall(length_prefix + msg_bytes)
    
    # Read the response; adjust buffer size if necessary.
    response_data = sock.recv(2048)
    return response_data

def parse_iso8583_response(response_data):
    """
    Attempts to parse the response data as an ISO8583 message.
    Strips a 2-byte length header first (if present).
    """
    if len(response_data) < 2:
        raise ValueError("Response too short to contain length header.")
    
    length = int.from_bytes(response_data[:2], byteorder='big')
    iso_data = response_data[2:2+length]
    
    iso_resp = ISO8583()
    iso_resp.set_network_iso(iso_data)
    return iso_resp

def main():
    print("dofsddfmkfkmsd")
    # Adjust these parameters:
    proxy_host = '127.0.0.1'     # SOCKS proxy host (Tor default)
    proxy_port = 9050            # SOCKS proxy port (Tor default)
    target_host = '192.168.1.100'  # Replace with the suspected ISO8583 server IP
    target_port = 5050             # Port used for ISO8583 (adjust if needed)
    
    try:
        # 1. Connect via SOCKS proxy.
        sock = connect_through_socks(proxy_host, proxy_port, target_host, target_port)
        print(f"[+] Connected to {target_host}:{target_port} via {proxy_host}:{proxy_port}")

        # 2. Send the ISO8583 ping message.
        response_data = send_iso8583_ping(sock)
        print(f"[+] Raw response (hex): {response_data.hex()}")

        # 3. Parse the response as ISO8583.
        iso_resp = parse_iso8583_response(response_data)
        mti = iso_resp.get_mti()
        print(f"[+] Received MTI: {mti}")
        
        if mti == '0810':
            print("[+] The response is a valid ISO8583 network management response (0810).")
        else:
            print("[!] The response MTI is not 0810; further analysis may be required.")

        # Optionally, print available ISO8583 fields.
        for bit in range(2, 129):
            val = iso_resp.get_bit(bit)
            if val:
                print(f"    Field {bit}: {val}")

        sock.close()
    
    except (socket.error, ValueError) as e:
        print(f"[!] Error during ISO8583 test: {e}")

if __name__ == '__main__':
    main()