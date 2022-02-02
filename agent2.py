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
from rules import discardHighest, discardIfCertain, discardNoInfo, discardNoInfoOldest, discardOldest, discardSafe, discardUseless, hintFives, hintMostInfo, hintMostInfo2, hintOld, hintOnes, hintPartiallyKnown, hintPlayable, hintRandom, hintUnkown, hintUseful, hintUseless, playProbablySafeCard, playIfCertain, playSafeCard, playSafeCard2

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
        print(
            f"card played: {(data.card).toString()} , card.value: {data.card.value}")
        # print(f"cardColor: {data.card.color}")
        # print(f"lastPlayer: {data.lastPlayer} player: {data.player} handLength: {data.handLength}")
        return 1, None
    if type(data) is GameData.ServerPlayerThunderStrike:
        print("OH NO! The Gods are unhappy with you!")
        print(
            f"card played: {(data.card).toString()} , card.value: {data.card.value}")
        return -1, None
    if type(data) is GameData.ServerGameOver:
        print(data.message)
        print(data.score)
        print(data.scoreMessage)
        stdout.flush()
        print("Ready for a new game!")
        return 0, data.score


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

# based on the 5 stacks of cards, says if one card is playable


def isPlayable(cardNum, cardColor, tableCards) -> bool:
    # print(f"The tableCards at isPlayable is: {tableCards}")
    # print(f"tableCards[cardColor]: {tableCards[cardColor]} , len(tableCards[cardColor]): {len(tableCards[cardColor])}")
    # print(f"cardNum: {cardNum} , cardColor: {cardColor}")
    # TODO: Check if its possible that there are empty places in the array that throws the len() calculation
    if(len(tableCards[cardColor]) == cardNum-1):
        print("I can play the card")
        return True
    return False


run = True

numPlayers = 5
slots = getNumSlots(numPlayers)

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]
cards = []

hintTable = [[0 for x in range(getNumSlots(numPlayers))]
             for y in range(numPlayers)]        # Array of shape H=[#Players][#Slots]

tableCards = {}     # dict for storing the stacks of cards on the table

colorDict = {0: 'red', 1: 'yellow', 2: 'green', 3: 'blue', 4: 'white'}
colorsName = ['red', 'yellow', 'green', 'blue', 'white']

discardedCards = {c: [0, 0, 0, 0, 0] for c in colorDict}
uselessCards = {c: 0 for c in colorDict}

# 3 one's for every color, 2 two's, three's and four's, and 1 five's
CARD_LIMIT = [3, 2, 2, 2, 1]


#########  RULES HERE JUST TO TEST, THEN TO BE MOVED TO rules.py  ###########


def discardLeastLikelyToBeNecessary(player, hintTable, tableCards):

    _slots = [s for s in range(slots)]
    necessarySlots = []
    notPlayableSlots = []

    for slot in _slots:
        if(any(el == 1 for el in hintTable[slot].values.values())
                and any(el == 1 for el in hintTable[slot].colors.values())):
            try:
                cardNum = list(hintTable[slot].values.values()).index(1)+1
                cardColor = colorDict[list(
                    hintTable[slot].colors.values()).index(1)]

                # Card may be playable in the future
                if len(tableCards[cardColor]) < cardNum:
                    # Test if the card is the last of its kind.
                    if discardedCards[cardColor][cardNum]+1 == CARD_LIMIT[cardNum-1]:
                        # For this, I see if the discardedCards of that card are one from being all discarded/used
                        necessarySlots.append(slot)
                else:
                    notPlayableSlots.append(slot)
                    continue
            except ValueError:
                print(
                    f"discardLeastLikelyToBeNecessary: No known card value in slot: {slot}")
                continue

    notNecessarySlots = [s for s in _slots if s not in [
        *necessarySlots, *notPlayableSlots]]

    if (notPlayableSlots):
        return random.choice(notPlayableSlots)
    else:
        return None


def DiscardProbablyUselessCard():
    # TODO: To be done. Look def in framework
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

            print(f"the tableCards are: {tableCards}")

            # increment all the cards' age in the hand of players by one
            updateCardsAge(hintTable)

            # time.sleep(40000)

            # 1. think a move (All players hinting if possible,  but player1)
            # move = "hint" if (
            #     playerName != "player1" and game.usedNoteTokens < 8) else "discard"
            # move = "hint" if client % 2 == 0 and playerName != "player1" and game.usedNoteTokens < 8 else "play"    #just to test and alternate
            #move = "hint" if game.usedNoteTokens < 8 and client < 4 else "play"
            if client < 2 and game.usedNoteTokens > 0:
                move = "discard"
            elif client < 4 and game.usedNoteTokens < 8:
                move = "hint"
            else:
                move = "play"
            # move = "hint" if (
            #     playerName != "player1" and game.usedNoteTokens < 8) else "discard"

            handSize = game.handSize
            print("HANDSIZE: ", game.handSize)

            # 2. take action
            if move == "play":

                # (PLAY ALWAYS CARD 0)

                # probableSlot = playIfCertain(
                #     client, hintTable[client], tableCards, handSize)
                # #probableSlot = playSafeCard(hintTable[client], tableCards, handSize)
                # probableSlot = playSafeCard2(hintTable[client], game.tableCards, handSize, [
                # x.hand for x in players], game.discardPile)
                probableSlot = playProbablySafeCard(hintTable[client], game.tableCards, handSize, [
                    x.hand for x in players], game.discardPile, 0.5)

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
                    res, score = managePlayResponse(data)

                # This means game ended, so.. restart
                if res == 0:
                    print(f"Score: {score}")
                    hintTableInit()

                    for i in range(100):
                        print(".", end="")
                        time.sleep(0.1)
                    print("\n"*100)
                    print("Start new game")

                    #run = False
                    break

                # shift hint slot when playing a card
                manageHintTableUpdate(client, cardPos)

            elif move == "hint":
                # (GIVE HINT)
                # 1. send a request

                # dest, value = hintPartiallyKnown(hintTable, tableCards, client, players)
                # typ = "value" if type(value) == int else "color"

                #dest, value = hintOnes(hintTable, client, players )

                #dest, value = hintUseful(hintTable, tableCards, client, players)
                #dest, value = hintOld(hintTable, tableCards, client, players)
                #dest, value = hintPlayable(hintTable, tableCards, client, players)
                #dest, value = hintUseless(hintTable, tableCards, client, players)
                # dest, value = hintFives(hintTable, client, players)
                # dest, value = hintMostInfo(hintTable, client, players)
                # dest, value = hintMostInfo2(hintTable, client, players)
                #dest, value = hintRandom(client, players)
                dest, value = hintUnkown(hintTable, client, players)
                if dest != None:
                    typ = "value" if type(value) == int else "color"
                    dest = "player"+str(dest)
                else:
                    value = -1  # players[0].hand[0].value
                    typ = "value"
                    dest = "player0"

                print(
                    f"Sending value \"{value}\" of type \"{typ}\" at dest {dest}")

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
                # discard = discardUseless(
                #     hintTable[client], game.discardPile, handSize)

                #discard = discardSafe(hintTable[client], tableCards, handSize)
                #discard = discardUselessSafe(hintTable[client], game.discardPile, handSize)
                # discard = discardIfCertain(
                #     hintTable[client], tableCards, handSize)
                #discard = discardHighest(hintTable[client], handSize)
                discard = discardOldest(hintTable[client], handSize)
                discard = discardNoInfo(hintTable[client], handSize)
                discard = discardNoInfoOldest(hintTable[client], handSize)


                discard = discard if discard != None else 3
                print(f"discard", {discard})
                #discardOrder = 4
                s.send(GameData.ClientPlayerDiscardCardRequest(
                    playerName, discard).serialize())
                data = s.recv(DATASIZE)
                res = manageDiscardResponse(data)
                if res:
                    manageHintTableUpdate(client, discard)
                    # updateDiscardedUselessCards(data.card)

                for c in range(numPlayers):
                    if c == client:
                        continue
                    data = clientSockets[c].recv(DATASIZE)
                    res = manageDiscardResponse(data)

                # this means GameOver
                if res == 0:
                    break
            time.sleep(2)
            it += 1


if (__name__ == "__main__"):
    main()
