from ast import Break
from distutils.log import debug
from os import stat
import os
from sys import stdout
from threading import Thread
import numpy as np
from numpy import nancumsum
import GameData
import time
from constants import DATASIZE
from game import Card, Game
from cardhints import CardHints
from rules import ruleMatch


HOST = ''
PORT = 1024


def addPlayers(game, numPlayers: int) -> list():
    clientSockets = []
    for client in range(numPlayers):
        game.addPlayer("player"+str(client))
    
    for client in range(numPlayers):
        game.setPlayerReady("player"+str(client))



def commandShow(world, playerName: str):  # SHOW (just first time)
    rqst = GameData.ClientGetGameStateRequest(playerName)
    data =world.satisfyRequest(rqst, playerName)
    data = data[0]
    if type(data) is GameData.ServerGameStateData:
        return data
    return None


def manageHintResponse(world, playerName, dest, typ, value, hintTable, handSize):
    rqst = GameData.ClientHintData(playerName, dest, typ, value)
    data = world.satisfyRequest(rqst, playerName)
    data = data[1]
    if type(data) is GameData.ServerHintData:

        manageHintTableHintUpdate(data, hintTable, handSize)
        return 1, None
    elif type(data) is GameData.ServerGameOver:
        stdout.flush()
        return 0, data.score
    else:
        print("Some error occurred with hint... this should not happen")
        print(type(data))
        os._exit(-1)


def managePlay(world, playerName, cardPos):
    rqst = GameData.ClientPlayerPlayCardRequest(playerName, cardPos)
    data = world.satisfyRequest(rqst, playerName)
    data = data[1]
    if type(data) is GameData.ServerPlayerMoveOk:
        return 1, data.card
    if type(data) is GameData.ServerPlayerThunderStrike:

        return -1, None
    if type(data) is GameData.ServerGameOver:
        return 0, data.score


def manageDiscardResponse(world, playerName, cardPos):
    rqst = GameData.ClientPlayerDiscardCardRequest(playerName, cardPos)
    data = world.satisfyRequest(rqst, playerName)
    data = data[1]
    if type(data) is GameData.ServerActionValid:
        dataOk = True
        # print("Action valid!")
        # print("Current player: " + data.player)
        return 1, None
    elif type(data) is GameData.ServerGameOver:
        # print("Game over!")
        # print("Start new game")
        return 0, data.score
    else:
        print("Some error occurred with discard... this should not happen")
        print(type(data))
        os._exit(-1)

# Function that updates the HintTable after an Hint


def manageHintTableHintUpdate(data, hintTable, slots):
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


def manageHintTableUpdate(playerNum: int, slotNum: int, hintTable, slots):

    # for s in range(slotNum, slots-1):
    #     hintTable[playerNum][s] = hintTable[playerNum][s+1]
    # s += 1
    # hintTable[playerNum][s] = CardHints(slots)

    hintTable[playerNum].pop(slotNum)
    hintTable[playerNum].append(CardHints(slots))

# based on the 5 stacks of cards, says if one card is playable


#########  RULES HERE JUST TO TEST, THEN TO BE MOVED TO rules.py  ###########



def hintTableInit(numPlayers, hintTable, slots):
    for p in range(numPlayers):
        for slot in range(slots):
            hintTable[p][slot] = CardHints(slots)


def updateCardsAge(hintTable, numPlayers, slots):

    for p in range(numPlayers):
        for slot in range(slots):
            hintTable[p][slot].incrementAge()

def updateTableCards(card, tableCards):

    tableCards[card.color].append(card)
    try:
        assert(len(tableCards[card.color]) <= 5)
    except AssertionError:
        print(f"ERROR: stack of color: {card.color} has {len(tableCards[card.color])} cards")

def clearTableCards(tableCards):
    for c in tableCards.keys():
        tableCards[c].clear()



def simulateGames2(numPlayers, numGames, rules):
    start = time.time()
    numslots = {1: 5, 2: 5, 3: 5, 4: 4, 5: 4}

    run = True
    hintTable = [[0 for x in range(numslots[numPlayers])]
                 for y in range(numPlayers)]        # Array of shape H=[#Players][#Slots]

    colorDict = {0: 'red', 1: 'yellow', 2: 'green', 3: 'blue', 4: 'white'}
    colorsName = ['red', 'yellow', 'green', 'blue', 'white']

    discardedCards = {c: [0, 0, 0, 0, 0] for c in colorsName}
    uselessCards = {c: 0 for c in colorsName}

    tableCards = {c: [] for c in colorsName}     # dict for storing the stacks of cards on the table

    # 3 one's for every color, 2 two's, three's and four's, and 1 five's
    CARD_LIMIT = [3, 2, 2, 2, 1]

    world = Game()

    addPlayers(world, numPlayers)
    world.start()


    run = True
    players = []

    # init HintTable => will be updated on hint or play or discard
    hintTableInit(numPlayers, hintTable, numslots[numPlayers])

    rulesArray = rules
    
    # START GAME
    it = 0
    endGames = 0
    totScore = 0

    while run:
        for client in range(numPlayers):
            playerName = "player" + str(client)

            # Before starting, every player is doing show in order to update infos
            game = commandShow(world, playerName)
            players = game.players
            tableCards = game.tableCards
            others = [p.hand for i, p in enumerate(
                players) if i != client]

            others = [p.hand for p in players]

            # increment all the cards' age in the hand of players by one
            updateCardsAge(hintTable, numPlayers, game.handSize)
            good = False
        

            if (game.handSize == 0):
                world._Game__nextTurn()
                continue
        
            for i, r in enumerate(rulesArray):
                move, cardInfo = ruleMatch(r, client, hintTable, tableCards,
                                           game.handSize, others,
                                           game.discardPile, game.players, game.usedNoteTokens)
                if cardInfo != None and cardInfo[0] != None:
                    good = True
                    break
            if not good:
                move = "play"
                cardInfo = [0]
            assert(type(cardInfo[0] == int))

            # 2. take action
            if move == "play":
                cardPos = cardInfo[0]
                
                res, score = managePlay(world, playerName, cardPos)

                if res == 0:
                    hintTableInit(numPlayers, hintTable, game.handSize)

                    endGames += 1
                    totScore += score
                    world = Game()
                    addPlayers(world, numPlayers)
                    world.start()
                    #run = False
                    break
                # shift hint slot when playing a card
                manageHintTableUpdate(
                    client, cardPos, hintTable, game.handSize)

            elif move == "hint":

                typ = 'color' if type(cardInfo[1]) == str else 'value'
                dest = "player"+str(cardInfo[0])
                value = cardInfo[1]

                                                                                                #change this in game.handSize
                res, score = manageHintResponse(world, playerName, dest, typ, value, hintTable, game.handSize)
                
                # This means game ended, so.. restart
                if res == 0:
                    endGames += 1
                    totScore += score
                    hintTableInit(numPlayers, hintTable,
                                  game.handSize)

                    world = Game()
                    addPlayers(world, numPlayers)
                    world.start()

                    #run = False
                    break
            elif move == "discard":
                cardPos = cardInfo[0]
               
                if(cardInfo[0] == None):
                    os._exit(-1)
                
                res, score = manageDiscardResponse(world, playerName, cardPos)

                # This means game ended, so.. restart
                if res == 0:
                    endGames += 1
                    totScore += score
                    hintTableInit(numPlayers, hintTable,
                                  game.handSize)
                    world = Game()
                    addPlayers(world, numPlayers)
                    world.start()
                    #run = False
                    break
                manageHintTableUpdate(
                    client, cardPos, hintTable, game.handSize)
                
            it += 1
            if(endGames == numGames):
                run = False
                break
    return totScore/endGames
