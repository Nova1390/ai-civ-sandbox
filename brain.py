import random

class RandomBrain:
    def decide(self, agent, world):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        return dx, dy


class FoodBrain:
    def decide(self, agent, world):

        closest_food = None
        min_dist = 999

        for fx, fy in world.food:
            dist = abs(agent.x - fx) + abs(agent.y - fy)

            if dist < min_dist:
                min_dist = dist
                closest_food = (fx, fy)

        if closest_food:
            fx, fy = closest_food

            dx = 0
            dy = 0

            if fx > agent.x:
                dx = 1
            elif fx < agent.x:
                dx = -1

            if fy > agent.y:
                dy = 1
            elif fy < agent.y:
                dy = -1

            return dx, dy

        return random.choice([-1,0,1]), random.choice([-1,0,1])