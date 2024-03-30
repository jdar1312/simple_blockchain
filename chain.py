#updates blockchain state for the zimcoin blockchain

from blocks import *
import copy

#--------------------------------------------
##### BLOCKCHAIN STATE CLASS #####
#--------------------------------------------

class BlockchainState:
    '''
    Defines the Blockchain State class. 

    METHODS:
    1. constructor function
    2. calculate_difficulty function
    3. verify_and_apply_block function to add block to chain if valid
    4. undo_last_block function to remove last block in cases of reorgs

    '''

    def __init__(self, longest_chain, user_states, total_difficulty):
        '''
        Constructor method for the Blockchain State class.

        PARAMETERS:
        longest_chain (list) - list of blocks
        user states (dict) - dictionary of user states at the end of the longest chain; k = public key hash of users, v = UserState object corresponding to user
        total_difficulty (int) -  sum of the difficulties of all of the blocks in the longest chain

        '''

        self.longest_chain = longest_chain
        self.user_states = user_states
        self.total_difficulty = total_difficulty

    def calculate_difficulty(self):
        '''
        Adjust mining difficulty based on rate at which blocks are produced.

        PARAMETERS:
        N/A

        OUTPUT:
        updated difficulty (int) where each block takes an average of 2 minutes to mine (given unchanged hashing rates)
        '''

        #if chain is too short return default difficulty of 1000
        if len(self.longest_chain) <= 10:
            updated_difficulty = 1000
            return updated_difficulty
        
        else:

            #calculate total difficulty of last 10 blocks
            total_difficulty_for_period = 0
            for block in self.longest_chain[-10::]:
                total_difficulty_for_period += block.difficulty

            #calculate time taken to mine last 10 blocks
            block_prev = self.longest_chain[-1]
            block_n_minus_11 = self.longest_chain[-11]
            total_time_for_period = block_prev.timestamp - block_n_minus_11.timestamp

            #placeholder for when total time is zero (avoid DivisionByZero error)
            if total_time_for_period == 0:
                total_time_for_period = 1

            #calculate updated difficulty
            updated_difficulty = (total_difficulty_for_period // total_time_for_period) * 120
            return updated_difficulty

    def verify_and_apply_block(self, block):
        '''
        Check if block is a valid addition to the chain, and add it if it is.

        PARAMETERS:
        block - instance of Block class to be validated before placing on chain

        OUTPUT:
        updates chain with validated block
        updates user states
        updates chain total difficulty
        '''

        #verify block height
        assert block.height == len(self.longest_chain), 'Height of block should equal length of valid chain'

        #verify parent block id
        if len(self.longest_chain) == 0: #if block height is zero, parent ID is byte array of zeros
            assert block.previous == bytes(32), 'Previous block ID should match ID of last block in chain'
        else: 
            assert block.previous == self.longest_chain[-1].block_id, 'Previous block ID should match ID of last block in chain'
        
        #verify timestamp
        if len(self.longest_chain) > 0:
            assert block.timestamp >= self.longest_chain[-1].timestamp, 'Timestamp should not be less than that of parent block'

        #verify block validation
        try: 
            updated_difficulty = self.calculate_difficulty()
            updated_states = block.verify_and_get_changes(updated_difficulty, self.user_states)

            #if block verification succeeds, update chain, difficulty, and states:
            self.longest_chain.append(block)
            self.total_difficulty += block.difficulty
            self.user_states = updated_states

        except AssertionError as e:
            raise

    def undo_last_block(self):
        '''
        Remove the last block from the end of the chain.

        PARAMETERS:
        N/A

        OUTPUT:
        removes last block from chain 
        undoes updates to user states
        undoes updates to chain total difficulty
        '''

        #remove block from chain
        removed_block = self.longest_chain.pop()

        #undo difficulty update
        self.total_difficulty -= removed_block.difficulty

        #revert to previous user states
        undone_states = removed_block.get_changes_for_undo(self.user_states)
        self.user_states = undone_states
    

#--------------------------------------------
##### VERIFY REORG FUNCTION #####
#--------------------------------------------

def verify_reorg(old_state, new_branch):
    '''
    Calculate a new blockchain state corresponding to the new longest chain, and raise an exception if the new chain is invalid.

    PARAMETERS:
    old_state - BlockchainState object corresponding to the previous longest chain
    new_branch - a list of Blocks on the proposed chain 
    
    OUTPUT:
    new BlockchainState object with new_branch if valid
    '''

    #initiate new chain state starting from old_state (use deepcopy as .copy() also manipulates original dict)
    start_chain = copy.deepcopy(old_state.longest_chain)
    start_states = copy.deepcopy(old_state.user_states)
    new_state = BlockchainState(start_chain, start_states, old_state.total_difficulty)

    split_height = new_branch[0].height #height at which new branch splits from old chain

    try:

        for block in reversed(new_state.longest_chain):

            #undo blocks above the split height
            if block.height >= split_height:

                new_state.undo_last_block()

            else: 
                break

        #add new branch
        for block in new_branch:
            new_state.verify_and_apply_block(block)

        #ensure that new chain has more proof-of-work than old chain
        assert new_state.total_difficulty > old_state.total_difficulty, 'New chain has lower total difficulty than old chain'

        return new_state

    except AssertionError:
        raise