import random
from config import AGENT_START_HUNGER, FOOD_EAT_GAIN


class Agent:

    def __init__(
        self,
        x,
        y,
        brain=None,
        is_player=False,
        player_id=None,
        traits=None,
        personality=None,
        role="npc",
    ):

        self.x = x
        self.y = y

        self.brain = brain
        self.is_player = is_player
        self.player_id = player_id
        self.role = role

        self.hunger = AGENT_START_HUNGER
        self.alive = True
        self.repro_cooldown = 0

        self.inventory = {
            "food": 0,
            "wood": 0,
            "stone": 0,
            "sword": 0,
        }

        # traits
        if traits is None:
            traits = {
                "strength": random.randint(1, 10),
                "agility": random.randint(1, 10),
                "intelligence": random.randint(1, 10),
            }

        self.traits = traits

        # personality
        if personality is None:
            personality = {
                "aggressiveness": random.random(),
                "curiosity": random.random(),
                "discipline": random.random(),
                "greed": random.random(),
            }

        self.personality = personality

        # memory
        self.memory = {
            "food": [],
            "wood": [],
            "stone": []
        }

        # goals
        self.goals_queue = []
        self.current_goal = None
        self.current_plan = []

        # anti stuck
        self.last_move = (0, 0)
        self.last_pos = (x, y)
        self.stuck_ticks = 0
        self.escape_steps = 0

        # LLM thinking timer
        self.last_think = 0

    def update(self, world):

        if self.role == "merchant":
            return

        if not self.alive:
            return

        dx = 0
        dy = 0

        if self.brain:
            dx, dy = self.brain.decide(self, world)

        nx = self.x + dx
        ny = self.y + dy

        if world.is_walkable(nx, ny):
            self.x = nx
            self.y = ny

        # metabolismo
        self.hunger -= 1

        # auto eat
        if self.hunger < 15 and self.inventory["food"] > 0:
            self.inventory["food"] -= 1
            self.eat()

        if self.hunger <= 0:
            self.alive = False

        if self.repro_cooldown > 0:
            self.repro_cooldown -= 1

    def eat(self):
        self.hunger += FOOD_EAT_GAIN