from __future__ import annotations

from typing import Optional, Tuple, Set
import random
import asyncio

from planner import Planner
from pathfinder import astar


Coord = Tuple[int, int]

VALID_GOALS = {
    "expand village",
    "gather food",
    "gather wood",
    "gather stone",
    "explore",
}


def normalize_goal(text: str) -> Optional[str]:
    t = (text or "").strip().lower()

    if not t:
        return None

    if "wood" in t or "legn" in t or "tree" in t:
        return "gather wood"

    if "stone" in t or "rock" in t or "pietr" in t:
        return "gather stone"

    if "food" in t or "hunt" in t or "eat" in t or "cibo" in t or "farm" in t:
        return "gather food"

    if "expand" in t or "build" in t or "house" in t or "village" in t:
        return "expand village"

    if "explore" in t or "esplora" in t:
        return "explore"

    if t in VALID_GOALS:
        return t

    return None


class FoodBrain:
    def __init__(self, vision_radius: int = 8):
        self.vision_radius = vision_radius

    def decide(self, agent, world) -> Tuple[str, ...]:
        village_strategy = self._get_village_strategy(agent, world)
        village = world.get_village_by_id(getattr(agent, "village_id", None))
        relation = (village.get("relation", "") if village else "").lower()

        # survival sempre prima
        if agent.hunger < 60 or agent.inventory.get("food", 0) == 0:
            farm_target = self.find_farm_target(agent, world, prefer_ripe=True)
            if farm_target is not None:
                return self.move_towards(agent, world, farm_target)

            target = self.find_nearest(agent, world.food, "food", self.vision_radius)
            if target is not None:
                return self.move_towards(agent, world, target)

        # migrazione
        if relation == "migrate" and village:
            migration_target_id = village.get("migration_target_id")
            migration_target = world.get_village_by_id(migration_target_id)
            if migration_target:
                center = migration_target.get("center")
                if center:
                    return self.move_towards(agent, world, (center["x"], center["y"]))

        # guerra
        if relation == "war" and village:
            target_village_id = village.get("target_village_id")
            enemy = world.get_village_by_id(target_village_id)
            if enemy:
                center = enemy.get("center")
                if center and random.random() < 0.45:
                    return self.move_towards(agent, world, (center["x"], center["y"]))

        # strategia del villaggio
        if village_strategy:
            action = self._decide_from_strategy(agent, world, village_strategy)
            if action is not None:
                return action

        # comportamento base
        if agent.inventory.get("wood", 0) < 5:
            target = self.find_nearest(agent, world.wood, "wood", self.vision_radius)
            if target is not None:
                return self.move_towards(agent, world, target)

        if agent.inventory.get("stone", 0) < 3:
            target = self.find_nearest(agent, world.stone, "stone", self.vision_radius)
            if target is not None:
                return self.move_towards(agent, world, target)

        village_home = self._get_known_village_center(agent, world)
        if village_home is not None and random.random() < 0.35:
            return self.move_towards(agent, world, village_home)

        return self.wander(agent, world)

    def _get_village_strategy(self, agent, world) -> str:
        village_id = getattr(agent, "village_id", None)
        if village_id is None:
            return ""

        village = world.get_village_by_id(village_id)
        if not village:
            return ""

        return str(village.get("strategy", "")).lower().strip()

    def _get_known_village_center(self, agent, world) -> Optional[Coord]:
        village_id = getattr(agent, "village_id", None)
        if village_id is not None:
            village = world.get_village_by_id(village_id)
            if village:
                c = village.get("center")
                if c:
                    return (c["x"], c["y"])

        mem = agent.memory.get("villages", set())
        if mem:
            ax, ay = agent.x, agent.y
            return min(mem, key=lambda p: abs(p[0] - ax) + abs(p[1] - ay))

        return None

    def _decide_from_strategy(self, agent, world, strategy: str) -> Optional[Tuple[str, ...]]:
        if "food" in strategy or "hunt" in strategy or "eat" in strategy or "farm" in strategy:
            farm_target = self.find_farm_target(agent, world, prefer_ripe=True)
            if farm_target is not None:
                return self.move_towards(agent, world, farm_target)

            target = self.find_nearest(agent, world.food, "food", self.vision_radius + 2)
            if target is not None:
                return self.move_towards(agent, world, target)

        if "wood" in strategy or "tree" in strategy or "legn" in strategy:
            target = self.find_nearest(agent, world.wood, "wood", self.vision_radius + 2)
            if target is not None:
                return self.move_towards(agent, world, target)

        if "stone" in strategy or "rock" in strategy or "pietr" in strategy:
            target = self.find_nearest(agent, world.stone, "stone", self.vision_radius + 2)
            if target is not None:
                return self.move_towards(agent, world, target)

        if "expand" in strategy or "build" in strategy or "village" in strategy or "house" in strategy:
            # se il villaggio ha pochi campi, prova a crearne/gestirne alcuni
            if len(getattr(world, "farm_plots", {})) < max(2, len(getattr(world, "villages", [])) * 2):
                farm_target = self.find_farm_target(agent, world, prefer_ripe=False)
                if farm_target is not None:
                    return self.move_towards(agent, world, farm_target)

            if agent.inventory.get("wood", 0) < 8:
                target = self.find_nearest(agent, world.wood, "wood", self.vision_radius + 2)
                if target is not None:
                    return self.move_towards(agent, world, target)

            if agent.inventory.get("stone", 0) < 5:
                target = self.find_nearest(agent, world.stone, "stone", self.vision_radius + 2)
                if target is not None:
                    return self.move_towards(agent, world, target)

            village_home = self._get_known_village_center(agent, world)
            if village_home is not None:
                return self.move_towards(agent, world, village_home)

        if "explore" in strategy or "esplora" in strategy:
            if random.random() < 0.75:
                return self.wander(agent, world)

        return None

    def find_nearest(
        self,
        agent,
        resource_set: Set[Coord],
        memory_key: str,
        radius: int,
    ) -> Optional[Coord]:
        ax = agent.x
        ay = agent.y

        best: Optional[Coord] = None
        best_d = 9999

        for (x, y) in resource_set:
            d = abs(x - ax) + abs(y - ay)
            if d <= radius and d < best_d:
                best_d = d
                best = (x, y)

        if best is not None:
            return best

        for (x, y) in agent.memory.get(memory_key, set()):
            d = abs(x - ax) + abs(y - ay)
            if d < best_d:
                best_d = d
                best = (x, y)

        return best

    def find_farm_target(self, agent, world, prefer_ripe: bool = True) -> Optional[Coord]:
        ax = agent.x
        ay = agent.y

        best: Optional[Coord] = None
        best_score = 999999

        known_farms = set(agent.memory.get("farms", set()))
        known_farms.update(getattr(world, "farms", set()))

        for pos in known_farms:
            plot = getattr(world, "farm_plots", {}).get(pos)
            if not plot:
                continue

            state = plot.get("state", "prepared")
            d = abs(pos[0] - ax) + abs(pos[1] - ay)

            if prefer_ripe:
                if state == "ripe":
                    score = d
                elif state == "prepared":
                    score = d + 4
                elif state == "planted":
                    score = d + 20
                elif state == "growing":
                    score = d + 12
                else:
                    score = d + 50
            else:
                if state == "prepared":
                    score = d
                elif state == "ripe":
                    score = d + 2
                elif state == "growing":
                    score = d + 10
                elif state == "planted":
                    score = d + 14
                else:
                    score = d + 50

            if score < best_score:
                best_score = score
                best = pos

        return best

    def move_towards(self, agent, world, target: Coord) -> Tuple[str, ...]:
        start = (agent.x, agent.y)

        if start == target:
            return ("wait",)

        path = astar(world, start, target)

        if path is not None and len(path) >= 2:
            next_x, next_y = path[1]
            dx = next_x - agent.x
            dy = next_y - agent.y

            if world.is_walkable(next_x, next_y) and not world.is_occupied(next_x, next_y):
                return ("move", dx, dy)

        return self.greedy_step(agent, world, target)

    def greedy_step(self, agent, world, target: Coord) -> Tuple[str, ...]:
        tx, ty = target
        options = []

        if tx > agent.x:
            options.append((1, 0))
        elif tx < agent.x:
            options.append((-1, 0))

        if ty > agent.y:
            options.append((0, 1))
        elif ty < agent.y:
            options.append((0, -1))

        random.shuffle(options)

        for dx, dy in options:
            nx, ny = agent.x + dx, agent.y + dy
            if world.is_walkable(nx, ny) and not world.is_occupied(nx, ny):
                return ("move", dx, dy)

        return self.wander(agent, world)

    def wander(self, agent, world) -> Tuple[str, ...]:
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]
        random.shuffle(dirs)

        for dx, dy in dirs:
            if dx == 0 and dy == 0:
                return ("wait",)

            nx, ny = agent.x + dx, agent.y + dy
            if world.is_walkable(nx, ny) and not world.is_occupied(nx, ny):
                return ("move", dx, dy)

        return ("wait",)


class LLMBrain:
    def __init__(self, planner: Planner, fallback: FoodBrain, think_every_ticks: int = 240):
        self.planner = planner
        self.fallback = fallback
        self.think_every_ticks = think_every_ticks

    def decide(self, agent, world) -> Tuple[str, ...]:
        if agent.hunger < 60 or agent.inventory.get("food", 0) == 0:
            return self.fallback.decide(agent, world)

        if self._should_think(agent, world):
            self._schedule_llm_request(agent, world)

        return self._act_from_goal(agent, world)

    def _should_think(self, agent, world) -> bool:
        if agent.llm_pending:
            return False

        if world.tick - agent.last_llm_tick < self.think_every_ticks:
            return False

        return True

    def _schedule_llm_request(self, agent, world) -> None:
        agent.llm_pending = True
        agent.last_llm_tick = world.tick

        prompt = self._make_prompt(agent, world)
        print(f"LLM thinking for {agent.role}: {agent.player_id or 'npc'}")

        if hasattr(world, "record_llm_interaction"):
            world.record_llm_interaction()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._request_goal(agent, world, prompt))
        except RuntimeError:
            agent.llm_pending = False
            print("LLM scheduling failed: no running event loop")

    async def _request_goal(self, agent, world, prompt: str) -> None:
        try:
            raw_goal = await self.planner.propose_goal_async(prompt)
            normalized = normalize_goal(raw_goal)

            if normalized is None:
                print(f"LLM invalid goal: {raw_goal}")
                return

            agent.goal = normalized
            print(f"LLM goal ({agent.role}): {agent.goal}")

            if getattr(agent, "role", "") == "leader" and getattr(agent, "village_id", None) is not None:
                village = world.get_village_by_id(agent.village_id)
                if village is not None:
                    village["strategy"] = normalized

        except Exception as e:
            print(f"LLM error: {e}")
        finally:
            agent.llm_pending = False

    def _act_from_goal(self, agent, world) -> Tuple[str, ...]:
        g = (agent.goal or "").lower()

        if "food" in g or "cibo" in g or "eat" in g or "hunt" in g or "farm" in g:
            farm_target = self.fallback.find_farm_target(agent, world, prefer_ripe=True)
            if farm_target is not None:
                return self.fallback.move_towards(agent, world, farm_target)

            target = self.fallback.find_nearest(
                agent, world.food, "food", self.fallback.vision_radius + 2
            )
            if target is not None:
                return self.fallback.move_towards(agent, world, target)

        if "wood" in g or "legn" in g or "tree" in g:
            target = self.fallback.find_nearest(
                agent, world.wood, "wood", self.fallback.vision_radius + 2
            )
            if target is not None:
                return self.fallback.move_towards(agent, world, target)

        if "stone" in g or "pietr" in g or "rock" in g:
            target = self.fallback.find_nearest(
                agent, world.stone, "stone", self.fallback.vision_radius + 2
            )
            if target is not None:
                return self.fallback.move_towards(agent, world, target)

        if "expand" in g or "build" in g or "village" in g or "house" in g:
            if agent.inventory.get("wood", 0) < 8:
                target = self.fallback.find_nearest(
                    agent, world.wood, "wood", self.fallback.vision_radius + 2
                )
                if target is not None:
                    return self.fallback.move_towards(agent, world, target)

            if agent.inventory.get("stone", 0) < 5:
                target = self.fallback.find_nearest(
                    agent, world.stone, "stone", self.fallback.vision_radius + 2
                )
                if target is not None:
                    return self.fallback.move_towards(agent, world, target)

        if "explore" in g or "esplora" in g:
            return self.fallback.wander(agent, world)

        return self.fallback.decide(agent, world)

    def _make_prompt(self, agent, world) -> str:
        role = getattr(agent, "role", "npc")
        village_summary = ""

        if getattr(agent, "village_id", None) is not None:
            village = world.get_village_by_id(agent.village_id)
            if village is not None:
                village_summary = (
                    f"village_id={village['id']}\n"
                    f"village_houses={village['houses']}\n"
                    f"village_population={village['population']}\n"
                    f"current_strategy={village.get('strategy', 'none')}\n"
                    f"relation={village.get('relation', 'peace')}\n"
                    f"target_village_id={village.get('target_village_id')}\n"
                    f"migration_target_id={village.get('migration_target_id')}\n"
                    f"power={village.get('power', 0)}\n"
                    f"farms={len(getattr(world, 'farm_plots', {}))}\n"
                )

        if role == "leader":
            return (
                "You are the leader of a village in a tile world.\n"
                "Return only one short goal.\n"
                "Allowed goals: expand village, gather food, gather wood, gather stone, explore.\n"
                f"{village_summary}"
                f"tick={world.tick}\n"
                f"position=({agent.x},{agent.y})\n"
                f"hunger={agent.hunger}\n"
                f"inventory={agent.inventory}\n"
            )

        return (
            "You are the high-level brain of a player character in a tile world.\n"
            "Return only one short goal.\n"
            "Allowed goals: gather food, gather wood, gather stone, explore.\n"
            f"tick={world.tick}\n"
            f"position=({agent.x},{agent.y})\n"
            f"hunger={agent.hunger}\n"
            f"inventory={agent.inventory}\n"
        )