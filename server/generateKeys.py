from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def generate_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    public_key = private_key.public_key()

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_key, public_key, public_key.public_numbers()

def encrypt_data(plaintext, public_key_server):
    ciphertext = public_key_server.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

def decrypt_data(ciphertext, private_key_client):
    plaintext = private_key_client.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext




# from cryptography import x509
# from cryptography.x509.oid import NameOID
# from cryptography.hazmat.primitives import serialization
# from cryptography.hazmat.primitives.asymmetric import rsa
# from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.backends import default_backend
# import datetime
#
# # Generate private key
# key = rsa.generate_private_key(
#     public_exponent=65537,
#     key_size=2048,
#     backend=default_backend()
# )
#
# # Write private key to file
# with open("server.key", "wb") as f:
#     f.write(key.private_bytes(
#         encoding=serialization.Encoding.PEM,
#         format=serialization.PrivateFormat.TraditionalOpenSSL,
#         encryption_algorithm=serialization.NoEncryption()
#     ))
#
# # Generate a self-signed certificate
# subject = issuer = x509.Name([
#     x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
#     x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
#     x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
#     x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Company"),
#     x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
# ])
# cert = x509.CertificateBuilder().subject_name(
#     subject
# ).issuer_name(
#     issuer
# ).public_key(
#     key.public_key()
# ).serial_number(
#     x509.random_serial_number()
# ).not_valid_before(
#     datetime.datetime.utcnow()
# ).not_valid_after(
#     datetime.datetime.utcnow() + datetime.timedelta(days=365)
# ).add_extension(
#     x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
#     critical=False,
# ).sign(key, hashes.SHA256(), default_backend())
#
# # Write certificate to file
# with open("server.crt", "wb") as f:
#     f.write(cert.public_bytes(serialization.Encoding.PEM))
