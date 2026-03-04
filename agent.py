import random
from config import WIDTH, HEIGHT

class Agent:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hunger = 20
        self.alive = True

    def move(self):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])

        self.x = max(0, min(WIDTH - 1, self.x + dx))
        self.y = max(0, min(HEIGHT - 1, self.y + dy))

        self.hunger -= 1
        if self.hunger <= 0:
            self.alive = False

    def eat(self):
        self.hunger += 10
