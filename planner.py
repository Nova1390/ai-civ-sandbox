def plan_from_goal(goal):

    text = goal["text"].lower()

    if "food" in text:
        return [
            {"action":"gather","resource":"food"}
        ]

    if "house" in text:
        return [
            {"action":"gather","resource":"wood"},
            {"action":"gather","resource":"stone"},
            {"action":"build","structure":"house"}
        ]

    if "attack" in text:
        return [
            {"action":"find_target"},
            {"action":"attack"}
        ]

    return []