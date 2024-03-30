#creates and updates user states and blocks for the zimcoin blockchain

from blockchain_utils import *
from collections import defaultdict
from itertools import count
import copy
from time import time

#--------------------------------------------
##### USER STATE CLASS #####
#--------------------------------------------

class UserState:
    '''
    Defines the UserState class. 

    METHODS:
    1. constructor function
    2. earn method to updated user balance with earned coins
    3. spend method to updated user balance and nonce when making transactions
    '''
    
    def __init__(self, balance, nonce): 
        '''
        Constructor method for the UserState class.

        PARAMETERS:
        balance (int) - balance that the user has on the chain
        nonce (int) - increments by 1 each time user sends a transaction
        '''

        self.balance = balance
        self.nonce = nonce

    def earn(self, amount, undo = False):
            '''
            Updates user balance with earned amount.

            PARAMETERS:
            amount (int) - amount of coins earned
            undo - set to True to undo transaction

            RETURNS
            updated user balance           
            '''

            if not undo:
                updated_balance = self.balance + amount
            else:
                updated_balance = self.balance - amount

            return updated_balance
    
    def spend(self, amount, undo = False):
            '''
            Updates user balance with spent amount and increments nonce by one.

            PARAMETERS:
            amount (int) - amount of coins spent
            undo - set to True to undo transaction

            RETURNS
            updated user balance and updated user nonce           
            '''

            if not undo:
                updated_balance = self.balance - amount
                updated_nonce = self.nonce + 1 
            else:
                updated_balance = self.balance + amount
                updated_nonce = self.nonce - 1 

            return updated_balance, updated_nonce

#--------------------------------------------
##### BLOCK CLASS #####
#--------------------------------------------

class Block:
    '''
    Defines the Block class. 

    METHODS:
    1. constructor function
    2. update_states function to update user states
    3. verify_and_get_changes function to verify the block metadata and return updated user states if valid
    4. get_changes_for_undo to undo changes to the user state by block
    '''

    def __init__(self, previous, height, miner, transactions, timestamp, difficulty, block_id, nonce):
        '''
        Constructor method for the Block class.

        PARAMETERS:
        previous (bytes or int) - block id of the block before this one in the block chain (zero for first block)
        height (int) - number of blocks before this one in the chain (zero for first block)
        miner (bytes) - public key hash of the user responsible for mining the block
        transactions (list) - list containing the transactions contained within the block
        timestamp (0< int < (2**64)-1) - UNIX time counting the number of seconds since 1st January 1970
        difficulty (0< int < (2**128)-1)  - difficulty of the proof of work needed to mine the block (average amount of hashes that must be computed to mine a block)
        block_id (32 bytes) - ID hash of the block
        nonce (0< int < (2**64)-1) - proof of work solution
        '''

        self.previous = previous
        self.height = height
        self.miner = miner
        self.transactions = transactions
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.block_id = block_id
        self.nonce = nonce

    def update_states(self,  previous_user_states: dict, mining_reward = 10000):
            '''
            Updates user states dictionary with new transactions.

            PARAMETERS:
            previous_user_states (dict) - dictionary of starting user states; k = public key hash of users, v = UserState object corresponding to user
            mining_reward (int) - coin reward for node mining the block

            RETURNS:
            dictionary of updated user states
            '''
            
            #create updated_user_states dict as copy of previous_user_states (so as not to overwrite old states)
            updated_user_states = defaultdict(lambda: UserState(0,-1), previous_user_states) 
                #default value is an intial state with balance = 0 and nonce = -1 (set when called user does not exist in dict)

            #miner reward
            updated_user_states[self.miner].balance = updated_user_states[self.miner].earn(mining_reward)

            #updated user states with each transaction
            for t in self.transactions:
                #verify transaction before updating states
                sender_balance = updated_user_states[t.sender_hash].balance 
                sender_previous_nonce = updated_user_states[t.sender_hash].nonce 
                assert t.verify(sender_balance, sender_previous_nonce)

                #miner fee
                updated_user_states[self.miner].balance = updated_user_states[self.miner].earn(t.fee)

                #update spender state
                updated_user_states[t.sender_hash].balance, updated_user_states[t.sender_hash].nonce = updated_user_states[t.sender_hash].spend(t.amount)

                #update recipient state
                updated_user_states[t.recipient_hash].balance = updated_user_states[t.recipient_hash].earn(t.amount - t.fee)

            return updated_user_states
        

    def verify_and_get_changes(self, difficulty, previous_user_states: dict):
        '''
        Verify block metadata and update user states with block transactions.

        PARAMETERS:
        difficulty (0< int < (2**128)-1) - difficulty of the proof of work needed to mine this block
        previous_user_states (dict) - dictionary with k = public key hash of users and v = UserState object corresponding to user

        RETURNS:
        dictionary of updated user states
        '''

        try:
            #verify difficulty
            assert self.difficulty == difficulty, 'Incorrect difficulty - difficulty of block should match the difficulty argument'

            #verify block_id
            transaction_ids = b''.join([t.txid for t in self.transactions])
            assert self.block_id == sha256_hash([self.previous, self.miner, transaction_ids, self.timestamp.to_bytes(8,'little'), difficulty.to_bytes(16,'little'), self.nonce.to_bytes(8,'little')]), 'Block ID does not correspond to the SHA256 hash of the block header components: previous, miner, transaction_ids, timestamp, difficulty, nonce'

            #verify transactions list
            assert len(self.transactions) <= 25, 'Block can only contain at most 25 transactions'

            #verify miner hash
            assert len(self.miner) == 20, 'Miner hash should be 20 bytes long'

            #verify proof-of-work
            assert int.from_bytes(self.block_id, "big") <= (2**256)/self.difficulty, 'Invalid proof of work - block ID should be small enough to match block difficulty'

            #update user states
            updated_user_states = self.update_states(previous_user_states) 

            #print(f'Block Verification succesful!')

            return updated_user_states          

        except AssertionError as e:
            print(f'Block Verification error: {e}')
            raise
                   

    def get_changes_for_undo(self, user_states_after: dict, mining_reward = 10000):
        '''
        Undo the changes to user states from block transactions. Verification not required.

        PARAMETERS:
        user_user_states (dict) - dictionary with k = public key hash of users and v = UserState object corresponding to user (after they have been updated with block transactions)
        mining_reward (int) - coin reward for node mining the block

        RETURNS:
        dictionary of user states with changes undone
        '''            

        #create undone_user_states dict as copy of user_states_after (use deepcopy as .copy() also manipulates original dict)
        undone_user_states = copy.deepcopy(user_states_after) 
        #miner reward
        undone_user_states[self.miner].balance = undone_user_states[self.miner].earn(mining_reward, undo = True)

        #updated user states with each transaction
        for t in self.transactions:

            #miner fee
            undone_user_states[self.miner].balance = undone_user_states[self.miner].earn(t.fee, undo = True)

            #update spender state
            undone_user_states[t.sender_hash].balance, undone_user_states[t.sender_hash].nonce = undone_user_states[t.sender_hash].spend(t.amount, undo = True)

            #update recipient state
            undone_user_states[t.recipient_hash].balance = undone_user_states[t.recipient_hash].earn(t.amount - t.fee, undo = True)

        return undone_user_states
     

#--------------------------------------------
##### BLOCK MINING FUNCTIONS #####
#--------------------------------------------       

def puzzle_solver(block_description, target):
    '''
    Find a nonce that when hashed to block_description produces a hash less than or equal to the target. 

    PARAMETERS:
    block_description (digest) - digest of the block attributes: previous, miner, transaction_ids, timestamp, difficulty
    target (int) - puzzle target

    OUTPUT:
    Nonce (int) that solves puzzle  
    '''

    for candidate_nonce in count():
        #itertools.count() generates an infinite sequence of integers starting from 0

        candidate_digest = block_description.copy()
        candidate_digest.update(candidate_nonce.to_bytes(8, 'little'))
        candidate_solution = candidate_digest.finalize()

        if int.from_bytes(candidate_solution, "big") <= target:
            #for puzzle solving the candidate block id is encoded as a big endian integer
            break
    
    return candidate_nonce

#----------------------------------------------------------------------

def mine_block(previous, height, miner, transactions, timestamp, difficulty, hashrate = time() + 100):
    '''

    PARAMETERS:
    previous (bytes or int) - block id of the previous block
    height (int) - block height
    miner (bytes) - public key hash of the miner 
    transactions (list) -  list of the transactions to be included
    timestamp (0< int < (2**64)-1) - UNIX time counting the number of seconds since 1st January 1970
    difficulty (0< int < (2**128)-1) - difficulty of the proof of work needed to mine the block (average amount of hashes that must be computed to mine a block)
    hashrate (int) - mining speed
    '''

    #generate block description
    transaction_ids = b''.join([t.txid for t in transactions]) #concatenate transaction id's (bytes) in block
    block_description = sha256_hash([previous, miner, transaction_ids, timestamp.to_bytes(8,'little'), difficulty.to_bytes(16,'little')], finalize = False) #return the description digest

    #proof-of-work 
    target = (2**256)/difficulty
    nonce = puzzle_solver(block_description, target)

    #combine nonce solution with block description to form block id
    block_id = sha256_hash([previous, miner, transaction_ids, timestamp.to_bytes(8,'little'), difficulty.to_bytes(16,'little'), nonce.to_bytes(8,'little')])

    #create Block instance
    block = Block(previous, height, miner, transactions, timestamp, difficulty, block_id, nonce)

    return block
