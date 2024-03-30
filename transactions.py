#creates transactions for the zimcoin blockchain

from blockchain_utils import *
from cryptography.exceptions import InvalidSignature

#--------------------------------------------
##### TRANSACTIONS CLASS #####
#--------------------------------------------

class Transaction:
    '''
    Defines the Transaction class. 

    METHODS:
    1. constructor function
    2. verify function to verify the transaction data
    '''

    def __init__(self, sender_hash, recipient_hash, sender_public_key, amount, fee, nonce, signature, txid): 
        '''
        The constructor method for the Transaction class. The parameters are used to set the attributes of the class instance.

        PARAMETERS:
        sender_hash (20 bytes) - SHA1 hash of sender's public key (i.e. sender address)
        recipient_hash (20 bytes) - SHA1 hash of recipient's public key (i.e. receiver address)
        sender_public_key (unencoded or ~ 90 bytes) - elliptic curve (secp256k1) public key generated from sender's secret key
        amount (int) - amount to be transferred
        fee (int) - transaction fee
        nonce (int) - sender transaction sequence number
        signature (~70 bytes) - ECDSA-signed SHA256 hash of transaction metadata by sender secret key 
        txid (32 bytes) - SHA256 hash of transaction metadata and signature
        '''

        #defining the class instance attributes
        self.sender_hash = sender_hash #self = referring to the object instance itself; .sender_hash = object attribute
        self.recipient_hash = recipient_hash
        self.sender_public_key = sender_public_key
        self.amount = amount
        self.fee = fee
        self.nonce = nonce
        self.signature = signature
        self.txid = txid


    def verify(self, sender_balance, sender_previous_nonce):
        '''
        Verifies a transaction by performing a number of checks:

        - sender_hash and recipient_hash should both be 20 bytes long
        - sender_hash should be the SHA1 hash of sender_public_key
        - amount should be a whole number between 1 and sender_balance inclusive
        - fee should be a whole number between 0 and amount inclusive
        - nonce should be sender_previous_nonce + 1
        - txid should be the the hash of the other fields in Transaction 
        - signature should be a valid signature, as described below
        
        PARAMETERS:
        sender_balance (int) - spender funds available to spend
        sender_previous_nonce (int) - nonce from previoius transaction by the spender

        '''
        try:
            #verify sender hash
            assert len(self.sender_hash) == 20, 'Sender hash should should be 20 bytes long'
            assert self.sender_hash == generate_address(self.sender_public_key), 'Sender hash be SHA1 hash of sender public key'

            #verify recipient hash
            assert len(self.recipient_hash) == 20, 'Recipient hash should should be 20 bytes long'

            #verify amount
            assert self.amount % 1 == 0, f'Amount ({self.amount}) should be whole number' 
            assert (self.amount > 0) and (self.amount <= (sender_balance)), f'Balance too small - amount ({self.amount}) should be positive and at most equal to sender_balance ({sender_balance})'

            #verify fee
            assert self.fee % 1 == 0 , f'Fee ({self.fee}) should be whole number' 
            assert (self.fee >= 0) and (self.fee <= self.amount), f'Fee ({self.fee}) should range between zero and amount'

            #verify nonce
            assert self.nonce == sender_previous_nonce + 1, f'Invalid nonce - current nonce ({self.nonce}) should be previous nonce ({sender_previous_nonce}) incremented by 1'

            #verify txid
            assert self.txid == sha256_hash([self.sender_hash, self.recipient_hash, pk_serialize(self.sender_public_key), self.amount.to_bytes(8,'little'), self.fee.to_bytes(8,'little'), self.nonce.to_bytes(8,'little'), self.signature]), 'Transaction ID does not correspond to the hash of the transaction components: sender hash, recipient hash, sender public key, amount, fee, nonce, signature'

            #verify signature

            #generate a hash of the message supposed to have been signed 
            msg_hash = sha256_hash([self.recipient_hash, self.amount.to_bytes(8,'little'), self.fee.to_bytes(8,'little'), self.nonce.to_bytes(8,'little')])
            #deserialize public key
            decoded_public_key = pk_serialize(self.sender_public_key, encode_type = 'des')
            #verify that ECDSA signature was signed with sender's secret key on the hashed message by unlocking with the sender's public key
            decoded_public_key.verify(self.signature, msg_hash, ec.ECDSA(utils.Prehashed(hashes.SHA256()))), 'Invalid Signature'
            
            #print(f'Transaction {self.txid.hex()} succesfully created')

            return True
            
        except AssertionError as e:
            print(f'Transaction {self.txid.hex()} unsuccesful: {e}')
            raise #throw AssertionError exception (break the code runtime)

        except InvalidSignature:
            print(f'Transaction {self.txid.hex()} unsuccesful: Invalid Signature')
            raise

#--------------------------------------------
##### CREATE TRANSACTION FUNCTION #####
#--------------------------------------------
        
def create_signed_transaction(sender_secret_key, recipient_hash, amount, fee, nonce):
    '''
    Generate a Transaction instance.

    PARAMETERS:
    sender_secret_key (bytes) - elliptic curve (secp256k1) secret key of sender
    recipient_hash (bytes) - recipient address (SHA1 hash of recipient's public key)
    amount (int) - transaction amount
    fee (int) - transaction fee
    nonce (int) - sender transaction sequence number
    '''

    #generate sender public key from elliptic curve secret key 
    sender_public_key = sender_secret_key.public_key()
    #generate sender address (sha1 hash of public key)
    sender_hash = generate_address(sender_public_key)

    #sign transaction message with sender's secret key
    signature = generate_signature(sender_secret_key, recipient_hash, amount, fee, nonce)

    #generate transaction id 
    txid = sha256_hash([sender_hash, recipient_hash, pk_serialize(sender_public_key), amount.to_bytes(8,'little'), fee.to_bytes(8,'little'), nonce.to_bytes(8,'little'), signature]) #public_key is serialized prior to hashing

    #create Transaction instance
    transaction = Transaction(sender_hash, recipient_hash, sender_public_key, amount, fee, nonce, signature, txid)

    return transaction
