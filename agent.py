#!/usr/bin/env python3

from re import M
import site
from sys import argv, stdout
from threading import Thread
import GameData
import socket
from simulation import hintTableInit, manageHintTableHintUpdate, manageHintTableUpdate, updateCardsAge
from constants import *
import os
import time

from rules import ruleMatch


if len(argv) < 4:
    #exit(-1)
    playerName = "AntoJuan" # For debug
    ip = HOST
    port = PORT
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])

run = True

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]


RULES = [15, 9, 17,  2,  5, 16,  3,  6, 10, 14,  7,  1, 21, 11, 22, 18,  8, 20, 13, 12,  4,  0, 19]

myTurn = False
infos = None

WAIT_SECONDS = 3

numslots = {1: 5, 2: 5, 3: 5, 4: 4, 5: 4}

firstShow = True
hintTable = [[]]
clientId = -1
numPlayers = 0
playerNames = {}

def manageInput(s: socket):
    global run
    global status
    global myTurn
    global infos
    global hintTable
    global clientId
    global numPlayers
    global playerNames

    command = ""
    while(command != "ready"):
        command = input()
        if command=="ready":
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
            status = statuses[1]
        else:
            print("Maybe you wanted to type \"ready\"?")

    it = 0
    while run:

        if it == 0 and firstShow:
            command = "show"
        else:
            command = "wait"
        if(myTurn):
            print("Mmmm, let me think a move...")
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            time.sleep(1)
            others = [p.hand for p in infos.players]
            updateCardsAge(hintTable, numPlayers, infos.handSize)

            #Now choose move
            good = False

            for r in RULES:
                move, cardInfo = ruleMatch(r, clientId, hintTable, infos.tableCards,
                                           infos.handSize, others,
                                           infos.discardPile, infos.players, infos.usedNoteTokens)
                if cardInfo != None and cardInfo[0] != None:
                    good = True
                    break
            if not good:
                print("No rules found :(")
                move = "discard"
                cardInfo = [0]

            #take action
            if move == "play":
                cardPos = cardInfo[0]
                command = "play " + str(cardPos)

            elif move == "hint":
                typ = 'color' if type(cardInfo[1]) == str else 'value'
                dest = infos.players[cardInfo[0]].name
                value = cardInfo[1]
                command = f"hint {typ} {dest} {value}"

            elif move == "discard":
                cardPos = cardInfo[0]
                command = "discard " + str(cardPos)

            else:
                "Something is wrong... returning"
                os._exit(-1)
        
        if command == "show" and status == statuses[1]:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        elif command.split(" ")[0] == "discard" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerDiscardCardRequest(playerName, cardOrder).serialize())
                myTurn = False
            except:
                print("Maybe you wanted to type 'discard <num>'?")
                continue
        elif command.split(" ")[0] == "play" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerPlayCardRequest(playerName, cardOrder).serialize())
                myTurn = False

            except:
                print("Maybe you wanted to type 'play <num>'?")
                continue
        elif command.split(" ")[0] == "hint" and status == statuses[1]:
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    print("Error: type can be 'color' or 'value'")
                    continue
                value = command.split(" ")[3].lower()
                if t == "value":
                    value = int(value)
                    if int(value) > 5 or int(value) < 1:
                        print("Error: card values can range from 1 to 5")
                        continue
                else:
                    if value not in ["green", "red", "blue", "yellow", "white"]:
                        print("Error: card color can only be green, red, blue, yellow or white")
                        continue
                s.send(GameData.ClientHintData(playerName, destination, t, value).serialize())
                myTurn = False
            
            except:
                print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                continue
        elif command == "":
            print("[" + playerName + " - " + status + "]: ", end="")
        elif command == "wait":
            print("waiting for my turn...")
            time.sleep(WAIT_SECONDS)
            continue
        else:
            print("Unknown command: " + command)
            continue
        it += 1
        stdout.flush()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    request = GameData.ClientPlayerAddData(playerName)
    s.connect((HOST, PORT))
    s.send(request.serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + status + "]: ", end="")

    Thread(target=manageInput, args = (s, )).start()
    while run:
        dataOk = False
        data = s.recv(DATASIZE)
        if not data:
            continue
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start!")
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = statuses[1]
        if type(data) is GameData.ServerGameStateData:
            dataOk = True
            if firstShow:
                print("Current player: " + data.currentPlayer)
                infos = data
                numPlayers = len(data.players)
                playerNames = {p.name: i for i, p in enumerate(data.players)}
                clientId = playerNames[playerName]
                hintTable = [[0 for x in range(numslots[numPlayers])]
                 for y in range(numPlayers)]        # Array of shape H=[#Players][#Slots]
                hintTableInit(numPlayers, hintTable, numslots[numPlayers])
                firstShow = False            
            if(data.currentPlayer == playerName):
                myTurn = True
                infos = data
                
        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)
        if type(data) is GameData.ServerActionValid:
            dataOk = True
            print("Action valid!")
            myTurn = False
            print("Current player: " + data.player)
            id = playerNames[data.lastPlayer]
            manageHintTableUpdate(
                    id, data.cardHandIndex, hintTable, data.handLength)
            if(data.player == playerName):
                myTurn = True
        if type(data) is GameData.ServerPlayerMoveOk:
            id = playerNames[data.lastPlayer]
            manageHintTableUpdate(
                    id, data.cardHandIndex, hintTable, data.handLength)
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)
            if(data.player == playerName):
                myTurn = True
            
        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            myTurn = False
            print("OH NO! The Gods are unhappy with you!")
            if(data.player == playerName):
                myTurn = True
        if type(data) is GameData.ServerHintData:
            dataOk = True
            print("Hint type: " + data.type)
            print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
            destId = playerNames[data.destination]
            for i in data.positions:
                print("\t" + str(i))
            myTurn = False
            manageHintTableHintUpdate(
                    data, hintTable, numslots[numPlayers], destId )
        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)
        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            hintTableInit(numPlayers, hintTable, numslots[numPlayers])


            myTurn = False
            #run = False
            print("Ready for a new game!")
        if not dataOk:
            print("Unknown or unimplemented data type: " +  str(type(data)))
        print("[" + playerName + " - " + status + "]: ", end="")
        stdout.flush()