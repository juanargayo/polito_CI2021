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


def evaluate_solution(solution: np.array) -> float:
    # simulate for this solution (this rule order) 20 mirror-games => return avg_score
    pass


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
                        )
    status = "server"
    ready = 0
    while True:
        time.sleep(0.1)
        line = server_proc.stdout.readline()
        if not line:
            break
        print("![server]", line.strip().decode())

        if(status == statuses[0] and line.strip().decode().split()[0] == "Hanabi"):
            status = statuses[1]
            # Creating n_players sub_process
            for turn in range(players):
                client_cmd = clients_cmd + f" player{turn}"
                client_procs.append(Popen(client_cmd.split(),
                                          stdin=PIPE,
                                          stdout=PIPE,
                                          ))
                # I read a line from every client
                if status == statuses[1]:
                    time.sleep(0.1)
                    client_line = client_procs[turn].stdout.readline()

                    if not client_line:
                        break
                    print(f"![client{turn}] {client_line}")
                    client_procs[turn].stdout.flush()
                    ready += 1
                    if ready == players:
                        status = "ready"

        if status == "ready":
            ready = 0
            for turn in range(players):
                time.sleep(0.1)
                client_procs[turn].stdin.write(b"ready")
                ready += 1
                if ready == players:
                    status = "game"
        if status == "game":
            print("[MASTER]Let's play")
            break
            #print("![client]", client_line2.strip().decode())

    server_proc.wait()
    print("![test] server killed ")


def main():
    simulation()


if __name__ == "__main__":
    main()


# GENETIC SECTION


NUM_RULES = 35
POPULATION_SIZE = 200
OFFSPRING_SIZE = int(np.round(NUM_RULES * 1.5))
TOURNAMENT_SIZE = 5
ELITE_SIZE = int(np.round(POPULATION_SIZE * 0.1))
STEADY_STATE = 5_000
GENERATION_SIZE = 500
GAME_SIZE = 20

# MUTATIONS


def parent_selection(population):
    tournament = population[np.random.randint(0,
                                              len(population),
                                              size=(TOURNAMENT_SIZE, ))]
    fitness = np.array([evaluate_solution(p) for p in tournament])
    return np.copy(tournament[fitness.argmax])


def tweak(solution: np.array, *, pm: float = 1 / NUM_RULES) -> np.array:
    new_solution = solution.copy()
    p = None
    while p is None or p < pm:
        i1 = np.random.randint(0, NUM_RULES)
        i2 = np.random.randint(0, NUM_RULES)
        temp = new_solution[i1]
        new_solution[i1] = new_solution[i2]
        new_solution[i2] = temp
        p = np.random.random()
    return new_solution


def inversion(solution: np.array, *, pm: float = 1 / NUM_RULES) -> np.array:
    new_solution = solution.copy()
    p = np.random.random()
    if p < pm:
        i1 = np.random.randint(0, NUM_RULES)
        i2 = np.random.randint(0, NUM_RULES)
        if i1 > i2:
            i2, i1 = i1, i2
        to_invert = solution[i1:i2 + 1]
        if len(to_invert) > 0:
            if i1 == 0:
                new_solution[i2::-1] = to_invert
            else:
                new_solution[i2:i1 - 1:-1] = to_invert
    return new_solution


def insert(solution: np.array, *, pm: float = 1 / NUM_RULES) -> np.array:
    new_solution = solution.copy()
    p = np.random.random()
    if p < pm:
        i1 = np.random.randint(0, NUM_RULES)
        i2 = np.random.randint(0, NUM_RULES)
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


# #EVOLUTION
# population = np.tile(np.array(range(NUM_RULES)), (POPULATION_SIZE, 1))
# generations = 1

# for i in range(POPULATION_SIZE):
#     np.random.shuffle(population[i])
# solution_costs = [
#     evaluate_solution(population[i]) for i in range(POPULATION_SIZE)
# ]
# global_best_solution = population[np.argmax(solution_costs)]
# global_best_fitness = evaluate_solution(global_best_solution)

# history = [(0, global_best_fitness)]
# steady_state = 0
# step = 0

# while steady_state < STEADY_STATE:
#     step += 1
#     steady_state += 1
#     generations += 1
#     offspring = list()
#     for o in range(OFFSPRING_SIZE // 2):
#         p1, p2 = parent_selection(population), parent_selection(population)
#         offspring.append(inversion(p1))
#         offspring.append(tweak(p2))
#         if steady_state > int(0.6 * STEADY_STATE) and np.random.random() < 0.3:
#             offspring.append(tweak(ordxover(p1, p2)))
#         if steady_state > int(0.6 * STEADY_STATE) and np.random.random() < 0.5:
#             offspring.append(insert(p1))
#     # while len(offspring) < OFFSPRING_SIZE:
#     #     p1 = parent_selection(population)
#     #     offspring.append(tweak(p1))

#     offspring = np.array(offspring)
#     fitness = [evaluate_solution(o) for o in offspring]
#     best_solution = offspring[np.argmax(fitness)]
#     best_fitness = evaluate_solution(best_solution)

#     if best_fitness > global_best_fitness:
#         global_best_solution = best_solution
#         global_best_fitness = best_fitness
#         history.append((step, global_best_fitness))
#         steady_state = 0

#     fitness_pop = [evaluate_solution(p) for p in population]
#     elite = np.copy(population[np.argsort(fitness_pop)][:ELITE_SIZE])
#     best_offspring = np.copy(offspring[np.argsort(fitness)][:POPULATION_SIZE -
#                                                             ELITE_SIZE])
#     population = np.concatenate((elite, best_offspring))

# #plot(history)
# print(global_best_solution)
