from grpc import server
import numpy as np

from subprocess import Popen, PIPE, STDOUT
import threading
import time
import signal
import os

# GAME SECTION

# Evaluation

statuses = ["server", "client", "ready", "game"]





# Simulation
def simulation():
    print("Starting...")
    players = 5  # random

    server_cmd = f"python3 server.py {players}"
    clients_cmd = "python3 client.py 127.0.0.1 1024"
    client_procs = []
    server_proc = Popen(server_cmd.split(),
                        stdin=PIPE,
                        stdout=PIPE,
                        universal_newlines=True
                        )
    status = "server"
    ready = 0
    end = False
    while not end:
        # time.sleep(0.1)
        line = server_proc.stdout.readline()
        if not line:
            break
        print("![server]", line.strip())

        if(status == statuses[0] and line.strip().split()[0] == "Hanabi"):
            status = statuses[1]
            # Creating n_players sub_process
            for turn in range(players):
                client_cmd = clients_cmd + f" player{turn}"
                client_procs.append(Popen(client_cmd.split(),
                                          stdin=PIPE,
                                          stdout=PIPE,
                                          universal_newlines=True
                                          ))
                # I read a line from every client
                if status == statuses[1]:
                    # time.sleep(0.1)
                    client_line = client_procs[turn].stdout.readline()
                    if not client_line:
                        continue
                    print(f"![client{turn}] {client_line}")
                    client_procs[turn].stdout.flush()

                    ready += 1
                    if ready == players:
                        status = "ready"

        if status == "ready":
            ready = 0
            cmd_bytes = b'ready'
            for turn in range(players):
                # time.sleep(0.1)
                client_procs[turn].stdin.write("ready\n")
                client_procs[turn].stdin.flush()  # not necessary in this case
                ready += 1
                if ready == players:
                    status = "game_start"
        if status == "game_start":
            print("[MASTER]Let's play")

            for turn in range(2*players):
                # time.sleep(0.1)
                line = client_procs[turn % players].stdout.readline()
                client_procs[turn % players].stdout.flush()

                if not line:
                    continue
                print(f"[!client{turn%players}] {line}")

                # client_procs[turn].stdin.write(play_cmd)
                # client_procs[turn].stdin.flush()  # not necessary in this case

                # print(stdout)
            status = "play"
        if status == "play":
            print("PLAY")
            play_cmd = "play 0\n"
            for turn in range(players):
                # time.sleep(0.1)

                client_procs[turn].stdin.write("show")
                client_procs[turn].stdin.flush()  # not necessary in this case
                time.sleep(1)

                print(turn, client_procs[turn].stdout.readline())

                client_procs[turn].stdin.write(play_cmd)
                client_procs[turn].stdin.flush()  # not necessary in this case

                move_response = client_procs[turn].stdout.readline()
                if move_response.split()[3] == "OH":
                    print("It was bad move")
                else:
                    print("It was a good move")

                if turn == players-1:
                    end = True
            #print("![client]", client_line2.strip().decode())

    time.sleep(3)
    server_proc.stdin.close()
    server_proc.terminate()
    server_proc.wait(0.2)

    for i in range(players):
        client_procs[i].stdin.close()
        client_procs[i].terminate()
        client_procs[i].wait(0.2)
    print("![test] server killed ")


def main():
    simulation()

##--##--##--##-- NOTES ##--##--##--##--##-##--##--

#For Mirror-play -> each agent plays with copies of himself for n games, where for each game,
#they play the 4 game sizes. Thus, the fitness is the average of 4n games

#after running the algorithm for 500 generations we took the agents corresponding to the 10 best performing
#chromosomes and ran a second round of simulations.


##--##--##--##--##--##--##--##--##--##--##--##--

if __name__ == "__main__":
    main()


# GENETIC SECTION


CHROMOSOME_SIZE = 22    #Number of rules
POPULATION_SIZE = 200
OFFSPRING_SIZE = int(np.round(CHROMOSOME_SIZE * 1.5))
MUTATION_RATE = 0.1
CROSSOVER_RATE = 0.9
TOURNAMENT_SIZE = 5
ELITE_SIZE = int(np.round(POPULATION_SIZE * 0.1))
NUM_GENERATIONS = 500
GAMES_PER_GEN = 20
STEADY_STATE = 1000

def evaluate_solution(solution: np.array) -> float:
    # simulate for this solution (this rule order) 20 mirror-games => return avg_score
    numPlayers = [p for p in range(1, 4)]
    score = 0

    for npl in numPlayers:
        score += simulateGame(solution, GAMES_PER_GEN, npl)

    avgScore = score/len(numPlayers)
    
    return avgScore



# MUTATIONS


def parent_selection(population):
    tournament = population[np.random.randint(0,
                                              len(population),
                                              size=(TOURNAMENT_SIZE, ))]
    fitness = np.array([evaluate_solution(p) for p in tournament])
    return np.copy(tournament[fitness.argmax])


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


#EVOLUTION
population = np.tile(np.array(range(CHROMOSOME_SIZE)), (POPULATION_SIZE, 1))
generations = 1

for i in range(POPULATION_SIZE):
    np.random.shuffle(population[i])

solution_costs = [evaluate_solution(population[i]) for i in range(POPULATION_SIZE)]
global_best_solution = population[np.argmax(solution_costs)]
global_best_fitness = evaluate_solution(global_best_solution)

history = [(0, global_best_fitness)]
steady_state = 0
step = 0

while steady_state < STEADY_STATE:
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
        history.append((step, global_best_fitness))
        steady_state = 0

    fitness_pop = [evaluate_solution(p) for p in population]
    elite = np.copy(population[np.argsort(fitness_pop)][:ELITE_SIZE])
    best_offspring = np.copy(offspring[np.argsort(fitness)][:POPULATION_SIZE -
                                                            ELITE_SIZE])
    population = np.concatenate((elite, best_offspring))

#plot(history)
print(global_best_solution)
