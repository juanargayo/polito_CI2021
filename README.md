# Computational Intelligence 2021-2022

Exam of computational intelligence 2021 - 2022. It requires teaching the client to play the game of Hanabi (rules can be found [here](https://www.spillehulen.dk/media/102616/hanabi-card-game-rules.pdf)).
The idea was to develop a genetic algorithm in order to evolve a rule-based agent. We tried to reproduce the results obtained in this paper https://arxiv.org/abs/1809.09764
The description of the idea is the following: "develop a genetic algorithm that builds rule-
based agents by determining the best sequence of rules from a fixed rule set to use as strategy" 

## Agent

The agent cointained in file agent.py is a working client that implements the best sequence of rules that we have found till now.

To start the agent:

```bash
python3 agent.py <IP> <port> <PlayerName>
```

Commands for agent:

- ready: set the status to ready

After it's ready the agent.py will start to run automatically, playing every time a legal move. It can plays several matches.

## Genetic

In the file genetic.py is implemented a very basic genetic algorithm. The values of the different genetic parameters were been chosen based on the
suggestions in the paper.

## Simulation

In the file simulation.py is present the function SimulateGames that is used by the genetic algorithm, in order to evaluate the sequence of rules.
Basically the simulation is just creating an instance of the class Game, and is simulating nGames, where every player is playing with the same list of
rules. When a rule is not appliable, the agent will choose the next one available. If no rule is applied, the agent will play the first card available.
After the execution of nGames, this function is returning the average score.
