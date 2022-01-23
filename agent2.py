from os import stat
import socket
from sys import stdout
from threading import Thread
from unittest.result import STDOUT_LINE
import GameData
import time
from constants import DATASIZE

HOST = ''
PORT = 1024


run = True

numPlayers = 3

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]
hintState = ("", "")

plays = [0]  # just to debug



def main():
    global status
    global numPlayers
    numPlayers = 6
    serverResponseThreads = []
    clientPlayThreads = []
    print("start simulation")
    """ s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT)) """
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
        print("[" + playerName + " - " + status + "]: ")

        clientSockets.append(s)

    for client in range(numPlayers):
        playerName = "player" + str(client)
        s = clientSockets[client]

        # GET CLIENTS READY
        s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)

        if type(data) is not GameData.ServerPlayerStartRequestAccepted:
            return
        print("Ready: " + str(data.acceptedStartRequests) +
              "/" + str(data.connectedPlayers) + " players")
    for client in range(numPlayers):
        playerName = "player" + str(client)
        s = clientSockets[client]

        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is not GameData.ServerStartGameData:
            return
        s.send(GameData.ClientPlayerReadyData(playerName).serialize())

    status = statuses[1]
    print("Game start!")

    run = True
    command = "show"
    while run:
        for client in range(numPlayers):
            playerName = "player" + str(client)
            s = clientSockets[client]

            # SHOW
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

            # think a move
            

            # make move (need to add hint and discard)
            card = 0

            s.send(GameData.ClientPlayerPlayCardRequest(
                playerName, card).serialize())

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

    # s.send(GameData.ClientPlayerReadyData(playerName).serialize())
    # status = statuses[1]"""
#         serverResponseThreads.append(Thread(target=manageServerResp, args=(
#             "player" + str(client), s, )))
#         clientPlayThreads.append(
#             Thread(target=managePlay, args=("player" + str(client), s, )))

# for client in range(numPlayers):
#     serverResponseThreads[client].start()
#     clientPlayThreads[client].start()

# serverResponseThreads[client].join()
# clientPlayThreads[client].join()


if (__name__ == "__main__"):
    main()
