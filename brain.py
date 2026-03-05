import random

VISION_RADIUS = 5


class FoodBrain:

    def decide(self, agent, world):

        self.update_memory(agent, world)

        # fame -> cerca food
        if agent.hunger < 10:
            target = self.get_memory_target(agent, "food")
            if target:
                return self.move_toward(agent, world, target)

        # player con plan
        if agent.is_player and agent.current_plan:
            step = agent.current_plan[0]
            if step.get("action") == "gather":
                res = step.get("resource")
                target = self.get_memory_target(agent, res)
                if target:
                    return self.move_toward(agent, world, target)

        # fallback: random walk
        return self.random_walk(agent, world)

    def update_memory(self, agent, world):

        ax, ay = agent.x, agent.y

        for fx, fy in world.food:
            if abs(ax - fx) <= VISION_RADIUS and abs(ay - fy) <= VISION_RADIUS:
                if (fx, fy) not in agent.memory["food"]:
                    agent.memory["food"].append((fx, fy))

        for wx, wy in world.wood:
            if abs(ax - wx) <= VISION_RADIUS and abs(ay - wy) <= VISION_RADIUS:
                if (wx, wy) not in agent.memory["wood"]:
                    agent.memory["wood"].append((wx, wy))

        for sx, sy in world.stone:
            if abs(ax - sx) <= VISION_RADIUS and abs(ay - sy) <= VISION_RADIUS:
                if (sx, sy) not in agent.memory["stone"]:
                    agent.memory["stone"].append((sx, sy))

    def get_memory_target(self, agent, resource):

        if resource not in agent.memory:
            return None

        if not agent.memory[resource]:
            return None

        return random.choice(agent.memory[resource])

    def move_toward(self, agent, world, target):

        tx, ty = target
        ax, ay = agent.x, agent.y

        dx = 0
        dy = 0

        if tx > ax:
            dx = 1
        elif tx < ax:
            dx = -1
        elif ty > ay:
            dy = 1
        elif ty < ay:
            dy = -1

        if world.is_walkable(ax + dx, ay + dy):
            return dx, dy

        return self.random_walk(agent, world)

    def random_walk(self, agent, world):

        moves = [(1,0),(-1,0),(0,1),(0,-1)]
        random.shuffle(moves)

        for dx, dy in moves:
            if world.is_walkable(agent.x + dx, agent.y + dy):
                return dx, dy

        return 0, 0