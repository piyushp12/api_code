import requests
import socket
import json
import whois
import os
import random
import threading
import time
from scapy.all import IP, ICMP, UDP, sr1
from requests.exceptions import RequestException

def get_proxies():
    """Retrieve proxy list from a proxy provider or local config."""
    return [
        "http://45.77.201.142:8080",
        "http://103.75.196.121:3128",
        "http://116.202.1.177:1080"
    ]

def get_random_proxy():
    """Select a random proxy from the list."""
    proxy = random.choice(get_proxies())
    return {"http": proxy, "https": proxy}

def get_bank_ip_ranges(bank_name):
    """Fetch ASN & IP ranges of the bank using BGPView API."""
    print(f"[🔎] Fetching ASN info for {bank_name}...")
    url = f"https://api.bgpview.io/search?query_term={bank_name}"
    try:
        response = requests.get(url, timeout=10).json()
    except requests.exceptions.RequestException as e:
        print(f"[❌] Error fetching ASN info: {e}")
        return []
    
    ip_ranges = []
    if "data" in response and "autonomous_systems" in response["data"]:
        for asn in response["data"]["autonomous_systems"]:
            print(f" - ASN: {asn['asn']} ({asn['name']})")
            asn_url = f"https://api.bgpview.io/asn/{asn['asn']}/prefixes"
            try:
                ip_data = requests.get(asn_url, timeout=10).json()
                for prefix in ip_data.get("data", {}).get("ipv4_prefixes", []):
                    ip_ranges.append(prefix['prefix'])
                    print(f"   - IP Range: {prefix['prefix']}")
            except requests.exceptions.RequestException as e:
                print(f"[❌] Error fetching IP ranges: {e}")
    return ip_ranges

def find_subdomains(domain):
    """Find subdomains related to the bank's domain using crt.sh."""
    print(f"[🔎] Finding subdomains for {domain}...")
    url = f"https://crt.sh/?q={domain}&output=json"
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.get(url, headers=headers, timeout=10000)
            if response.status_code == 200:
                return set(entry["name_value"] for entry in response.json())
            print(f"Retrying {attempt + 1}/3...")
            time.sleep(3)  # Wait before retrying
        except (RequestException, json.JSONDecodeError) as e:
            print(f"[❌] Failed attempt {attempt + 1}: {e}")
    return set()

def resolve_subdomains(subdomains):
    """Resolve a set of subdomains to IP addresses."""
    resolved_ips = set()
    for sub in subdomains:
        try:
            ip = socket.gethostbyname(sub)
            print(f"[🔎] {sub} resolved to {ip}")
            resolved_ips.add(ip)
        except socket.gaierror:
            print(f"[❌] Could not resolve {sub}")
    return list(resolved_ips)

def scan_iso8583_ports(ip):
    """Scan for ISO 8583 (financial messaging) ports on discovered IPs."""
    print(f"[🔎] Scanning {ip} for ISO 8583 ports...")
    # Example TCP port(s); adjust as needed
    common_ports = [5050]
    open_ports = []
    
    def check_port(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        if sock.connect_ex((ip, port)) == 0:
            print(f" ✅ Open Port Found (ISO8583): {port}")
            open_ports.append(port)
        sock.close()
    
    threads = [threading.Thread(target=check_port, args=(port,)) for port in common_ports]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    return open_ports

def scan_vpn_ports(ip):
    """
    Scan for VPN-related ports on the target IP.
    Checks both TCP and UDP ports.
    Common TCP ports: 443, 5050, 6000, 7000, 8443 (e.g., SSL VPN)
    Common UDP ports: 500 (IPsec/IKE), 4500 (NAT-T), 1701 (L2TP)
    """
    print(f"[🔎] Scanning {ip} for VPN endpoints...")
    tcp_ports = [443, 5050, 6000, 7000, 8443]
    udp_ports = [500, 4500, 1701]
    open_tcp = []
    open_udp = {}

    # TCP scan using threads
    def check_tcp_port(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        if sock.connect_ex((ip, port)) == 0:
            print(f" ✅ Open TCP Port Found (VPN): {port}")
            open_tcp.append(port)
        sock.close()

    # UDP scan using Scapy
    def check_udp_port(port):
        pkt = IP(dst=ip)/UDP(dport=port)/b'Hello'
        reply = sr1(pkt, timeout=2, verbose=False)
        # In UDP scanning, no reply can mean open|filtered.
        if reply is None:
            print(f" ⚠ UDP Port {port} is open|filtered (no response)")
            open_udp[port] = "open|filtered"
        elif reply.haslayer(ICMP):
            # ICMP unreachable often indicates a closed port.
            print(f" ❌ UDP Port {port} is closed (ICMP response)")
            open_udp[port] = "closed"
        else:
            print(f" ✅ Open UDP Port Found (VPN): {port}")
            open_udp[port] = "open"

    threads = []
    # Launch TCP port checks
    for port in tcp_ports:
        t = threading.Thread(target=check_tcp_port, args=(port,))
        t.start()
        threads.append(t)
    # Launch UDP port checks
    for port in udp_ports:
        t = threading.Thread(target=check_udp_port, args=(port,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    
    return {"tcp": open_tcp, "udp": open_udp}

def trace_route(target_ip):
    """Traceroute to detect network path and possible VPN tunnel hops."""
    print(f"[🔎] Tracing route to {target_ip}...")
    route = []
    for ttl in range(1, 30):
        pkt = IP(dst=target_ip, ttl=ttl) / ICMP()
        reply = sr1(pkt, verbose=False, timeout=2)
        if reply is None:
            break
        route.append(reply.src)
        print(f" {ttl}: {reply.src}")
        if reply.src == target_ip:
            print("[✅] Reached target!")
            break
    return route

def discover_atm_vpn_with_dns(bank_name, domain):
    """
    Main function to run the discovery process for ATM-to-bank VPN endpoints.
    It gathers IP ranges via ASN lookup (if available), finds subdomains,
    resolves subdomains to IPs, and scans each IP for both ISO8583 ports and VPN-related ports.
    It also performs traceroute analysis.
    """
    ip_ranges = get_bank_ip_ranges(bank_name)
    subdomains = find_subdomains(domain)
    resolved_ips = resolve_subdomains(subdomains)
    results = {
        "bank": bank_name,
        "ip_ranges": ip_ranges,
        "subdomains": list(subdomains),
        "resolved_ips": resolved_ips,
        "scans": []
    }
    
    for ip in resolved_ips:
        print(f"\n[🔎] Processing IP: {ip}")
        iso8583_open = scan_iso8583_ports(ip)
        vpn_scan = scan_vpn_ports(ip)
        # Only run traceroute if any VPN port is open or open|filtered.
        if vpn_scan["tcp"] or any(status == "open" or status == "open|filtered" for status in vpn_scan["udp"].values()):
            trace = trace_route(ip)
        else:
            trace = []
        results["scans"].append({
            "ip": ip,
            "iso8583_ports": iso8583_open,
            "vpn_scan": vpn_scan,
            "trace": trace
        })
    
    with open("atm_vpn_discovery_results_with_dns.json", "w") as f:
        json.dump(results, f, indent=4)
    print("[✅] Discovery complete. Results saved.")

# Example usage:
if __name__ == "__main__":
    bank_name = "BBVA"
    domain = "www.bbva.pe"
    discover_atm_vpn_with_dns(bank_name, domain)