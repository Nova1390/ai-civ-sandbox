class FoodBrain:
    """
    Brain semplice: va verso il cibo più vicino.
    Se non vede cibo, si muove a caso.
    """

    def decide(self, agent, world):
        if not world.food:
            return 0, 0

        ax, ay = agent.x, agent.y

        # trova cibo più vicino (manhattan)
        best = None
        best_dist = 10**9
        for (fx, fy) in world.food:
            d = abs(fx - ax) + abs(fy - ay)
            if d < best_dist:
                best_dist = d
                best = (fx, fy)

        if best is None:
            return 0, 0

        fx, fy = best
        dx = 0
        dy = 0
        if fx > ax:
            dx = 1
        elif fx < ax:
            dx = -1
        elif fy > ay:
            dy = 1
        elif fy < ay:
            dy = -1

        return dx, dy