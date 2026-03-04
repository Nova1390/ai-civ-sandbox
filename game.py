import random
import time
import os

WIDTH = 20
HEIGHT = 20
NUM_AGENTS = 10
NUM_FOOD = 30

class Agent:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hunger = 20

    def move(self):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        self.x = max(0, min(WIDTH - 1, self.x + dx))
        self.y = max(0, min(HEIGHT - 1, self.y + dy))
        self.hunger -= 1

    def eat(self):
        self.hunger += 10

def clear():
    os.system('clear')

agents = [Agent(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)) for _ in range(NUM_AGENTS)]
food = {(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)) for _ in range(NUM_FOOD)}

while True:
    clear()
    grid = [["." for _ in range(WIDTH)] for _ in range(HEIGHT)]

    for fx, fy in food:
        grid[fy][fx] = "F"

    alive_agents = []
    for agent in agents:
        agent.move()

        if (agent.x, agent.y) in food:
            agent.eat()
            food.remove((agent.x, agent.y))

        if agent.hunger > 0:
            alive_agents.append(agent)
            grid[agent.y][agent.x] = "A"

    agents = alive_agents

    for row in grid:
        print(" ".join(row))

    print(f"\nAgenti vivi: {len(agents)}")

    if len(agents) == 0:
        print("Tutti morti 💀")
        break

    time.sleep(0.5)
