"""
VERA Office - SSL Certificate Setup
Generates self-signed SSL certificates for HTTPS on first run.
"""
from pathlib import Path
from loguru import logger


def ensure_ssl_certs(base_dir: Path = None) -> tuple:
    """
    Ensure SSL certificate and key exist. Generate self-signed if missing.
    
    Args:
        base_dir: Base directory of the application. Defaults to project root.
    
    Returns:
        Tuple of (cert_path, key_path)
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent
    
    ssl_dir = base_dir / "keys" / "ssl"
    ssl_dir.mkdir(parents=True, exist_ok=True)
    
    cert_path = ssl_dir / "cert.pem"
    key_path = ssl_dir / "key.pem"
    
    if cert_path.exists() and key_path.exists():
        logger.info(f"SSL certificates found: {ssl_dir}")
        return str(cert_path), str(key_path)
    
    logger.info("Generating self-signed SSL certificate...")
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        import socket
        
        # Generate RSA key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Get hostname for SAN
        hostname = socket.gethostname()
        
        # Build certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "VERA Office"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])
        
        san_names = [
            x509.DNSName("localhost"),
            x509.DNSName(hostname),
            x509.DNSName("vera-office.local"),
            x509.IPAddress(__import__("ipaddress").IPv4Address("127.0.0.1")),
        ]
        
        # Try to add local IP
        try:
            local_ip = socket.gethostbyname(hostname)
            if local_ip != "127.0.0.1":
                san_names.append(
                    x509.IPAddress(__import__("ipaddress").IPv4Address(local_ip))
                )
        except Exception:
            pass
        
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName(san_names),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )
        
        # Write key
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        
        # Write cert
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        logger.success(f"SSL certificate generated: {ssl_dir}")
        return str(cert_path), str(key_path)
        
    except ImportError:
        logger.error("cryptography package not installed! Cannot generate SSL certs.")
        raise
    except Exception as e:
        logger.error(f"Failed to generate SSL certificate: {e}")
        raise
