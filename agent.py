from config import WIDTH, HEIGHT, AGENT_START_HUNGER, FOOD_EAT_GAIN


class Agent:
    def __init__(self, x, y, brain=None, is_player=False, player_id=None):
        self.x = x
        self.y = y

        self.brain = brain
        self.is_player = is_player
        self.player_id = player_id

        self.hunger = AGENT_START_HUNGER
        self.alive = True
        self.repro_cooldown = 0

        # Inventario base
        self.inventory = {
            "food": 0,
            "wood": 0,
            "stone": 0,
            "sword": 0,
        }

        # Goal system (per player AI)
        self.goals_queue = []
        self.current_goal = None
        self.current_plan = []

    def update(self, world):
        # movimento (se brain presente)
        dx, dy = 0, 0
        if self.brain is not None:
            dx, dy = self.brain.decide(self, world)

        self.x = max(0, min(WIDTH - 1, self.x + dx))
        self.y = max(0, min(HEIGHT - 1, self.y + dy))

        # fame
        self.hunger -= 1
        if self.hunger <= 0:
            self.alive = False

        if self.repro_cooldown > 0:
            self.repro_cooldown -= 1

    def eat(self):
        self.hunger += FOOD_EAT_GAIN