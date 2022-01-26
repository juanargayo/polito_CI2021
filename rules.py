

from agent2 import getNumSlots, numPlayers


def ruleMatch(playerNum: int, ruleNum: int, hintTable) -> str:

    return rules[ruleNum](playerNum, hintTable)        #returns cardNumber to be used

def playIfCertain(playerNum: int, hintTable):
    for slot in range(getNumSlots(numPlayers)):    #ok to import them? is there a better way?        
        for (k1, v1), (k2, v2) in zip(hintTable[slot].values, hintTable[slot].colors):
            #print(f"{k1} -> {v1}")
            #print(f"{k2} -> {v2}")
            if(v1==v2):
                print(f"For slot number {slot}:")
                print(f"k1: {k1} and k2: {k2}")

    return None

def playIfHinted(playerNum: int):

    return


#Array of rule functions
rules = [playIfCertain,
        playIfHinted]