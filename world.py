import random

from config import (
    WIDTH,
    HEIGHT,
    NUM_AGENTS,
    NUM_FOOD,
    FOOD_RESPAWN_PER_TICK,
    MAX_FOOD,
    REPRO_MIN_HUNGER,
    REPRO_PROB,
    REPRO_COST,
    MAX_AGENTS,
    AGENT_START_HUNGER,
)

from agent import Agent
from brain import FoodBrain
from planner import plan_from_goal


class World:
    def __init__(self):
        # NPC iniziali
        self.agents = [
            Agent(
                random.randint(0, WIDTH - 1),
                random.randint(0, HEIGHT - 1),
                brain=FoodBrain(),
                is_player=False,
                player_id=None,
            )
            for _ in range(NUM_AGENTS)
        ]

        # Cibo iniziale
        self.food = {
            (random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1))
            for _ in range(NUM_FOOD)
        }

        # Stats
        self.tick = 0
        self.last_births = 0
        self.last_deaths = 0
        self.last_eaten = 0
        self.total_births = 0
        self.total_deaths = 0
        self.total_eaten = 0

    def _maybe_assign_goal_and_plan(self, agent: Agent):
        # SOLO player: se non ha goal attivo e coda non vuota, prende il prossimo
        if not agent.is_player:
            return

        if agent.current_goal is None and agent.goals_queue:
            agent.current_goal = agent.goals_queue.pop(0)
            agent.current_plan = plan_from_goal(agent.current_goal)

    def _execute_one_plan_step(self, agent: Agent):
        # esegui 1 step per tick (solo player)
        if not agent.is_player:
            return

        if not agent.current_plan:
            return

        step = agent.current_plan[0]
        action = step.get("action")

        if action == "gather":
            resource = step.get("resource")
            if resource in agent.inventory:
                agent.inventory[resource] += 1
            agent.current_plan.pop(0)

        elif action == "build":
            structure = step.get("structure")

            if structure == "house":
                # costi minimi per esempio
                need_wood = 5
                need_stone = 3

                if agent.inventory["wood"] >= need_wood and agent.inventory["stone"] >= need_stone:
                    agent.inventory["wood"] -= need_wood
                    agent.inventory["stone"] -= need_stone
                    # (più avanti: creeremo un oggetto casa nel mondo)
                    agent.current_plan.pop(0)
                else:
                    # se non hai risorse, inserisci gather davanti
                    if agent.inventory["wood"] < need_wood:
                        agent.current_plan.insert(0, {"action": "gather", "resource": "wood"})
                    elif agent.inventory["stone"] < need_stone:
                        agent.current_plan.insert(0, {"action": "gather", "resource": "stone"})
            else:
                agent.current_plan.pop(0)

        elif action == "attack":
            # placeholder: per ora “consuma” lo step
            agent.current_plan.pop(0)

        else:
            # step sconosciuto
            agent.current_plan.pop(0)

        # se finito, libera goal
        if not agent.current_plan:
            agent.current_goal = None

    def update(self):
        self.tick += 1
        self.last_births = 0
        self.last_deaths = 0
        self.last_eaten = 0

        alive_agents = []
        died_this_tick = 0

        # 1) Update agenti + plan (player) + mangiare + morte/respawn
        for agent in self.agents:
            # assegna goal/plan se necessario
            self._maybe_assign_goal_and_plan(agent)

            # esegui 1 step di piano (prima del movimento)
            self._execute_one_plan_step(agent)

            # update normale (movimento + fame)
            agent.update(self)

            # se mangia (cibo a terra)
            if (agent.x, agent.y) in self.food:
                agent.eat()
                self.food.remove((agent.x, agent.y))
                self.last_eaten += 1

            if agent.alive:
                alive_agents.append(agent)
            else:
                died_this_tick += 1

                # PLAYER: respawn automatico (non sparisce mai)
                if agent.is_player:
                    agent.alive = True
                    agent.hunger = AGENT_START_HUNGER
                    agent.x = random.randint(0, WIDTH - 1)
                    agent.y = random.randint(0, HEIGHT - 1)
                    agent.repro_cooldown = 0
                    alive_agents.append(agent)
                # NPC: muore davvero (non viene re-inserito)

        self.agents = alive_agents

        self.last_deaths = died_this_tick
        self.total_deaths += died_this_tick

        # 2) Riproduzione SOLO NPC
        npc_agents = [a for a in self.agents if not a.is_player]

        if len(npc_agents) < MAX_AGENTS:
            pos_map = {}
            for a in npc_agents:
                pos_map.setdefault((a.x, a.y), []).append(a)

            babies = []

            for (x, y), group in pos_map.items():
                if len(group) < 2:
                    continue

                a1, a2 = group[0], group[1]

                can_reproduce = (
                    a1.hunger >= REPRO_MIN_HUNGER
                    and a2.hunger >= REPRO_MIN_HUNGER
                    and a1.repro_cooldown == 0
                    and a2.repro_cooldown == 0
                )

                if can_reproduce and random.random() < REPRO_PROB:
                    a1.hunger -= REPRO_COST
                    a2.hunger -= REPRO_COST
                    a1.repro_cooldown = 10
                    a2.repro_cooldown = 10

                    babies.append(
                        Agent(
                            x,
                            y,
                            brain=FoodBrain(),
                            is_player=False,
                            player_id=None,
                        )
                    )

                if len(npc_agents) + len(babies) >= MAX_AGENTS:
                    break

            self.agents.extend(babies)
            self.last_births = len(babies)
            self.total_births += self.last_births

        # 3) Respawn cibo
        if len(self.food) < MAX_FOOD:
            for _ in range(FOOD_RESPAWN_PER_TICK):
                if len(self.food) >= MAX_FOOD:
                    break
                self.food.add((random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1)))

        self.total_eaten += self.last_eaten

    def generate_grid(self):
        grid = [["." for _ in range(WIDTH)] for _ in range(HEIGHT)]

        for fx, fy in self.food:
            grid[fy][fx] = "F"

        for a in self.agents:
            grid[a.y][a.x] = "P" if a.is_player else "A"

        return grid