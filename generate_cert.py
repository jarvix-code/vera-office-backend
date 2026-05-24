#!/usr/bin/env python3
"""
Generate self-signed certificate with IP SAN for VERA Office
"""
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime
import ipaddress

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# Certificate details
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "VERA Office"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "VERA"),
])

# Create certificate with IP SANs
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(private_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))  # 10 years
    .add_extension(
        x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.IPv4Address("192.168.178.44")),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.DNSName("localhost"),
            x509.DNSName("vera-office.local"),
        ]),
        critical=False,
    )
    .sign(private_key, hashes.SHA256(), default_backend())
)

# Write private key
with open("certs/vera.key", "wb") as f:
    f.write(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

# Write certificate
with open("certs/vera.crt", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("✓ Certificate generated:")
print("  - certs/vera.crt")
print("  - certs/vera.key")
print("  - Valid for: 192.168.178.44, 127.0.0.1, localhost, vera-office.local")
print("  - Expires: 2036-03-26")
