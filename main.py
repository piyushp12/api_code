import socks
import socket
from pyISO8583.iso8583 import ISO8583
from pyISO8583.iso8583 import InvalidIso8583Error
from pyISO8583.iso8583 import IsoFieldError

def connect_through_socks(proxy_host, proxy_port, target_host, target_port):
    """
    Establishes a TCP connection to the target via a SOCKS5 proxy.
    """
    s = socks.socksocket()
    # SOCKS5 proxy. You can also specify username/password if needed:
    # s.set_proxy(socks.SOCKS5, proxy_host, proxy_port, username="user", password="pass")
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
    
    # Set a few standard fields (examples: STAN, Transmission Date/Time, etc.)
    # Field 7: Transmission date & time (MMDDhhmmss)
    iso.set_bit(7, '0323081530')  # Example date-time: Mar 23, 08:15:30
    # Field 11: System Trace Audit Number (STAN)
    iso.set_bit(11, '000001')
    # Field 70: Network Management Information Code (e.g., '001' for sign-on)
    iso.set_bit(70, '001')

    # Return the packed ISO message
    return iso.get_raw_iso()

def send_iso8583_ping(sock):
    """
    Sends a minimal 0800 message and attempts to read the response.
    """
    msg_bytes = build_iso8583_ping()
    
    # Some ISO 8583 servers expect a 2-byte or 4-byte length header before the message.
    # Adjust as required. Example: 2-byte big-endian length header:
    length_prefix = len(msg_bytes).to_bytes(2, byteorder='big')
    
    # Send length header + ISO8583 message
    sock.sendall(length_prefix + msg_bytes)
    
    # Attempt to receive response (you might need a loop for larger messages)
    response = sock.recv(2048)
    return response

def parse_iso8583_response(response_data):
    """
    Attempts to parse the received data as an ISO 8583 message.
    Strips off the first 2 bytes if they represent length.
    """
    if len(response_data) < 2:
        raise ValueError("Response too short to contain length header.")

    # Read the length from the first 2 bytes
    length = int.from_bytes(response_data[:2], byteorder='big')
    iso_data = response_data[2:2+length]

    # Attempt to parse as ISO 8583
    iso_resp = ISO8583()
    iso_resp.set_network_iso(iso_data)
    return iso_resp

def main():
    # Adjust these values for your environment:
    proxy_host = '127.0.0.1'
    proxy_port = 9050  # Example: Tor SOCKS proxy or another local SOCKS proxy
    target_host = '192.168.1.100'
    target_port = 5050  # Commonly used for ISO 8583 in some setups

    try:
        # 1. Connect via SOCKS proxy
        sock = connect_through_socks(proxy_host, proxy_port, target_host, target_port)
        print(f"[+] Connected to {target_host}:{target_port} via {proxy_host}:{proxy_port}")

        # 2. Send a minimal ISO 8583 ping (0800)
        response_data = send_iso8583_ping(sock)
        print(f"[+] Raw response (hex): {response_data.hex()}")

        # 3. Parse the response
        iso_resp = parse_iso8583_response(response_data)
        mti = iso_resp.get_mti()
        print(f"[+] Received MTI: {mti}")
        
        if mti == '0810':
            print("[+] The response is a valid ISO 8583 0810 (network management response).")
        else:
            print("[!] The response MTI is not 0810; it may be a different ISO message or not ISO at all.")

        # Optional: Print some fields if present
        for bit_pos in range(2, 129):
            if iso_resp.get_bit(bit_pos):
                print(f"    Field {bit_pos}: {iso_resp.get_bit(bit_pos)}")

        sock.close()

    except (socket.error, InvalidIso8583Error, IsoFieldError, ValueError) as e:
        print(f"[!] Error during ISO 8583 test: {e}")

if __name__ == '_main_':
    main()