from os import stat
import os
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
#########  RULES HERE JUST TO TEST, THEN TO BE MOVED TO rules.py  ###########

def playIfCertain(playerNum: int, hintTable):
    # ok to import them? is there a better way?
    for slot in range(getNumSlots(numPlayers)):
        if(any(el == 1 for el in hintTable[slot].values.values())
                & any(el == 1 for el in hintTable[slot].colors.values())):
            # print(f"Found playable card for slot number {slot}:")
            # print(f"the type(hintTable[slot].values.values()): {type(hintTable[slot].values.values())}")
            # print(f"list(hintTable[slot].values.values()).index(1)+1: {list(hintTable[slot].values.values()).index(1)+1}")
            # print(f"list(hintTable[slot].colors.values()).index(1): {list(hintTable[slot].colors.values()).index(1)}")
            cardNum = list(hintTable[slot].values.values()).index(1)+1
            cardColor = colorDict[list(hintTable[slot].colors.values()).index(1)]
            print(f"cardNum: {cardNum} , cardColor: {cardColor}")
            if(isPlayable(cardNum, cardColor, tableCards)):
                print("The card is playable")
                return slot
            else:
                print("The card is NOT playable")
                return False
                                        # In this case, we are playing the first playable card
                                        # of the player, there maybe more than one, we can make
                                        # an array and then by some metric (or random) choose one

def isPlayable(cardNum, cardColor, tableCards) -> bool:       #based on the 5 stacks of cards, says if one card is playable
    # print(f"The tableCards at isPlayable is: {tableCards}")
    # print(f"tableCards[cardColor]: {tableCards[cardColor]} , len(tableCards[cardColor]): {len(tableCards[cardColor])}")
    # print(f"cardNum: {cardNum} , cardColor: {cardColor}")
    if(len(tableCards[cardColor])<cardNum):
        print("I can play the card")
        return True

    return False


#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#


def hintTableInit():
    global numPlayers
    global hintTable
    global slots
    for p in range(numPlayers):
        for slot in range(slots):
            hintTable[p][slot] = CardHints(slots)


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

            print(f"the tableCards are: {tableCards}")

            # 1. think a move (All players hinting if possible,  but player1)
            move = "hint" if (
                playerName != "player1" and game.usedNoteTokens < 8) else "discard"

            # 2. take action
            if move == "play":

                # (PLAY ALWAYS CARD 0)

                probableSlot = playIfCertain(client, hintTable[1])
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

                cardPos = 0
                typ = "color"
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
                # hintTable[1][0].directHintColor('red')
                # hintTable[1][0].directHintValue(1)

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
