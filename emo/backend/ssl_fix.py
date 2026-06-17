"""Utilise les certificats SSL Windows (fix CERTIFICATE_VERIFY_FAILED)."""
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    import os
    try:
        import certifi
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except ImportError:
        pass
