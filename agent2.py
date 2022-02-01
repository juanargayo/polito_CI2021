import collections
from os import stat
import os
import random
import socket
from sys import stdout
from threading import Thread
from unittest.result import STDOUT_LINE
from xmlrpc.client import Boolean
import numpy as np
from numpy import nancumsum
import GameData
import time
from constants import DATASIZE
from game import Card
from cardhints import CardHints

HOST = ''
PORT = 1024


def connectClients(numPlayers: int) -> list():
    clientSockets = []
    for client in range(numPlayers):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))

        playerName = "player" + str(client)
        print(f"main: {playerName}")

        # CONNECT CLIENTS
        request = GameData.ClientPlayerAddData(playerName)
        s.send(request.serialize())
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is not GameData.ServerPlayerConnectionOk:
            return
        print("Connection accepted by the server. Welcome " + playerName)
        clientSockets.append(s)
    return clientSockets


def getReadyClients(numPlayers: int, clientSockets: list) -> int:
    for client in range(numPlayers):
        playerName = "player" + str(client)
        s = clientSockets[client]

        # GET CLIENTS READY
        s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)

        if type(data) is not GameData.ServerPlayerStartRequestAccepted:
            return -1
        print("Ready: " + str(data.acceptedStartRequests) +
              "/" + str(data.connectedPlayers) + " players")
    for client in range(numPlayers):
        playerName = "player" + str(client)
        s = clientSockets[client]

        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is not GameData.ServerStartGameData:
            return -1
        s.send(GameData.ClientPlayerReadyData(playerName).serialize())
    return 0


def getNumSlots(numPlayers):
    if numPlayers <= 3:
        return 5
    else:
        return 4


def commandShow(playerName: str, s: socket):  # SHOW (just first time)
    s.send(GameData.ClientGetGameStateRequest(
        playerName).serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)

    # print(type(data))
    if type(data) is GameData.ServerGameStateData:
        dataOk = True
        # Removing print for debugging purpose (too much print...)

        # print("Current player: " + data.currentPlayer)
        # print("Player hands: ")
        # for p in data.players:
        #     print(p.toClientString())
        #     # SAVING INFORMATIONS => cards[0] avremo la hand di player0
        # print("Cards in your hand: " + str(data.handSize))
        # print("Table cards: ")
        # for pos in data.tableCards:
        #     print(pos + ": [ ")
        #     for c in data.tableCards[pos]:
        #         print(c.toClientString() + " ")
        #         print("]")
        # print("Discard pile: ")
        # for c in data.discardPile:
        #     print("\t" + c.toClientString())
        # print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
        # print("Storm tokens used: " + str(data.usedStormTokens) + "/3")
        return data
    return None


def manageHintResponse(data):
    data = GameData.GameData.deserialize(data)
    if type(data) is not GameData.ServerHintData:
        print("Invalid action, terminating", type(data))
        os._exit(-1)

    print("Hint type: " + data.type)
    print("Player " + data.destination +
          " cards with value " + str(data.value) + " are:")
    for i in data.positions:
        print("\t" + str(i))


def managePlayResponse(data):
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerMoveOk:
        print("Nice move!")
        print("Current player: " + data.player)
        print(f"card played: {(data.card).toString()} , card.value: {data.card.value}")
        # print(f"cardColor: {data.card.color}")
        # print(f"lastPlayer: {data.lastPlayer} player: {data.player} handLength: {data.handLength}")
        return 1
    if type(data) is GameData.ServerPlayerThunderStrike:
        print("OH NO! The Gods are unhappy with you!")
        print(f"card played: {(data.card).toString()} , card.value: {data.card.value}")
        return -1
    if type(data) is GameData.ServerGameOver:
        print(data.message)
        print(data.score)
        print(data.scoreMessage)
        stdout.flush()
        print("Ready for a new game!")
        return 0


def manageDiscardResponse(data):
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerActionValid:
        dataOk = True
        print("Action valid!")
        print("Current player: " + data.player)
        return 1
    elif type(data) is GameData.ServerGameOver:
        print("Game over!")
        print("Start new game")
        return 0
    else:
        print("Some error occurred with discard... this should not happen")
        print(type(data))
        os._exit(-1)

# Function that updates the HintTable after an Hint


def manageHintTableHintUpdate(data):
    global numPlayers
    global hintTable
    global slots
    data = GameData.GameData.deserialize(data)
    for i in range(slots):
        if i in data.positions:
            if data.type == "color":
                hintTable[int(data.destination[-1:])
                          ][i].directHintColor(data.value)
            elif data.type == "value":
                hintTable[int(data.destination[-1:])
                          ][i].directHintValue(data.value)
            else:
                print("ERROR: Wrong hint type")
        else:
            if data.type == "color":
                hintTable[int(data.destination[-1:])
                          ][i].undirectHintColor(data.value)
            elif data.type == "value":
                hintTable[int(data.destination[-1:])
                          ][i].undirectHintValue(data.value)
            else:
                print("ERROR: Wrong hint type")

# Function that updates the HintTable after a play or a discard


def manageHintTableUpdate(playerNum: int, slotNum: int):
    global numPlayers
    global hintTable
    global slots

    # for s in range(slotNum, slots-1):
    #     hintTable[playerNum][s] = hintTable[playerNum][s+1]
    # s += 1
    # hintTable[playerNum][s] = CardHints(slots)

    hintTable[playerNum].pop(slotNum)
    hintTable[playerNum].append(CardHints(slots))


            


run = True

numPlayers = 3
slots = getNumSlots(numPlayers)

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]
cards = []

hintTable = [[0 for x in range(getNumSlots(numPlayers))] 
                for y in range(numPlayers)]        # Array of shape H=[#Players][#Slots]

tableCards = {}     # dict for storing the stacks of cards on the table

colorDict = {0:'red', 1:'green', 2:'blue', 3:'yellow', 4:'white'}
colorsName= ['red', 'green', 'blue', 'yellow', 'white']

discardedCards = {c:[0, 0, 0, 0, 0] for c in colorDict}
uselessCards = {c:0 for c in colorDict}

CARD_LIMIT = [3, 2, 2, 2, 1]    #3 one's for every color, 2 two's, three's and four's, and 1 five's


#########  RULES HERE JUST TO TEST, THEN TO BE MOVED TO rules.py  ###########

def playIfCertain(playerNum: int, hintTable):
    # ok to import them? is there a better way?
    for slot in range(getNumSlots(numPlayers)):
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):
            # print(f"Found playable card for slot number {slot}:")
            # print(f"the type(hintTable[slot].values.values()): {type(hintTable[slot].values.values())}")
            # print(f"list(hintTable[slot].values.values()).index(1)+1: {list(hintTable[slot].values.values()).index(1)+1}")
            # print(f"list(hintTable[slot].colors.values()).index(1): {list(hintTable[slot].colors.values()).index(1)}")
            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(hintTable[slot].colors.values()).index(1)]
                print(f"cardNum: {cardNum} , cardColor: {cardColor}")
                if(isPlayable(cardNum, cardColor, tableCards)):
                    print("The card is playable")
                    return slot
                else:
                    print("The card is NOT playable")
                    continue
            except ValueError:
                print(f"ifCertain: No known card value in slot: {slot}")
                continue
                                        # In this case, we are playing the first playable card
                                        # of the player, there maybe more than one, we can make
                                        # an array and then by some metric (or random) choose one

def isPlayable(cardNum, cardColor, tableCards) -> bool:       #based on the 5 stacks of cards, says if one card is playable
    # print(f"The tableCards at isPlayable is: {tableCards}")
    # print(f"tableCards[cardColor]: {tableCards[cardColor]} , len(tableCards[cardColor]): {len(tableCards[cardColor])}")
    # print(f"cardNum: {cardNum} , cardColor: {cardColor}")
    if(len(tableCards[cardColor])==cardNum-1):          #TODO: Check if its possible that there ar/can be empty places in the array that throws off the len() calculation
        print("I can play the card")                    #TODO: Check if need this function to say if its NOW playable (like it works now), or to say if it can be played in the future
        return True

    return False

def playSafeCard(hintTable, tableCards):        #we know just know the number of the card. It searches
                                                #for a slot it can be placed, regardless of the color
    cardsNum = []
    for slot in range(getNumSlots(numPlayers)):
        try:
            #print(list(hintTable[slot].values.values()))
            possibleCards = list(hintTable[slot].values.values()).index(1)+1                            #TODO: Check that card_index+1 matches card value when hinted/played
            print(f"list comp {[possibleCards==len(tableCards[colorDict[x]])+1 for x in range(5)]}")
            # for x in range(5): 
            #     print(f"tablecard[{x}]: {tableCards[colorDict[x]]}")
            # print(f"possibleCards-1: {possibleCards-1} ")
            if(any(possibleCards==len(tableCards[colorDict[x]])+1 for x in range(5))):
                print(f"possibleCardsFound: {possibleCards} and tableCards: {tableCards}")
                cardsNum.append(possibleCards) 
        except ValueError:
            print(f"No known card value in slot: {slot}")
            continue
    if(cardsNum):    
        return cardsNum[0]       #return the first card to be playable. There can be many, we may choose by some metric                  
    else:
        return None

def hintPartiallyKnown(hintTable, tableCards, playerWhoHints, players):      #I hint a card that IS playable, which the player just knows the color or the value

    print(f"\nThe playerWhoHints is: {playerWhoHints}")
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]  
    print(f"players after slicing: {playersArr}\n")
    
    for p in playersArr:
        for slot in range(slots):
            foundValue = any(el == 1 for el in hintTable[p][slot].values.values())
            foundColor = any(el == 1 for el in hintTable[p][slot].colors.values())

            if(isPlayable(players[p].hand[slot].value, players[p].hand[slot].color, tableCards)):       #TODO: Check correspondance between cards 
                if foundValue and not foundColor:                                                       #in hintTable and in the players hand
                    return p, players[p].hand[slot].color
                elif not foundValue and foundColor:
                    return p, players[p].hand[slot].value                                       #TODO: Check that card_index+1 matches card value when hinted/played
                else:
                    continue                                                                    #TODO: Test, debug and check
            else:
                continue
    
    return None, 0

def hintOnes(hintTable, playerWhoHints, players):                   #Hints cards with value one to the player that has the most of them

    print(f"\nThe playerWhoHints is: {playerWhoHints}")
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]  
    print(f"players after slicing: {playersArr}\n")
    
    maxOnePlayer = None, 0      #FIrst value: player number, Second value: amount of one cards in his hand

    for p in playersArr:
        onesCount = 0
        for slot in range(slots):
            if hintTable[p][slot].values.values()[1] == 1:   #position number 0 in hintTable has the info of card value 1
                continue           #The player p already knows about this one. See other slots
            if players[p].hand[slot].value == 1:
                onesCount += 1
        if onesCount > maxOnePlayer[1]:
            maxOnePlayer[0] = p
            maxOnePlayer[1] = onesCount                                         #TODO: Test, debug and check

    if maxOnePlayer[1] > 0:
        return maxOnePlayer[0], 1
    else:
        return None, 0      #no player with one-value cards found

def hintUseful(hintTable, tableCards, playerWhoHints, players):             #Tell anoyone about some useful info of a playable card. 
                                                                            #Prioritizing value information over color of a card. 
    print(f"\nThe playerWhoHints is: {playerWhoHints}")
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr - playersArr[playerWhoHints]  
    print(f"players after slicing: {playersArr}\n")
    random.shuffle(playersArr)
    print(f"players after shuffle: {playersArr}\n")

    for p in playersArr:
        for slot in range(slots):
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

def hintOld(hintTable, playerWhoHints, players, tableCards):            #Chooses a random player and hints him the oldest card it has
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr - playersArr[playerWhoHints] 
    random.shuffle(playersArr)
    hint = 1 
    age = 0

    break_out_flag = False

    for p in playersArr:
        for slot in range(slots):
            if isPlayable(players[p].hand[slot].value, players[p].hand[slot].color, tableCards):
                if hintTable[p][slot].age > age:
                    age = hintTable[p][slot].age
                    if not any(el == 1 for el in hintTable[p][slot].values.values()):
                        hint = players[p].hand[slot].value
                    else:
                        hint = players[p].hand[slot].color
            break_out_flag = True
        if break_out_flag:                                                                      #TODO: Test, debug and check
            break

    return p, hint


def hintPlayable(playerWhoHints, players, tableCards):              #Hints a playable card, randomly chooses between color or value, even if it already knows it
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr - playersArr[playerWhoHints] 
    random.shuffle(playersArr)

    for p in playersArr:
        for slot in range(slots):
            if(isPlayable(players[p].hand[slot].value, players[p].hand[slot].color, tableCards)):
                return p, random.choice([players[p].hand[slot].value, 
                                        players[p].hand[slot].color])

    return None, 0                                                                                  #TODO: Test, debug and check

def hintUseless(hintTable, playerWhoHints, players, tableCards):                    #Hints a useless card. A card whoes value is below the stack's top one, for the given color
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr - playersArr[playerWhoHints] 
    random.shuffle(playersArr)

    for p in playersArr:
        for slot in range(slots):
            if len(tableCards[players[p].hand[slot].color]) >= players[p].hand[slot].value:     #checks for the pile of the cards color if the amount (len()) of cards
                                                                                                #its higher than the card's number. If True > card won't be played
                if not any(el == 1 for el in hintTable[p][slot].values.values()):
                    return p, players[p].hand[slot].value                                       #if the players doesn't know the value, I hint it
                elif not any(el == 1 for el in hintTable[p][slot].colors.values()):
                    return p, players[p].hand[slot].color                                       #if the players doesn't know the color, I hint it
    return None, 0                                                                              #TODO: Test, debug and check

def hintFives(hintTable, playerWhoHints, players):
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]  
    random.shuffle(playersArr)

    maxOnePlayer = None, 0      #FIrst value: player number, Second value: amount of one cards in his hand

    for p in playersArr:
        fivesCount = 0
        for slot in range(slots):
            if hintTable[p][slot].values.values()[5] == 5:
                continue           #The player p already knows about this five. See other slots
            if players[p].hand[slot].value == 5:
                fivesCount += 1
        if fivesCount > maxOnePlayer[1]:
            maxOnePlayer[0] = p
            maxOnePlayer[1] = fivesCount                                         #TODO: Test, debug and check

    if maxOnePlayer[1] > 0:
        return maxOnePlayer[0], 5
    else:
        return None, 0      #no player with five-value cards found


def hintMostInfo(hintTable, playerWhoHints, players):                       #Hint whatever gives the most information to the player 
    playersArr = [p for p in range(numPlayers)]                             #(given by amount of cards with same color or value)
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]  
    p = random.choice(playersArr)

    color = {c:0 for c in colorsName}       #(color name, #repetitions)
    value = {v:0 for v in range(1,6)}       #(value, #repetitions)

    for slot in range(slots):
        if hintTable[p][slot].values.values()[players[p].hand[slot].value] == 0:    #checks if the card's value/color the player p has in its hand has not been hinted yet
            value[players[p].hand[slot].value] += 1
        if hintTable[p][slot].colors.values()[players[p].hand[slot].color] == 0:
            color[players[p].hand[slot].color] += 1


    sortedColor =  collections.OrderedDict({k: v for k, v in sorted(color.items(), key=lambda item: item[1], reverse=True)})
    sortedValue =  collections.OrderedDict({k: v for k, v in sorted(value.items(), key=lambda item: item[1], reverse=True)})

    if next(iter(sortedColor.values())) >= next(iter(sortedValue.values())):
        return p, next(iter(sortedColor.keys()))
    else:                                                                                       #TODO: Test, debug and check
        return p, next(iter(sortedValue.keys()))

def hintRandom(hintTable, playerWhoHints, players):
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr[playerWhoHints:] + playersArr[:playerWhoHints]  
    
    p = random.choice(playersArr)

    randomColor = random.choice(colorsName)
    randomValue = random.choice([v for v in range(1,6)])                                        #TODO: Test, debug and check

    return p, random.choice([randomColor, randomValue])                #TODO: manage how do we know at the other end if we hint value or color

def hintUnkown(hintTable, tableCards, playerWhoHints, players):         #Hint new info to a player about its cards. 
                                                                        #The card might not be playable. Differently, in hintUseful the card IS playable
    playersArr = [p for p in range(numPlayers)]
    playersArr = playersArr - playersArr[playerWhoHints]  
    random.shuffle(playersArr)

    for p in playersArr:
        for slot in range(slots):
            foundValue = any(el == 1 for el in hintTable[p][slot].values.values())
            foundColor = any(el == 1 for el in hintTable[p][slot].colors.values())
            if not foundValue and foundColor:                                       #in hintTable and in the players hand
                return p, players[p].hand[slot].value
            elif foundValue and not foundColor:
                return p, players[p].hand[slot].color                               
            elif not foundColor and not foundValue:
                return p, players[p].hand[slot].value                                                                    #TODO: Test, debug and check
            else:
                continue

    return None, 0

def discardUseless(player, hintTable):

    for slot in range(slots):
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):

            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(hintTable[slot].colors.values()).index(1)]
                print(f"cardNum: {cardNum} , cardColor: {cardColor}")
                if(uselessCards[cardColor] >= cardNum):
                    print("The card is discardable")
                    return slot
                else:
                    print("The card is NOT discardable")
                    continue
            except ValueError:
                print(f"discardUseless: No known card value in slot: {slot}")
                continue
                                        # In this case, we are discarding the first discardable card
                                        # of the player, there maybe more than one, we can make
                                        # an array and then by some metric (or random) choose one

    return None

def discardIfCertain(player, hintTable):

    for slot in range(slots):
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):

            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(hintTable[slot].colors.values()).index(1)]
                print(f"cardNum: {cardNum} , cardColor: {cardColor}")
                if(not isPlayable(cardNum, cardColor, tableCards)):
                    print("The card is not playable = discardable")
                    return slot
                else:
                    print("The card is playable = NOT discardable")
                    continue
            except ValueError:
                print(f"discardNoPlayable: No known card value in slot: {slot}")
                continue

    return None

def discardUselessNotPlayable(player, hintTable):

    for slot in range(slots):
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):

            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(hintTable[slot].colors.values()).index(1)]
                print(f"cardNum: {cardNum} , cardColor: {cardColor}")
                if(not isPlayable(cardNum, cardColor, tableCards)):
                    print("The card is not playable = discardable")
                    return slot
                if len(tableCards[cardColor]) == 4:                  #TODO: Check if its possible that there ar/can be empty places in the array that throws off the len() calculation
                    return slot                 #the stack of that color has been completed, any other card of that color can be discarded
                if(uselessCards[cardColor] >= cardNum):
                    print("The card is discardable")
                    return slot
                else:
                    print("The card is playable = NOT discardable")
                    continue
            except ValueError:
                print(f"discardNoPlayable: No known card value in slot: {slot}")
                continue

    return None

def discardHighest(player, hintTable):                  #Discards card in hand with highest known value

    slotToDiscard = 0

    for slot in range(slots):
        if any(el == 1 for el in hintTable[slot].values.values()):
            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                if cardNum > slotToDiscard:
                    slotToDiscard = cardNum
            except ValueError:
                print(f"discardNoPlayable: No known card value in slot: {slot}")
                continue
    if slotToDiscard == 0:
        print("discardHighest: No known card to discard")
        return None
    else:
        return slotToDiscard

def discardOldestNotPlayable(player, hintTable):

    slotToDiscard = 0
    age = 0

    for slot in range(slots):
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):
            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(hintTable[slot].colors.values()).index(1)]
                print(f"cardNum: {cardNum} , cardColor: {cardColor}")
                if(not isPlayable(cardNum, cardColor, tableCards)):
                    if hintTable[slot].age > age:
                        age = hintTable[slot].age
                        slotToDiscard = slot
                else:
                    continue
            except ValueError:
                print(f"discardOldestNotPlayable: No known card value in slot: {slot}")
                continue

    if slotToDiscard == 0:
        print("discardOldest: No known card to discard")
        return None
    else:
        return slotToDiscard

def discardOldest(player, hintTable):

    slotToDiscard = 0
    age = 0

    for slot in range(slots):
        if hintTable[slot].age > age:
            age = hintTable[slot].age
            slotToDiscard = slot

    if slotToDiscard == 0:
        print("discardOldest: No known card to discard")
        return None
    else:
        return slotToDiscard

def discardNoInfo(player, hintTable):

    slotsToDiscard = []

    for slot in range(slots):
        if(not any(el == 1 for el in hintTable[slot].values.values())
            and not any(el == 1 for el in hintTable[slot].colors.values())):

            slots.append(slot)

    if slotsToDiscard:
        return random.choice(slotsToDiscard)
    else:
        return None

def discardLeastLikelyToBeNecessary(player, hintTable,tableCards):

    _slots = [s for s in range(slots)]
    necessarySlots = []
    notPlayableSlots = []

    for slot in _slots:
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):
            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(hintTable[slot].colors.values()).index(1)]
                
                if len(tableCards[cardColor]) < cardNum:                                    #Card may be playable in the future
                    if discardedCards[cardColor][cardNum]+1 == CARD_LIMIT[cardNum-1]:       #Test if the card is the last of its kind.  
                        necessarySlots.append(slot)                                         #For this, I see if the discardedCards of that card are one from being all discarded/used
                else:
                    notPlayableSlots.append(slot)
                    continue
            except ValueError:
                print(f"discardLeastLikelyToBeNecessary: No known card value in slot: {slot}")
                continue

    notNecessarySlots = [s for s in _slots if s not in [*necessarySlots, *notPlayableSlots]]

    if (notPlayableSlots):
        return random.choice(notPlayableSlots)
    else:
        return None


def DiscardProbablyUselessCard():
                #TODO: To be done. Look def in framework
    return None
#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

def updateDiscardedUselessCards(cardDiscarded):

    """ Updates the discardedCards dict that holds a counter for the numberof time each card (value & color) is discarded.
        Also, updates the uslessCards dict that has for every color the value of the card for which all cards of that (value&color) had been discarded"""

    discardedCards[cardDiscarded.color][cardDiscarded.value-1] += 1

    if (discardedCards[cardDiscarded.color][cardDiscarded.value-1] >= CARD_LIMIT[cardDiscarded.value-1]) and cardDiscarded.value > uselessCards[cardDiscarded.color]:

        uselessCards[cardDiscarded.color] = cardDiscarded.value


def hintTableInit():
    global numPlayers
    global hintTable
    global slots
    for p in range(numPlayers):
        for slot in range(slots):
            hintTable[p][slot] = CardHints(slots)

def updateCardsAge(hintTable):

    for p in range(numPlayers):
        for slot in range(slots):
            hintTable[p][slot].incrementAge()

def main():
    global status
    global numPlayers
    global hintTable
    global tableCards
    print("start simulation")
    clientSockets = []

    print("start simulation")

    clientSockets = connectClients(numPlayers)
    print("connected")

    getReadyClients(numPlayers, clientSockets)
    print("ready")

    run = True
    players = []

    # init HintTable => will be updated on hint or play or discard
    hintTableInit()

    # START GAME
    it = 0
    while run:
        for client in range(numPlayers):
            playerName = "player" + str(client)

            s = clientSockets[client]

            print(f"\nplayer{client},it:{it} \n")

            # Before starting, every player is doing show in order to update infos
            game = commandShow(playerName, s)
            players = game.players
            tableCards = game.tableCards
            print(f"players[client]: {players[client].toString()} players[1].hand: {players[client].hand}")

            print(f"the tableCards are: {tableCards}")

            updateCardsAge()        #increment all the cards' age in the hand of players by one

            # 1. think a move (All players hinting if possible,  but player1)
            # move = "hint" if (
            #     playerName != "player1" and game.usedNoteTokens < 8) else "discard"
            move = "hint" if client % 2 == 0 and playerName != "player1" and game.usedNoteTokens < 8 else "play"    #just to test and alternate

            
            # 2. take action
            if move == "play":

                # (PLAY ALWAYS CARD 0)

                #probableSlot = playIfCertain(client, hintTable[client])
                probableSlot = playSafeCard(hintTable[client], tableCards)

                print(f"probableSlot: {probableSlot}")

                cardPos = probableSlot if probableSlot else 0
                #cardPos = 0
                s.send(GameData.ClientPlayerPlayCardRequest(
                    playerName, cardPos).serialize())
                data = s.recv(DATASIZE)
                res = managePlayResponse(data)

                # this is just ack for other players...
                for c in range(numPlayers):
                    if c == client:
                        continue
                    data = clientSockets[c].recv(DATASIZE)
                    res = managePlayResponse(data)

                # This means game ended, so.. restart
                if res == 0:
                    hintTableInit()
                    print("Start new game")
                    #run = False
                    break

                # shift hint slot when playing a card
                manageHintTableUpdate(client, cardPos)      

            elif move == "hint":
                # (GIVE HINT)
                # 1. send a request

                hintPartiallyKnown(hintTable, tableCards, client)

                cardPos = 0
                typ = "value"
                dest = "player1"

                # value? => Find value of the first card of player1 (just for the moment)
                value = players[1].hand[0].value if typ == "value" else players[1].hand[0].color
                print(value)

                # Send request
                s.send(GameData.ClientHintData(
                    playerName, dest, typ, value).serialize())

                # Response must be read first from the sender, then from the others
                data = s.recv(DATASIZE)
                manageHintResponse(data)

                # HintResponse ACK for the remaining clients
                for c in range(numPlayers):
                    if c == client:
                        continue
                    data = clientSockets[c].recv(DATASIZE)
                    manageHintResponse(data)

                # Hint table update
                manageHintTableHintUpdate(data)

                # hard code moves, just to test the rule , it might give problems when there are two correct colors for card 0
                #hintTable[1][0].directHintColor('red')
                #hintTable[1][0].directHintValue(1)

                # Just for testing
                print("\nHINT TABLE (after update):")
                for slot in range(slots):
                    print(
                        f"values: {hintTable[1][slot].values}")
                    print(
                        f"colors: {hintTable[1][slot].colors}\n")

                # playableCard = playIfCertain(1, hintTable[1])
                # print(f"\n the playable card is: {playableCard}")

                # 2. Put hint info in HINT TABLE (done)
                # 3. Check if token is correctly decreasing (done)
                # 4. Remember to update info after play or discard (done)

            elif move == "discard":
                discardOrder = 4
                s.send(GameData.ClientPlayerDiscardCardRequest(
                    playerName, discardOrder).serialize())
                data = s.recv(DATASIZE)
                res = manageDiscardResponse(data)
                if res:
                    manageHintTableUpdate(client, discardOrder)
                    updateDiscardedUselessCards(data.card)
                
                for c in range(numPlayers):
                    if c == client:
                        continue
                    data = clientSockets[c].recv(DATASIZE)
                    res = manageDiscardResponse(data)

                # this means GameOver
                if res == 0:
                    break


if (__name__ == "__main__"):
    main()
