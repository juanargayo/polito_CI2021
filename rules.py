

from ast import If
import random
from game import Card

import time

colorDict = {0: 'red', 1: 'green', 2: 'blue', 3: 'yellow', 4: 'white'}
colorsName = ['red', 'green', 'blue', 'yellow', 'white']


def ruleMatch(playerNum: int, ruleNum: int, hintTable) -> str:
    # returns cardNumber to be used
    return rules[ruleNum](playerNum, hintTable)


def isPlayable(cardNum, cardColor, tableCards) -> bool:
    # print(f"The tableCards at isPlayable is: {tableCards}")
    # print(f"tableCards[cardColor]: {tableCards[cardColor]} , len(tableCards[cardColor]): {len(tableCards[cardColor])}")
    # print(f"cardNum: {cardNum} , cardColor: {cardColor}")
    # TODO: Check if its possible that there are empty places in the array that throws the len() calculation
    if(len(tableCards[cardColor]) == cardNum-1):
        print("I can play the card")
        return True
    return False


def playIfCertain(playerNum: int, hintTable, tableCards, slots):
    for slot in range(slots):
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):
            # print(f"Found playable card for slot number {slot}:")
            # print(f"the type(hintTable[slot].values.values()): {type(hintTable[slot].values.values())}")
            # print(f"list(hintTable[slot].values.values()).index(1)+1: {list(hintTable[slot].values.values()).index(1)+1}")
            # print(f"list(hintTable[slot].colors.values()).index(1): {list(hintTable[slot].colors.values()).index(1)}")
            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(
                    hintTable[slot].colors.values()).index(1)]
                print(f"cardNum: {cardNum} , cardColor: {cardColor}")
                if(isPlayable(cardNum, cardColor, tableCards)):
                    print("The card is playable")
                    return slot
                else:
                    print("The card is NOT playable")
                    return False
            except ValueError:
                print(f"ifCertain: No known card value in slot: {slot}")
                # In this case, we are playing the first playable card
                # of the player, there maybe more than one, we can make
                # an array and then by some metric (or random) choose one

# Plays a card that is known to be playable (even with partial informations)

# we know just know the number of the card. It searches

# TODO: handle undirect hint
# TODO: handle also full known hint


def playSafeCard(hintTable, tableCards, slots):
    # for a slot it can be placed, regardless of the color
    cardsNum = []
    for slot in range(slots):
        try:
            # print(list(hintTable[slot].values.values()))
            # TODO: Check that card_index+1 matches card value when hinted/played

            possibleCards = list(hintTable[slot].values.values()).index(1)+1
            print(
                f"list comp {[possibleCards==len(tableCards[colorDict[x]])+1 for x in range(5)]}")
            # for x in range(5):
            #     print(f"tablecard[{x}]: {tableCards[colorDict[x]]}")
            # print(f"possibleCards-1: {possibleCards-1} ")
            if(any(possibleCards == len(tableCards[colorDict[x]])+1 for x in range(5))):
                print(
                    f"possibleCardsFound: {possibleCards} and tableCards: {tableCards}")
                cardsNum.append(possibleCards)
        except ValueError:
            print(f"No known card value in slot: {slot}")
    if(cardsNum):
        # return the first card to be playable. There can be many, we may choose by some metric
        return cardsNum[0]
    else:
        return None



cardsNumber = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}

# Return how many cards are still present for that values and that colors


def getNumCards(values: list, colors: list, others, fireworks):
    #others = [card for cards in others for card in cards]

    # values = [1, 3]
    # colors = ["red", "green"]

    # print(f"values: {values}")
    # print(f"colors: {colors}")
    # print(f"others: {others}")
    # print(f"fireworks: {fireworks}")

    n = 0
    for v in values:
        for col in colors:
            n += cardsNumber[v]
            n -= sum(1 for c in others if c.value ==
                     v and c.color == col)
            n -= fireworks[col].count(v)
    #print(f"TOT: {n}")
    return n

# Prob that card in numslot has that value and color


def calcprob(numslot, value, color, hint, others, discards, colorStack, fireworks):
    # Test just value hint

    # PARTIALLY KNOWN-2 VALUE+COLOR => Ok
    # hint.values = {1: 0, 2: -1, 3: 0, 4: -1, 5: -1}
    # hint.colors = {'red': 0, 'green': 0, 'blue': -1, 'yellow': -1, 'white': -1}

    # PARTIALLY KNOWN-2 VALUE => ok
    # hint.values = {1: 0, 2: 0, 3: -1, 4: 0, 5: -1}
    # hint.colors = {'red': 0, 'green': 0, 'blue': 0, 'yellow': 0, 'white': 0}

    # PARTIALLY KNOWN-2 COLOR => ok
    # hint.values = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    # hint.colors = {'red': 0, 'green': 0, 'blue':-1, 'yellow': -1, 'white': -1}

    # PARTIALLY KNOWN-1 VALUE => Final prob: 1.0 in first play => OK
    # hint.values = {1: 1, 2: -1, 3: -1, 4: -1, 5: -1}
    # hint.colors = {'red': 0, 'green': 0, 'blue': 0, 'yellow': 0, 'white': 0}

    # PARTIALLY KNOWN-1 COLOR => ok
    # hint.values = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    # hint.colors = {'red': 1, 'green': -1, 'blue': -1, 'yellow': -1, 'white': -1}

    # COMPLETELY KNOWN => OK
    # hint.values = {1: 1, 2: -1, 3: -1, 4: -1, 5: -1}
    # hint.colors = {'red': 1, 'green': -1, 'blue': -1, 'yellow': -1, 'white': -1}

    # COMPLETELY UKNOWN
    # hint.values = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    # hint.colors = {'red': 0, 'green': 0, 'blue': 0, 'yellow': 0, 'white': 0}

    possibleValues = [k for k in hint.values if hint.values[k] == 0]
    possibleColors = [k for k in hint.colors if hint.colors[k] == 0]

    # Finiamo nel caso partiallyknown1-value o partiallyknown1-color
    if(not len(possibleValues)):
        possibleValues = [k for k in hint.values if hint.values[k] == 1]
    if(not len(possibleColors)):
        possibleColors = [k for k in hint.colors if hint.colors[k] == 1]

    # Se tra i valori possibili non è listato il colore o il valore corrente, la probabilità è 0
    if(value not in possibleValues or color not in possibleColors):
        num = 0
        tot = 1
    else:
        # Get the numbers of the cards value-color still present (not played, nor discarded, nor present in other players hand)
        # num = cardsNumber[value]
        # num -= getOccurrencies(others, value, color)
        # num -= getOccurrencies(discards, value, color)
        # num -= colorStack.count(value)
        num = getNumCards([value], [color], others + discards, fireworks)
        tot = getNumCards(possibleValues, possibleColors,
                          others + discards, fireworks)

    print(
        f"\tprob for card {str(value)+color[0].upper()} and slot{numslot}: {num}/{tot}={num/tot}")

    return num/tot


def playProbablySafeCard(playerNum: int, hintTable, slots,  fireworks, others, discards, p):
    print(
        f"cards: {[str(card.value)+card.color for cards in others for card in cards]}")
    others = [card for cards in others for card in cards]

    probs = []
    for slot in range(slots):
        print(f"slot n.{slot}:")
        prob = 0
        # Compute prob for that card to be playable
        for x in fireworks:
            next = 1 if not fireworks[x] else int(fireworks[x][-1].value) + 1
            # Calc probability that card in my slot has next-value and x-color
            p = calcprob(
                slot, next, x, hintTable[slot], others, discards, fireworks[x], fireworks)
            prob += p
        print(f"Final prob for slot{slot}: {prob}\n")
        probs.append(prob)
    # Put a threshold and if not return false
    return probs.index(max(probs)) if max(probs) > p else False

# ------------#
#  HINT PART  #
# ------------#

# I hint a card that IS playable, which the player just knows the color or the value
def hintPartiallyKnown(hintTable, tableCards, playerWhoHints, players):
    print(f"\nThe playerWhoHints is: {playerWhoHints}")
    playersArr = [p for p in range(len(players))]
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]
    playersArr.remove(playerWhoHints)
    for p in playersArr:
        for slot in range(len(players[p].hand)):
            foundValue = any(
                el == 1 for el in hintTable[p][slot].values.values())
            foundColor = any(
                el == 1 for el in hintTable[p][slot].colors.values())

            # TODO: Check correspondance between cards
            if(isPlayable(players[p].hand[slot].value, players[p].hand[slot].color, tableCards)):
                if foundValue and not foundColor:  # in hintTable and in the players hand
                    return p, players[p].hand[slot].color
                elif not foundValue and foundColor:
                    # TODO: Check that card_index+1 matches card value when hinted/played
                    return p, players[p].hand[slot].value
                else:
                    continue
    return None, 0


# Hints cards with value one to the player that has the most of them
def hintOnes(hintTable, playerWhoHints, players):
    print(f"\nThe playerWhoHints is: {playerWhoHints}")
    playersArr = [p for p in range(len(players))]
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]

    playersArr.remove(playerWhoHints)

    # FIrst value: player number, Second value: amount of one cards in his hand
    maxOnePlayer = [None, 0]

    for p in playersArr:
        onesCount = 0
        for slot in range(len(players[p].hand)):
            # position number 0 in hintTable has the info of card value 1
            if hintTable[p][slot].values[1] == 1:
                continue  # The player p already knows about this one. See other slots
            if players[p].hand[slot].value == 1:
                onesCount += 1
        if onesCount > maxOnePlayer[1]:
            maxOnePlayer[0] = p
            maxOnePlayer[1] = onesCount  # TODO: Test, debug and check

    if maxOnePlayer[1] > 0:
        return maxOnePlayer[0], 1
    else:
        return None, 0  # no player with one-value cards found

def hintUseful(hintTable, tableCards, playerWhoHints, players):             #Tell anoyone about some useful info of a playable card. 
                                                                            #Prioritizing value information over color of a card. 
    print(f"\nThe playerWhoHints is: {playerWhoHints}")
    playersArr = [p for p in range(len(players))]
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]
    playersArr.remove(playerWhoHints)
    random.shuffle(playersArr)
    
    for p in playersArr:
        for slot in range(len(players[p].hand)):
            foundValue = any(el == 1 for el in hintTable[p][slot].values.values())
            foundColor = any(el == 1 for el in hintTable[p][slot].colors.values())

            if isPlayable(players[p].hand[slot].value, players[p].hand[slot].color, tableCards):       #TODO: Check correspondance between cards 
                if not foundValue and foundColor:                                                       #in hintTable and in the players hand
                    return p, players[p].hand[slot].value
                elif foundValue and not foundColor:
                    return p, players[p].hand[slot].color                               
                elif not foundColor and not foundValue:
                    return p, players[p].hand[slot].value                                                                    #TODO: Test, debug and check
            else:
                continue

    return None, 0


# Array of rule functions
rules = [playIfCertain, playSafeCard, playProbablySafeCard, hintPartiallyKnown, hintOnes, hintUseful]


def probPlayable(card: Card, table, discards, fireworks, hintTable):

    pass
