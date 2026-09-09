"""
FleetMind — SSRF-Hardened Deep Reader Tool
-------------------------------------------
Provides secure web page reading capabilities with strict protections against
Server-Side Request Forgery (SSRF) attacks targeting internal services,
loopback addresses, cloud metadata endpoints, or non-HTTP schemes.
"""

import logging
import socket
import urllib.parse
import ipaddress
import httpx
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

# List of blocked IP networks (RFC 1918, RFC 3927, Loopback, Cloud Metadata)
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # IPv4 Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / AWS Metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/32"),       # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
]


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address string resolves to a blocked or internal network."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
        for net in BLOCKED_IP_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        # Invalid IP string → block by default for safety
        return True


def validate_url_for_ssrf(url_str: str) -> tuple[bool, str]:
    """
    Validate a URL against SSRF vulnerabilities.

    Returns:
        tuple[bool, str]: (is_valid, error_reason_or_ok)
    """
    if not url_str or not isinstance(url_str, str):
        return False, "URL must be a non-empty string."

    url_str = url_str.strip()

    try:
        parsed = urllib.parse.urlparse(url_str)
    except Exception as e:
        return False, f"URL parsing error: {e}"

    # 1. Scheme Check
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Blocked scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."

    # 2. Hostname Check
    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid URL: missing hostname."

    hostname_lower = hostname.lower()

    if hostname_lower in ("localhost", "localhost.localdomain") or hostname_lower.endswith(".local"):
        return False, f"Access to local hostname '{hostname}' is blocked."

    # 3. Direct IP Check (e.g. http://127.0.0.1/ or http://169.254.169.254/)
    if is_ip_blocked(hostname_lower) == True and not any(c.isalpha() for c in hostname_lower):
        return False, f"Security Violation: Access to IP '{hostname}' is blocked."

    # 4. Hostname Resolution Check (DNS Rebinding / Internal IP resolution)
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for family, socktype, proto, canonname, sockaddr in addr_info:
            resolved_ip = sockaddr[0]
            if is_ip_blocked(resolved_ip):
                return False, f"Security Violation: Target host '{hostname}' resolves to blocked IP '{resolved_ip}'."
    except socket.gaierror:
        # In offline/sandbox environments DNS resolution may fail for external domains.
        # If hostname is not a direct IP or localhost, allow it so HTTP client handles connection error.
        pass
    except Exception as e:
        return False, f"DNS resolution error: {e}"

    return True, "OK"


def deep_read_url(url: str) -> str:
    """
    Safely fetch and read a web page URL with SSRF protections and a 5s timeout.
    """
    is_valid, reason = validate_url_for_ssrf(url)
    if not is_valid:
        logger.warning(f"SSRF blocked request to '{url}': {reason}")
        return f"🚫 Blocked: {reason}"

    try:
        # Strict 5-second timeout, no automatic redirects to prevent redirect-based SSRF
        with httpx.Client(timeout=5.0, follow_redirects=False) as client:
            resp = client.get(url, headers={"User-Agent": "FleetMind-Agent/1.0"})
            
            if resp.status_code in (301, 302, 303, 307, 308):
                redirect_url = resp.headers.get("location", "")
                if redirect_url:
                    full_redirect_url = urllib.parse.urljoin(url, redirect_url)
                    is_red_valid, red_reason = validate_url_for_ssrf(full_redirect_url)
                    if not is_red_valid:
                        return f"🚫 Redirect Blocked: {red_reason}"
                    # Re-fetch redirect target safely
                    resp = client.get(full_redirect_url, headers={"User-Agent": "FleetMind-Agent/1.0"})

            resp.raise_for_status()
            text = resp.text[:2000]  # Return first 2KB snippet
            return f"Content from {url}:\n{text}"
    except httpx.TimeoutException:
        return f"⏱️ Error reading {url}: Request timed out (5s limit)."
    except Exception as e:
        return f"Error reading {url}: {str(e)}"


def get_reader_tools() -> list[Tool]:
    """Return the SSRF-hardened deep reader tool."""
    return [
        Tool(
            name="deep_read_url",
            func=deep_read_url,
            description=(
                "Deep read the content of a web page URL safely."
                " Input: a full HTTP/HTTPS URL."
                " Returns the text content of the page."
            ),
        )
    ]
