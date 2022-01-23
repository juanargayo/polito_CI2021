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

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

hintState = ("", "")


def managePlay(playerName: str):
    print(f"managePlay: thread+ {playerName[-1]}")


def manageServerResp(playerName: str, s: socket):
    print("manageServerResp: thread"+playerName[-1])

    while run:
        dataOk = False
        data = s.recv(DATASIZE)
        if not data:
            continue
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) +
                  "/" + str(data.connectedPlayers) + " players")
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start!")
            s.send(GameData.ClientPlayerReadyData(
                playerName).serialize())
            status = statuses[1]
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
            print("Note tokens used: " +
                  str(data.usedNoteTokens) + "/8")
            print("Storm tokens used: " +
                  str(data.usedStormTokens) + "/3")
        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)
        if type(data) is GameData.ServerActionValid:
            dataOk = True
            print("Action valid!")
            print("Current player: " + data.player)
        if type(data) is GameData.ServerPlayerMoveOk:
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)
        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")
        if type(data) is GameData.ServerHintData:
            dataOk = True
            print("Hint type: " + data.type)
            print("Player " + data.destination +
                  " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))
        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)
        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            #run = False
            print("Ready for a new game!")
        if not dataOk:
            print("Unknown or unimplemented data type: " + str(type(data)))
        print("[" + playerName + " - " + "Lobby" + "]: ", end="")
        stdout.flush()


def main():
    global status
    numPlayers = 8
    serverResponseThreads = []
    clientPlayThreads = []
    print("start simulation")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    for client in range(numPlayers):
        playerName = "player" + str(client)
        print(f"main: {playerName}")

        request = GameData.ClientPlayerAddData(playerName)
        s.send(request.serialize())
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerConnectionOk:
            print("Connection accepted by the server. Welcome " + playerName)
            print("[" + playerName + " - " + status + "]: ", end="")
            serverResponseThreads.append(Thread(target=manageServerResp, args=(
                "player" + str(client), s, )))
            clientPlayThreads.append(
                Thread(target=managePlay, args=("player" + str(client), )))

    for client in range(numPlayers):
        serverResponseThreads[client].start()
        clientPlayThreads[client].start()

        serverResponseThreads[client].join()
        clientPlayThreads[client].join()


if (__name__ == "__main__"):
    main()
