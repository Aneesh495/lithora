"""Shared HTTP/TLS helper for data acquisition.

Some environments (corporate proxies, TLS-inspecting gateways) present a
root certificate that is trusted by the operating system keychain but not by
Python's bundled certificate store. Rather than disable verification (which
would silently accept any certificate), we prefer the operating system trust
store via ``truststore`` when it is available, and fall back to the default
verifying context otherwise. Verification is never turned off.
"""

from __future__ import annotations

import ssl
import urllib.request


def make_ssl_context() -> ssl.SSLContext:
    """Return a verifying SSL context, preferring the OS trust store.

    ``truststore`` injects the operating system's trusted roots, which covers
    proxy or enterprise CAs that are trusted by the machine but absent from
    Python's bundled roots. If it is not installed we use the standard
    verifying context, which is correct on machines without an intercepting
    proxy.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


def open_url(url: str, timeout_s: float = 60.0):
    """Open a URL with the preferred SSL context and a research user agent."""
    req = urllib.request.Request(url, headers={"User-Agent": "lithora/0.1 (research)"})
    ctx = make_ssl_context()
    return urllib.request.urlopen(req, timeout=timeout_s, context=ctx)
