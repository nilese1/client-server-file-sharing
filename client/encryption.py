

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as symPadding
from cryptography.hazmat.backends import default_backend



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
    print(f'Client Public Key: {public_key}')
    return private_key, public_key, public_key.public_numbers()

def generate_symmetric_key(key, init_vector):
    symmetric = Cipher(algorithms.AES(key), modes.CBC(init_vector), backend=default_backend())
    return symmetric

def encrypt_data(plaintext, public_key_server):
    print(f"public_key_server Type: {type(public_key_server)}")

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

def symmetric_encrypt(plaintext, symmetric_key):
    encryptor = symmetric_key.encryptor()
    padder = symPadding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    return ciphertext

def symmetric_decrypt(ciphertext, symmetric_key):
    decryptor = symmetric_key.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = symPadding.PKCS7(128).unpadder()
    unpadded_data = unpadder.update(plaintext) + unpadder.finalize()
    return unpadded_data

# private, public, nums = generate_keys()
#
# message = b"Hello World!"
# message2 = b"The quick brown fox"
#
# cipher = encrypt_data(message, public)
# cipher2 = encrypt_data(message2, public)
#
# print(f"Here is encrypted1: {cipher}")
# print(f"Here is encrypted2: {cipher2}")
#
# plain = decrypt_data(cipher, private)
#
# print(f"Here is decrypted: {plain}")
#
# plain2 = decrypt_data(cipher2, private)
#
# print(f"Here is decrypted: {plain2}")