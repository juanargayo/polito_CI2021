import collections
from distutils.log import debug
from os import stat
import os
import random
import socket
from subprocess import Popen, PIPE
from sys import stdout
from threading import Thread
from unittest.result import STDOUT_LINE
from xmlrpc.client import Boolean
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
    if type(data) is GameData.ServerHintData:
        # print("Hint type: " + data.type)
        # print("Player " + data.destination +
        #       " cards with value " + str(data.value) + " are:")
        # for i in data.positions:
        #     print("\t" + str(i))
        return 1, None
    elif type(data) is GameData.ServerGameOver:
        print("gameover in managehint")
        print(data.message)
        print(data.score)
        print(data.scoreMessage)
        stdout.flush()
        print("Ready for a new game!")
        return 0, data.score
    else:
        print("Some error occurred with hint... this should not happen")
        print(type(data))
        os._exit(-1)


def managePlayResponse(data):
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerMoveOk:
        # print("Nice move!")
        # print("Current player: " + data.player)
        # print(
        #     f"card played: {(data.card).toString()} , card.value: {data.card.value}")
        # # print(f"cardColor: {data.card.color}")
        # print(f"lastPlayer: {data.lastPlayer} player: {data.player} handLength: {data.handLength}")
        return 1, None
    if type(data) is GameData.ServerPlayerThunderStrike:
        #     print("OH NO! The Gods are unhappy with you!")
        #     print(
        #         f"card played: {(data.card).toString()} , card.value: {data.card.value}")
        return -1, None
    if type(data) is GameData.ServerGameOver:
        # print(data.message)
        # print(data.score)
        # print(data.scoreMessage)
        # stdout.flush()
        # print("Ready for a new game!")
        return 0, data.score


def manageDiscardResponse(data):
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerActionValid:
        dataOk = True
        # print("Action valid!")
        # print("Current player: " + data.player)
        return 1, None
    elif type(data) is GameData.ServerGameOver:
        print("Game over!")
        print("Start new game")
        return 0, data.score
    else:
        print("Some error occurred with discard... this should not happen")
        print(type(data))
        os._exit(-1)

# Function that updates the HintTable after an Hint


def manageHintTableHintUpdate(data, hintTable, slots):
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


def manageHintTableUpdate(playerNum: int, slotNum: int, hintTable, slots):

    # for s in range(slotNum, slots-1):
    #     hintTable[playerNum][s] = hintTable[playerNum][s+1]
    # s += 1
    # hintTable[playerNum][s] = CardHints(slots)

    hintTable[playerNum].pop(slotNum)
    hintTable[playerNum].append(CardHints(slots))

# based on the 5 stacks of cards, says if one card is playable


#########  RULES HERE JUST TO TEST, THEN TO BE MOVED TO rules.py  ###########


def DiscardProbablyUselessCard():
    # TODO: To be done. Look def in framework
    return None
#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#


def updateDiscardedUselessCards(cardDiscarded, discardedCards, uselessCards, CARD_LIMIT):
    """ Updates the discardedCards dict that holds a counter for the numberof time each card (value & color) is discarded.
        Also, updates the uslessCards dict that has for every color the value of the card for which all cards of that (value&color) had been discarded"""

    discardedCards[cardDiscarded.color][cardDiscarded.value-1] += 1

    print(f"\nafter discardedCards: {discardedCards}")

    print(f"before uselessCards: {uselessCards}")

    if (discardedCards[cardDiscarded.color][cardDiscarded.value-1] >= CARD_LIMIT[cardDiscarded.value-1]) and cardDiscarded.value > uselessCards[cardDiscarded.color]:

        uselessCards[cardDiscarded.color] = cardDiscarded.value
        print(f"after uselessCards: {uselessCards}")


def hintTableInit(numPlayers, hintTable, slots):
    for p in range(numPlayers):
        for slot in range(slots):
            hintTable[p][slot] = CardHints(slots)


def updateCardsAge(hintTable, numPlayers, slots):

    for p in range(numPlayers):
        for slot in range(slots):
            hintTable[p][slot].incrementAge()


def simulateGames(numPlayers, numGames, rules):

    run = True

    hintTable = [[0 for x in range(getNumSlots(numPlayers))]
                 for y in range(numPlayers)]        # Array of shape H=[#Players][#Slots]

    tableCards = {}     # dict for storing the stacks of cards on the table

    colorDict = {0: 'red', 1: 'yellow', 2: 'green', 3: 'blue', 4: 'white'}
    colorsName = ['red', 'yellow', 'green', 'blue', 'white']

    discardedCards = {c: [0, 0, 0, 0, 0] for c in colorsName}
    uselessCards = {c: 0 for c in colorsName}

    # 3 one's for every color, 2 two's, three's and four's, and 1 five's
    CARD_LIMIT = [3, 2, 2, 2, 1]

    logfile = open("mylogfile.log", "w")

    print("start server")
    server_cmd = f"python3 server.py {numPlayers}\n"
    server_proc = Popen(server_cmd.split(),
                        stdout=logfile,
                        universal_newlines=True
                        )

    print("start simulation")
    clientSockets = []

    print("start simulation")
    time.sleep(1)
    clientSockets = connectClients(numPlayers)
    print("connected")

    getReadyClients(numPlayers, clientSockets)
    print("ready")

    run = True
    players = []

    # init HintTable => will be updated on hint or play or discard
    hintTableInit(numPlayers, hintTable, getNumSlots(numPlayers))

    # rulesArray = [r for r in range(0, 21)]
    # random.shuffle(rulesArray)

    rulesArray = rules

    # START GAME
    it = 0
    endGames = 0
    totScore = 0
    while run:
        for client in range(numPlayers):
            playerName = "player" + str(client)

            s = clientSockets[client]
            print(f"NumPlayers: {numPlayers}, Game: {endGames}/{numGames}")
            print(f"\nplayer{client},it:{it} \n")

            # Before starting, every player is doing show in order to update infos
            game = commandShow(playerName, s)
            players = game.players
            tableCards = game.tableCards
            others = [p.hand for i, p in enumerate(
                players) if i != client]

            others = [p.hand for p in players]

            # increment all the cards' age in the hand of players by one
            updateCardsAge(hintTable, numPlayers, game.handSize)
            good = False
            rulesArray[2] = 10
            for i, r in enumerate(rulesArray):
                print(f"r: {r}(i={i})")
                move, cardInfo = ruleMatch(r, client, hintTable, tableCards,
                                           game.handSize, others,
                                           game.discardPile, game.players, game.usedNoteTokens)
                if cardInfo != None and cardInfo[0] != None:
                    good = True
                    break
            if not good:
                print("No rules found :(")
                move = "discard"
                cardInfo = [0]
            assert(type(cardInfo[0] == int))
            # 2. take action
            if move == "play":

                cardPos = cardInfo[0]
                s.send(GameData.ClientPlayerPlayCardRequest(
                    playerName, cardPos).serialize())
                data = s.recv(DATASIZE)
                res = managePlayResponse(data)

                # this is just ack for other players...
                for c in range(numPlayers):
                    if c == client:
                        continue
                    data = clientSockets[c].recv(DATASIZE)
                    res, score = managePlayResponse(data)

                # This means game ended, so.. restart
                if res == 0:
                    print(f"Score: {score}")
                    hintTableInit(numPlayers, hintTable, game.handSize)

                    endGames += 1
                    totScore += score

                    print("\n"*100)
                    print("Start new game")

                    #run = False
                    break

                # shift hint slot when playing a card
                manageHintTableUpdate(
                    client, cardPos, hintTable, game.handSize)

            elif move == "hint":

                typ = 'color' if type(cardInfo[1]) == str else 'value'
                dest = "player"+str(cardInfo[0])
                value = cardInfo[1]
                print("val:" + str(value))

                # Send request
                s.send(GameData.ClientHintData(
                    playerName, dest, typ, value).serialize())

                # Response must be read first from the sender, then from the others
                data = s.recv(DATASIZE)
                manageHintResponse(data)

                test = type(GameData.GameData.deserialize(
                    data) == GameData.ServerInvalidDataReceived)

                if test:
                    for p in players:
                        print(p.name)
                        for c in p.hand:
                            print(c.value, c.color)
                        print()
                    print()
                    for p in range(len(players)):
                        print("player", p)
                        for slot in range(len(players[p].hand)):
                            print(hintTable[p][slot])
                        print()
                print(f"dest: {dest}, typ: {typ}, value:{value}")

                # HintResponse ACK for the remaining clients
                for c in range(numPlayers):
                    if c == client:
                        continue
                    data = clientSockets[c].recv(DATASIZE)
                    res, score = manageHintResponse(data)

                # This means game ended, so.. restart
                if res == 0:
                    endGames += 1
                    totScore += score
                    print(f"Score: {score}")
                    hintTableInit(numPlayers, hintTable,
                                  getNumSlots(numPlayers))
                    print("\n"*100)
                    print("Start new game")
                    #run = False
                    break

                # Hint table update
                # SICURO CHE VA BENE GETNUMSLOTS????
                manageHintTableHintUpdate(
                    data, hintTable, getNumSlots(numPlayers))

            elif move == "discard":
                discard = cardInfo[0]
                if(cardInfo[0] == None):
                    print("what's happenin'?", cardInfo)
                    os._exit(-1)
                #discardOrder = 4
                s.send(GameData.ClientPlayerDiscardCardRequest(
                    playerName, discard).serialize())
                data = s.recv(DATASIZE)
                res, score = manageDiscardResponse(data)
                if res:
                    manageHintTableUpdate(
                        client, discard, hintTable, getNumSlots(numPlayers))
                    # updateDiscardedUselessCards(data.card)

                # this is just ack for other players...
                for c in range(numPlayers):
                    if c == client:
                        continue
                    data = clientSockets[c].recv(DATASIZE)
                    res, score = manageDiscardResponse(data)

                # This means game ended, so.. restart
                if res == 0:
                    endGames += 1
                    totScore += score
                    print(f"Score: {score}")
                    hintTableInit(numPlayers, hintTable,
                                  getNumSlots(numPlayers))
                    print("\n"*100)
                    print("Start new game")

                    #run = False
                    break
                # time.sleep(0.6)
            it += 1
            if(endGames == numGames):
                run = False
                break

    logfile.flush()
    server_proc.terminate()
    server_proc.wait(0.2)
    return totScore/endGames
