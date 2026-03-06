from __future__ import annotations

import random
from typing import Dict, List, Optional, Set, Tuple

from config import (
    WIDTH,
    HEIGHT,
    NUM_AGENTS,
    NUM_FOOD,
    NUM_WOOD,
    NUM_STONE,
    FOOD_RESPAWN_PER_TICK,
    WOOD_RESPAWN_PER_TICK,
    STONE_RESPAWN_PER_TICK,
    MAX_FOOD,
    MAX_WOOD,
    MAX_STONE,
    FOOD_EAT_GAIN,
    MAX_AGENTS,
)

from agent import Agent
from brain import FoodBrain
import systems.building_system as building_system
import systems.village_system as village_system
import systems.farming_system as farming_system
import systems.road_system as road_system

Coord = Tuple[int, int]

MAX_STRUCTURES = 60
MAX_HOUSES_PER_VILLAGE = 8
MAX_NEW_VILLAGE_SEEDS = 2
MIN_HOUSES_FOR_VILLAGE = 3
MIN_HOUSES_FOR_LEADER = 3


class World:
    def __init__(self):
        self.width = int(WIDTH)
        self.height = int(HEIGHT)

        self.tick = 0
        self.llm_interactions = 0

        self.tiles: List[List[str]] = self._generate_tiles()

        self.food: Set[Coord] = set()
        self.wood: Set[Coord] = set()
        self.stone: Set[Coord] = set()

        self.farms: Set[Coord] = set()
        self.farm_plots: Dict[Coord, Dict] = {}

        self.structures: Set[Coord] = set()
        self.storage_buildings: Set[Coord] = set()
        self.roads: Set[Coord] = set()
        self.road_usage: Dict[Coord, int] = {}

        self.villages: List[Dict] = []
        self.agents: List[Agent] = []

        self.MAX_STRUCTURES = MAX_STRUCTURES
        self.MAX_HOUSES_PER_VILLAGE = MAX_HOUSES_PER_VILLAGE
        self.MAX_NEW_VILLAGE_SEEDS = MAX_NEW_VILLAGE_SEEDS
        self.MIN_HOUSES_FOR_VILLAGE = MIN_HOUSES_FOR_VILLAGE
        self.MIN_HOUSES_FOR_LEADER = MIN_HOUSES_FOR_LEADER

        self.MAX_FOOD = MAX_FOOD
        self.MAX_WOOD = MAX_WOOD
        self.MAX_STONE = MAX_STONE

        self._spawn_initial_food(NUM_FOOD)
        self._spawn_initial_wood(NUM_WOOD)
        self._spawn_initial_stone(NUM_STONE)

        if NUM_AGENTS > 0:
            brain = FoodBrain()
            for _ in range(NUM_AGENTS):
                pos = self.find_random_free()
                if pos:
                    x, y = pos
                    self.add_agent(Agent(x, y, brain, False, None))

        self.detect_villages()

    def record_llm_interaction(self) -> None:
        self.llm_interactions += 1

    def get_village_by_id(self, village_id: Optional[int]) -> Optional[Dict]:
        return village_system.get_village_by_id(self, village_id)

    def count_leaders(self) -> int:
        return village_system.count_leaders(self)

    def get_civilization_stats(self) -> Dict:
        return village_system.get_civilization_stats(self)

    def record_road_step(self, x: int, y: int) -> None:
        road_system.record_agent_step(self, x, y)

    def _generate_tiles(self) -> List[List[str]]:
        tiles: List[List[str]] = []

        for _y in range(self.height):
            row: List[str] = []

            for _x in range(self.width):
                r = random.random()

                if r < 0.08:
                    row.append("W")
                elif r < 0.18:
                    row.append("M")
                elif r < 0.40:
                    row.append("F")
                else:
                    row.append("G")

            tiles.append(row)

        return tiles

    def is_walkable(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return False
        return self.tiles[y][x] != "W"

    def is_occupied(self, x: int, y: int) -> bool:
        for a in self.agents:
            if a.alive and a.x == x and a.y == y:
                return True
        return False

    def add_agent(self, agent: Agent):
        self.agents.append(agent)

    def find_random_free(self) -> Optional[Coord]:
        for _ in range(2000):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)

            if self.is_walkable(x, y) and not self.is_occupied(x, y):
                return (x, y)

        return None

    def find_free_adjacent(self, x: int, y: int) -> Optional[Coord]:
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(dirs)

        for dx, dy in dirs:
            nx = x + dx
            ny = y + dy

            if self.is_walkable(nx, ny) and not self.is_occupied(nx, ny):
                return (nx, ny)

        return None

    def _spawn_initial_food(self, n: int):
        for _ in range(n):
            pos = self.find_random_free()
            if pos:
                self.food.add(pos)

    def _spawn_initial_wood(self, n: int):
        for _ in range(n):
            for _ in range(50):
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                if self.tiles[y][x] == "F" and (x, y) not in self.wood:
                    self.wood.add((x, y))
                    break

    def _spawn_initial_stone(self, n: int):
        for _ in range(n):
            for _ in range(50):
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                if self.tiles[y][x] == "M" and (x, y) not in self.stone:
                    self.stone.add((x, y))
                    break

    def respawn_resources(self):
        if len(self.food) < MAX_FOOD:
            for _ in range(FOOD_RESPAWN_PER_TICK):
                pos = self.find_random_free()
                if pos:
                    self.food.add(pos)

        if len(self.wood) < MAX_WOOD:
            for _ in range(WOOD_RESPAWN_PER_TICK):
                for _ in range(50):
                    x = random.randint(0, self.width - 1)
                    y = random.randint(0, self.height - 1)
                    if self.tiles[y][x] == "F":
                        self.wood.add((x, y))
                        break

        if len(self.stone) < MAX_STONE:
            for _ in range(STONE_RESPAWN_PER_TICK):
                for _ in range(50):
                    x = random.randint(0, self.width - 1)
                    y = random.randint(0, self.height - 1)
                    if self.tiles[y][x] == "M":
                        self.stone.add((x, y))
                        break

    def autopickup(self, agent: Agent):
        pos = (agent.x, agent.y)

        if pos in self.food:
            self.food.remove(pos)
            agent.inventory["food"] = agent.inventory.get("food", 0) + 1
            agent.hunger += FOOD_EAT_GAIN
            if agent.hunger > 100:
                agent.hunger = 100

    def gather_resource(self, agent: Agent):
        pos = (agent.x, agent.y)
        village = self.get_village_by_id(getattr(agent, "village_id", None))

        if pos in self.wood:
            self.wood.remove(pos)
            if village is not None:
                village["storage"]["wood"] = village["storage"].get("wood", 0) + 1
            else:
                agent.inventory["wood"] = agent.inventory.get("wood", 0) + 1
            return True

        if pos in self.stone:
            self.stone.remove(pos)
            if village is not None:
                village["storage"]["stone"] = village["storage"].get("stone", 0) + 1
            else:
                agent.inventory["stone"] = agent.inventory.get("stone", 0) + 1
            return True

        return False

    def building_score(self, x: int, y: int) -> int:
        return building_system.building_score(self, x, y)

    def count_nearby_houses(self, x: int, y: int, radius: int = 5) -> int:
        return building_system.count_nearby_houses(self, x, y, radius)

    def count_nearby_population(self, x: int, y: int, radius: int = 6) -> int:
        return building_system.count_nearby_population(self, x, y, radius)

    def can_build_at(self, x: int, y: int) -> bool:
        return building_system.can_build_at(self, x, y)

    def try_build_house(self, agent: Agent):
        return building_system.try_build_house(self, agent)

    def try_build_storage(self, agent: Agent):
        return building_system.try_build_storage(self, agent)

    def try_build_farm(self, agent: Agent):
        return farming_system.try_build_farm(self, agent)

    def work_farm(self, agent: Agent):
        return farming_system.work_farm(self, agent)

    def detect_villages(self):
        village_system.detect_villages(self)

    def assign_village_leaders(self):
        village_system.assign_village_leaders(self)

    def update_village_politics(self):
        village_system.update_village_politics(self)

    def update(self):
        self.tick += 1

        self.respawn_resources()
        farming_system.update_farms(self)

        for agent in list(self.agents):
            if not agent.alive:
                continue
            agent.update(self)

        self.agents = [a for a in self.agents if a.alive]

        if len(self.agents) > MAX_AGENTS:
            extra = len(self.agents) - MAX_AGENTS

            for a in self.agents:
                if extra <= 0:
                    break
                if not a.is_player:
                    a.alive = False
                    extra -= 1

            self.agents = [a for a in self.agents if a.alive]

        self.detect_villages()