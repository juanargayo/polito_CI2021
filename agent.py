#from grpc import server
import numpy as np

from subprocess import Popen, PIPE, STDOUT
import threading
import time
import signal
import os

from agent2 import simulateGames
from agent3 import simulateGames2

# GAME SECTION

# Evaluation

statuses = ["server", "client", "ready", "game"]


# --##--##--##-- NOTES ##--##--##--##--##-##--##--

# For Mirror-play -> each agent plays with copies of himself for n games, where for each game,
# they play the 4 game sizes. Thus, the fitness is the average of 4n games

# after running the algorithm for 500 generations we took the agents corresponding to the 10 best performing
# chromosomes and ran a second round of simulations.


# --##--##--##--##--##--##--##--##--##--##--##--


# GENETIC SECTION

CHROMOSOME_SIZE = 22  # Number of rules
POPULATION_SIZE = 10
OFFSPRING_SIZE = 5 #int(np.round(CHROMOSOME_SIZE * 1.5))
MUTATION_RATE = 0.1
CROSSOVER_RATE = 0.9
TOURNAMENT_SIZE = 5
ELITE_SIZE = int(np.round(POPULATION_SIZE * 0.1))
NUM_GENERATIONS = 50
GAMES_PER_GEN = 1
STEADY_STATE = 1000


def evaluate_solution(solution: np.array) -> float:
    # simulate for this solution (this rule order) 20 mirror-games => return avg_score
    numPlayers = [p for p in range(2, 6)]
    score = 0
    start_time = time.time()
    for npl in numPlayers:
        score += simulateGames2(npl, GAMES_PER_GEN, solution)
        #print(f"Evaluated in {time.time()-start_time}s")
    avgScore = score/len(numPlayers)
    #print(f"Eval: {avgScore}")
    return avgScore


# MUTATIONS

def parent_selection(population):
    tournament = population[np.random.randint(0,
                                              len(population),
                                              size=(TOURNAMENT_SIZE, ))]
    fitness = np.array([evaluate_solution(p) for p in tournament])
    return np.copy(tournament[np.argmax(fitness)])


def tweak(solution: np.array, *, pm: float = 1 / CHROMOSOME_SIZE) -> np.array:
    new_solution = solution.copy()
    p = None
    while p is None or p < pm:
        i1 = np.random.randint(0, CHROMOSOME_SIZE)
        i2 = np.random.randint(0, CHROMOSOME_SIZE)
        temp = new_solution[i1]
        new_solution[i1] = new_solution[i2]
        new_solution[i2] = temp
        p = np.random.random()
    return new_solution


def inversion(solution: np.array, *, pm: float = 1 / CHROMOSOME_SIZE) -> np.array:
    new_solution = solution.copy()
    p = np.random.random()
    if p < pm:
        i1 = np.random.randint(0, CHROMOSOME_SIZE)
        i2 = np.random.randint(0, CHROMOSOME_SIZE)
        if i1 > i2:
            i2, i1 = i1, i2
        to_invert = solution[i1:i2 + 1]
        if len(to_invert) > 0:
            if i1 == 0:
                new_solution[i2::-1] = to_invert
            else:
                new_solution[i2:i1 - 1:-1] = to_invert
    return new_solution


def insert(solution: np.array, *, pm: float = 1 / CHROMOSOME_SIZE) -> np.array:
    new_solution = solution.copy()
    p = np.random.random()
    if p < pm:
        i1 = np.random.randint(0, CHROMOSOME_SIZE)
        i2 = np.random.randint(0, CHROMOSOME_SIZE)
        if i1 > i2:
            i2, i1 = i1, i2
        to_move = solution[i1 + 1:i2]
        if len(to_move) > 0:
            new_solution[i1 + 1] = solution[i2]
            new_solution[i1 + 2:i2 + 1] = to_move
    return new_solution


def ordxover(p1, p2):
    i1, i2 = int(np.random.random() * len(p1)), int(np.random.random() *
                                                    len(p2))
    start, end = min(i1, i2), max(i1, i2)
    off_p1 = np.array(p1[start:end + 1])
    off_p2 = np.array([item for item in p2 if item not in off_p1])
    off = np.concatenate((off_p1, off_p2))
    return off


def main():
    # EVOLUTION
    start = time.time()
    population = np.tile(np.array(range(CHROMOSOME_SIZE)),
                         (POPULATION_SIZE, 1))
    generations = 1

    #population[0] = [7, 8, 9, 10, 11, 12, 1, 20]
    for i in range(POPULATION_SIZE):
        np.random.shuffle(population[i])

    solution_costs = [evaluate_solution(population[i])
                      for i in range(POPULATION_SIZE)]
    global_best_solution = population[np.argmax(solution_costs)]
    global_best_fitness = solution_costs[np.argmax(solution_costs)]
    print("BEST SOLUTION",global_best_solution)
    print("BEST SCORE", global_best_fitness)

    history = [(0, global_best_fitness)]
    steady_state = 0
    step = 0

    while steady_state < STEADY_STATE:
        print(f"generation n.{generations}")
        step += 1
        steady_state += 1
        generations += 1
        offspring = list()
        for o in range(OFFSPRING_SIZE // 2):
            p1, p2 = parent_selection(population), parent_selection(population)
            offspring.append(inversion(p1))
            offspring.append(tweak(p2))
            if steady_state > int(0.6 * STEADY_STATE) and np.random.random() < 0.3:
                offspring.append(tweak(ordxover(p1, p2)))
            if steady_state > int(0.6 * STEADY_STATE) and np.random.random() < 0.5:
                offspring.append(insert(p1))
        # while len(offspring) < OFFSPRING_SIZE:
        #     p1 = parent_selection(population)
        #     offspring.append(tweak(p1))

        offspring = np.array(offspring)
        fitness = [evaluate_solution(o) for o in offspring]
        best_solution = offspring[np.argmax(fitness)]
        best_fitness = evaluate_solution(best_solution)
        
        if best_fitness > global_best_fitness:
            global_best_solution = best_solution
            global_best_fitness = best_fitness
            print("BEST SOLUTION",global_best_solution)
            print("BEST SCORE", global_best_fitness)
            history.append((step, global_best_fitness))
            steady_state = 0
            

        fitness_pop = [evaluate_solution(p) for p in population]
        elite = np.copy(population[np.argsort(fitness_pop)][:ELITE_SIZE])
        best_offspring = np.copy(offspring[np.argsort(fitness)][:POPULATION_SIZE -
                                                                ELITE_SIZE])
        population = np.concatenate((elite, best_offspring))
        

    # plot(history)
    print(global_best_solution)


if __name__ == "__main__":
    main()
