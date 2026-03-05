import random

from config import WIDTH, HEIGHT, NUM_AGENTS, NUM_FOOD
from agent import Agent
from brain import FoodBrain

# opzionali: se non ci sono in config, usiamo default safe
try:
    from config import NUM_WOOD
except Exception:
    NUM_WOOD = 30

try:
    from config import NUM_STONE
except Exception:
    NUM_STONE = 25

try:
    from config import MAX_FOOD
except Exception:
    MAX_FOOD = 150

try:
    from config import MAX_WOOD
except Exception:
    MAX_WOOD = 120

try:
    from config import MAX_STONE
except Exception:
    MAX_STONE = 90

try:
    from config import FOOD_RESPAWN_PER_TICK
except Exception:
    FOOD_RESPAWN_PER_TICK = 2

try:
    from config import WOOD_RESPAWN_PER_TICK
except Exception:
    WOOD_RESPAWN_PER_TICK = 1

try:
    from config import STONE_RESPAWN_PER_TICK
except Exception:
    STONE_RESPAWN_PER_TICK = 1

# opzionale: LLM thinker
try:
    from llm_brain import should_think, think
    HAS_LLM = True
except Exception:
    HAS_LLM = False


class World:
    def __init__(self):
        self.tick = 0

        # base map: "G/F/M/W"
        self.tiles = self._generate_tiles()

        # overlay compatibile col server: dict[(x,y)] = "R"|"H"|"K"...
        # per ora vuoto, ma evita crash su /state
        self.overlay = {}

        self.food = set()
        self.wood = set()
        self.stone = set()

        self.agents = []

        self._spawn_resources_initial()
        self._spawn_agents_initial()

    # ---------- MAP ----------
    def _generate_tiles(self):
        tiles = []
        for _y in range(HEIGHT):
            row = []
            for _x in range(WIDTH):
                r = random.random()
                if r < 0.10:
                    row.append("W")  # water
                elif r < 0.30:
                    row.append("F")  # forest
                elif r < 0.45:
                    row.append("M")  # mountain
                else:
                    row.append("G")  # grass
            tiles.append(row)
        return tiles

    def in_bounds(self, x, y):
        return 0 <= x < WIDTH and 0 <= y < HEIGHT

    def is_walkable(self, x, y):
        if not self.in_bounds(x, y):
            return False

        # overlay sempre walkable (semplificazione)
        if (x, y) in self.overlay:
            return True

        # water bloccata
        return self.tiles[y][x] != "W"

    def _random_walkable_cell(self):
        while True:
            x = random.randint(0, WIDTH - 1)
            y = random.randint(0, HEIGHT - 1)
            if self.is_walkable(x, y):
                return x, y

    # ---------- RESOURCES ----------
    def _spawn_resources_initial(self):
        # food su grass
        self._spawn_on_tile(self.food, NUM_FOOD, allowed={"G"})
        # wood su forest
        self._spawn_on_tile(self.wood, NUM_WOOD, allowed={"F"})
        # stone su mountain
        self._spawn_on_tile(self.stone, NUM_STONE, allowed={"M"})

    def _spawn_on_tile(self, s: set, count: int, allowed: set):
        tries = 0
        while len(s) < count and tries < 20000:
            tries += 1
            x = random.randint(0, WIDTH - 1)
            y = random.randint(0, HEIGHT - 1)

            # evita overlay
            if (x, y) in self.overlay:
                continue

            if self.tiles[y][x] in allowed:
                s.add((x, y))

    def _respawn(self, s: set, max_count: int, per_tick: int, allowed: set):
        if len(s) >= max_count:
            return

        for _ in range(per_tick):
            if len(s) >= max_count:
                break

            tries = 0
            while tries < 5000:
                tries += 1
                x = random.randint(0, WIDTH - 1)
                y = random.randint(0, HEIGHT - 1)

                if (x, y) in self.overlay:
                    continue

                if self.tiles[y][x] in allowed:
                    s.add((x, y))
                    break

    # ---------- AGENTS ----------
    def _spawn_agents_initial(self):
        brain = FoodBrain()
        for _ in range(NUM_AGENTS):
            x, y = self._random_walkable_cell()
            self.agents.append(Agent(x, y, brain=brain))

    # ---------- LOOP ----------
    def update(self):
        self.tick += 1

        # respawn risorse
        self._respawn(self.food, MAX_FOOD, FOOD_RESPAWN_PER_TICK, allowed={"G"})
        self._respawn(self.wood, MAX_WOOD, WOOD_RESPAWN_PER_TICK, allowed={"F"})
        self._respawn(self.stone, MAX_STONE, STONE_RESPAWN_PER_TICK, allowed={"M"})

        alive = []

        for agent in self.agents:
            if not agent.alive:
                continue

            # LLM pensa ogni tanto SOLO per player (se llm_brain presente)
            if HAS_LLM and agent.is_player and should_think(agent):
                print("LLM thinking for player:", agent.player_id)
                think(agent, self)

            agent.update(self)

            pos = (agent.x, agent.y)

            if pos in self.food:
                agent.inventory["food"] += 1
                agent.eat()
                self.food.remove(pos)

            if pos in self.wood:
                agent.inventory["wood"] += 1
                self.wood.remove(pos)

            if pos in self.stone:
                agent.inventory["stone"] += 1
                self.stone.remove(pos)

            alive.append(agent)

        self.agents = alive

    # ---------- DEBUG ----------
    def generate_grid(self):
        grid = [["." for _ in range(WIDTH)] for _ in range(HEIGHT)]

        for y in range(HEIGHT):
            for x in range(WIDTH):
                grid[y][x] = self.tiles[y][x]

        for (x, y), t in self.overlay.items():
            grid[y][x] = t

        for x, y in self.food:
            if (x, y) not in self.overlay:
                grid[y][x] = "f"
        for x, y in self.wood:
            if (x, y) not in self.overlay:
                grid[y][x] = "w"
        for x, y in self.stone:
            if (x, y) not in self.overlay:
                grid[y][x] = "s"

        for a in self.agents:
            grid[a.y][a.x] = "P" if a.is_player else "A"

        return grid