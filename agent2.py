from os import stat
import os
import socket
from sys import stdout
from threading import Thread
from unittest.result import STDOUT_LINE
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


def readGame(numPlayers: int, clientSockets: socket):
    cards = []
    playerName = "player0"
    client = 0
    s = clientSockets[client]

    # send SHOW
    s.send(GameData.ClientGetGameStateRequest(
        playerName).serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)

    if type(data) is GameData.ServerGameStateData:
        dataOk = True
        return data
    return None


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
        return 1
    if type(data) is GameData.ServerPlayerThunderStrike:
        print("OH NO! The Gods are unhappy with you!")
        return -1
    if type(data) is GameData.ServerGameOver:
        print(data.message)
        print(data.score)
        print(data.scoreMessage)
        stdout.flush()
        print("Ready for a new game!")
        return 0

# Function that updates the HintTable after an Hint


def manageHintTableHintUpdate(data):
    global numPlayers
    global hintTable
    data = GameData.GameData.deserialize(data)
    for i in range(getNumSlots(numPlayers)):
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


def manageHintTableUpdate(data):
    pass


run = True

numPlayers = 3
slots = getNumSlots(numPlayers)

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]
hintState = ("", "")

plays = [0]  # just to debug

cards = []

hintTable = [[0 for x in range(getNumSlots(numPlayers))] for y in range(
    numPlayers)]  # Array of shape H=[#Players][#Slots]


def playIfCertain(playerNum: int, hintTable):
    # ok to import them? is there a better way?
    for slot in range(getNumSlots(numPlayers)):

        if(any(el == 1 for el in hintTable[slot].values.values())
                & any(el == 1 for el in hintTable[slot].colors.values())):
            print(f"Found playable card for slot number {slot}:")
            return slot  # In this case, we are playing the first playable card
            # of the player, there maybe more than one, we can make
            # an array and then by some metric (or random) choose one


def hintTableInit():
    global numPlayers
    global hintTable
    for p in range(numPlayers):
        for slot in range(getNumSlots(numPlayers)):
            hintTable[p][slot] = CardHints(slots)


def main():
    global status
    global numPlayers
    global hintTable
    print("start simulation")
    clientSockets = []

    clientSockets = connectClients(numPlayers)
    getReadyClients(numPlayers, clientSockets)

    print("Game start!")

    run = True
    command = "show"
    players = []
    # SAVE INFORMATIONS

    # save cards => to update on play or discard

    # with game struct
    # we can take what we need (!!! except additional infos, and card of the current_player (now is player0) ) from here
    #  -> Should be updated automatically => but can't see your hand in your own turn

    game = readGame(numPlayers, clientSockets)

    players = game.players
    print(players[1].name)

    player = players[1]
    for card in range(len(player.hand)):
        print(player.hand[card].toString())
        print()

    # init card_infos => !!! to update on hint or play or discard
    hintTableInit()

    print("HINT TABLE player0:")
    for slot in range(getNumSlots(numPlayers)):
        print(hintTable[0][slot].values)
        print(hintTable[0][slot].colors)

    time.sleep(0)
    # init table_cards = {}
    # init scarti = {}

    # START GAME
    it = 0
    while run:
        for client in range(numPlayers):
            playerName = "player" + str(client)

            s = clientSockets[client]

            print(f"\nfor cycle of player{client}\n")

            # Before starting, every player is doing show in order to update infos
            game = commandShow(playerName, s)
            players = game.players

            # 1. think a move (All players hinting if possible,  but player1)
            move = "hint" if (
                playerName != "player1" and game.usedNoteTokens < 8) else "play"

            # 2. take action

            if move == "play":
                # (PLAY ALWAYS CARD 0)
                cardPos = 0
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
                    break
                # without this multiple occurrencies will happen because slot will change
                # hintTableUpdate()

            elif move == "hint":
                # (GIVE HINT)
                # 1. send a request

                cardPos = 0
                typ = "value"
                dest = "player1"

                # value = ? => Find value of the first card of player1
                value = players[1].hand[0].value if typ == "value" else players[1].hand[0].color
                print(value)
                time.sleep(2)

                # Debug purpose, just checking that player1 is not hinting (pretty useless..)
                if playerName == "player1":
                    print("There must be an error")
                    time.sleep(10)
                    continue

                # Source Hint
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

                # hard code moves, just to test the rule , it might give problems when there are teo correct colors for card 0
                # hintTable[1][0].directHintColor('red')
                # hintTable[1][0].directHintValue(0)

                # Just for testing
                print("\nHINT TABLE (after update):")
                for slot in range(getNumSlots(numPlayers)):
                    print(
                        f"values: {hintTable[1][slot].values}")
                    print(
                        f"colors: {hintTable[1][slot].colors}\n")

                # playableCard = playIfCertain(1, hintTable[1])
                # print(f"\n the playable card is: {playableCard}")

                # 2. Put hint info in HINT TABLE (done)
                # 3. Check if token is correctly decreasing (done)
                # 4. Remember to update info after play or discard (to do)

            # elif move == "discard":
                # Yet to implement. We have to be aware of many things, e.g. when getting the new card, updating the hint table.

        time.sleep(3)


if (__name__ == "__main__"):
    main()
