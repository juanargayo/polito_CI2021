from os import stat
import socket
from sys import stdout
from threading import Thread
from unittest.result import STDOUT_LINE

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
        print("Current player: " + data.currentPlayer)
        print("Player hands: ")
        for p in data.players:
            print(p.toClientString())
            # SAVING INFORMATIONS => cards[0] avremo la hand di player0
        print("Cards in your hand: " + str(data.handSize))
        print("Table cards: ")
        for pos in data.tableCards:
            print(pos + ": [ ")
            for c in data.tableCards[pos]:
                print(c.toClientString() + " ")
                print("]")
        print("Discard pile: ")
        for c in data.discardPile:
            print("\t" + c.toClientString())
        print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
        print("Storm tokens used: " + str(data.usedStormTokens) + "/3")


# currently not properly working...
def commandPlay(cardPos: int, playerName: str, s: socket):
    global run
    s.send(GameData.ClientPlayerPlayCardRequest(
        playerName, cardPos).serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)

    if type(data) is GameData.ServerPlayerMoveOk:
        return (1, None)

    if type(data) is GameData.ServerPlayerThunderStrike:
        return (0, None)

    if type(data) is GameData.ServerGameOver:
        stdout.flush()
        return -1, data.score
        print(data.message)
        print(data.score)
        print(data.scoreMessage)
    if type(data) is GameData.ServerGameStateData:
        dataOk = True
        print("Current player: " + data.currentPlayer)
        print("Player hands: ")
        for p in data.players:
            print(p.toClientString())
        print("Cards in your hand: " + str(data.handSize))
        print("Table cards: ")
        for pos in data.tableCards:
            print(pos + ": [ ")
        for c in data.tableCards[pos]:
            print(c.toClientString() + " ")
            print("]")
            print("Discard pile: ")
            for c in data.discardPile:
                print("\t" + c.toClientString())
            print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
            print("Storm tokens used: " + str(data.usedStormTokens) + "/3")


run = True

numPlayers = 3
slots = getNumSlots(numPlayers)

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]
hintState = ("", "")

plays = [0]  # just to debug

cards = []
hintTable = []


def main():
    global status
    global numPlayers
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
    for player in players:
        hintTable.append(CardHints(slots))

    print("HINT TABLE:")
    print(hintTable[0].values)
    print(hintTable[0].colors)

    # init table_cards = {}
    # init scarti = {}

    # START GAME

    while run:
        for client in range(numPlayers):
            playerName = "player" + str(client)
            s = clientSockets[client]

            print(f"\nfor cycle of player{str(client)}\n")

            #commandShow(playerName, s)

            # 1. think a move
            move = "hint"

            # 2. take action

            if move == "play":
                # (PLAY ALWAYS CARD 0)
                cardPos = 0
                s.send(GameData.ClientPlayerPlayCardRequest(
                    playerName, cardPos).serialize())
                data = s.recv(DATASIZE)
                data = GameData.GameData.deserialize(data)
                if type(data) is GameData.ServerPlayerMoveOk:
                    dataOk = True
                    print("Nice move!")
                    print("Current player: " + data.player)
                if type(data) is GameData.ServerPlayerThunderStrike:
                    dataOk = True
                    print("OH NO! The Gods are unhappy with you!")
                if type(data) is GameData.ServerGameOver:
                    dataOk = True
                    print(data.message)
                    print(data.score)
                    print(data.scoreMessage)
                    stdout.flush()
                    run = False
                    print("Ready for a new game!")
                    break
            elif move == "hint":
                # (GIVE HINT) 
                # 1. send a request

                cardPos = 0
                typ = "color"
                dest = "player1"

                # value = ? => Find value of the first card of player1
                value = players[1].hand[0].color

                # Debug purpose
                if playerName == "player1":
                    continue

                
                # Source Hint
                s.send(GameData.ClientHintData(
                    playerName, dest, typ, value).serialize())

                data = s.recv(DATASIZE)
                data = GameData.GameData.deserialize(data)

                if type(data) is not GameData.ServerHintData:
                    print("Invalid action, terminating", type(data))
                    return
                print("Hint type: " + data.type)
                print("Player " + data.destination +
                      " cards with value " + str(data.value) + " are:")
                for i in data.positions:
                    print("\t" + str(i))
                
                for i in data.positions:
                    if data.type == "value":
                        hintTable[int(data.destination[-1:])].directHintValue(i)
                    elif data.type == "color":
                        hintTable[int(data.destination[-1:])].directHintColor(i)
                    else:
                        print("ERROR: Wrong hint type")

                #Just for testing
                print("\nHINT TABLE (after update):")
                print(f"values: {hintTable[int(data.destination[-1:])].values}")
                print(f"colors: {hintTable[int(data.destination[-1:])].colors}\n")

                # Dest Hint (Other data is sent from server)
                if playerName == "player0":
                    s = clientSockets[1]
                    data = s.recv(DATASIZE)
                    data = GameData.GameData.deserialize(data)

                    if type(data) is not GameData.ServerHintData:
                        return
                    print("Hint type: " + data.type)
                    print("Player " + data.destination +
                          " cards with value " + str(data.value) + " are:")
                    for i in data.positions:
                        print("\t" + str(i))
                
                #2. Put hint info in HINT TABLE
                #3. Check if token is correctly decreasing
                #4. Remember to update info after play or discard


                time.sleep(3)

            #elif move == "discard":
                #Yet to implement. We have to be aware of many things, e.g. when getting the new card, updating the hint table.

        time.sleep(1)


if (__name__ == "__main__"):
    main()


# That's how commandPlay could be used
# res = commandPlay(cardPos, playerName, s)

    # score = res[0]
    # res = res[0]
    # print(res)
    # if res == 0:
    #     print("Nice move!")
    # elif res == 1:
    #     print("OH NO! The Gods are unhappy with you!")
    # else:
    #     run = False
    #     print("score: ", score)
    #     print("Ready for a new game!")
    #     break
