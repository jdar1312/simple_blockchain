
#helper functions for zimcoin blockchain

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives import serialization

#--------------------------------------------
##### BLOCKCHAIN HELPER FUNCTIONS #####
#--------------------------------------------

def pk_serialize(public_key, encode_type = 'ser'):
    '''
    Encode/decode a public key via DER (Distinguished Encoding Rules) serialization/deserialization

    PARAMETERS:
    public_key - public key to encode/decode
    encode_type - 'ser' for serialization, 'des' for deserialization

    OUTPUT:
    encoded/decoded public key
    '''
    assert encode_type in ['ser', 'des'], 'encode_type must be ser or des'

    #encode public key in bytes via serialization
    if encode_type == 'ser':
        if type(public_key) == bytes:
            mod_public_key = public_key
        else:
            mod_public_key = public_key.public_bytes(encoding=serialization.Encoding.DER,format=serialization.PublicFormat.SubjectPublicKeyInfo)
    
    #decode public key via deserialization
    elif encode_type == 'des':
        if type(public_key) == bytes:
            mod_public_key = serialization.load_der_public_key(public_key)
        else:
            mod_public_key = public_key  
    
    return mod_public_key

#----------------------------------------------------------------------

def generate_address(public_key):
    '''
    Generate the address of a user as the SHA1 of their public key.

    PARAMETERS:
    public_key (unencoded or in bytes) - user public key

    OUTPUT:
    SHA1 hash (bytes) of public key
    '''

    #encode public key
    encoded_public_key = pk_serialize(public_key, encode_type = 'ser')

    #generate address
    address_digest = hashes.Hash(hashes.SHA1())
    address_digest.update(encoded_public_key)
    address_hash = address_digest.finalize()

    return address_hash

#----------------------------------------------------------------------

def sha256_hash(message_components: list, finalize = True):
    '''
    Generate the SHA256 hash of a message.

    PARAMETERS:
    message_components (list) - list of components to be added to the digest (in bytes)
    finalize - True to return full hash; False to return unfinalized digest

    OUTPUT:
    SHA256 hash (bytes) of message components
    '''

    digest = hashes.Hash(hashes.SHA256())

    #if component is an integer it is converted to bytes of length 8 via little endian encoding
    for e in message_components:
        assert type(e) == bytes, f'{e} must be of type bytes'
        digest.update(e)
    
    if finalize: 
        msg_hash = digest.finalize() 
        return msg_hash
    else:
        return digest


#----------------------------------------------------------------------

def generate_signature(sender_secret_key, recipient_hash, amount, fee, nonce):
    '''
    Generate transaction message SHA256 hash and sign with sender's secret key.

    PARAMETERS:
    sender_secret_key (bytes) - elliptic curve (secp256k1) secret key of sender
    recipient_hash (bytes) - recipient address (SHA1 hash of recipient's public key)
    amount (int) - transaction amount
    fee (int) - transaction fee
    nonce (int) - transaction sequence number

    OUTPUT:
    Signature (bytes) of message with sender's secret key   
    '''

    #produce SHA256 hash of transaction message
    msg_hash = sha256_hash([recipient_hash, amount.to_bytes(8,'little'), fee.to_bytes(8,'little'), nonce.to_bytes(8,'little')])

    #generate ECDSA signature of prehashed message using sender's secret key
    signature = sender_secret_key.sign(msg_hash, ec.ECDSA(utils.Prehashed(hashes.SHA256()))) 

    return signature