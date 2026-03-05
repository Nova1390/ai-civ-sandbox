import random


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def plan_from_goal(goal):
    """
    goal può essere:
    - dict {"text": "...", "horizon": "..."}
    - stringa "gather wood"
    Ritorna una lista di step: [{"action": "...", ...}, ...]
    """
    if isinstance(goal, dict):
        text = goal.get("text", "")
    else:
        text = str(goal)

    t = _norm(text)

    # --- GATHER ---
    if "gather wood" in t or ("gather" in t and "wood" in t) or "collect wood" in t:
        return [
            {"action": "gather", "resource": "wood"},
            {"action": "gather", "resource": "wood"},
            {"action": "gather", "resource": "wood"},
            {"action": "return_home"},
        ]

    if "gather stone" in t or ("gather" in t and "stone" in t) or "collect stone" in t:
        return [
            {"action": "gather", "resource": "stone"},
            {"action": "gather", "resource": "stone"},
            {"action": "gather", "resource": "stone"},
            {"action": "return_home"},
        ]

    if "gather food" in t or ("gather" in t and "food" in t) or "collect food" in t or "hunt" in t:
        return [
            {"action": "gather", "resource": "food"},
            {"action": "gather", "resource": "food"},
            {"action": "return_home"},
        ]

    # --- BUILD ---
    if "build house" in t or "build a house" in t or ("build" in t and "house" in t):
        # prerequisiti minimi: wood + stone (li raccogli se mancano)
        return [
            {"action": "ensure", "resource": "wood", "amount": 5},
            {"action": "ensure", "resource": "stone", "amount": 3},
            {"action": "return_home"},
            {"action": "build", "what": "house"},
        ]

    # --- RETURN HOME ---
    if "return home" in t or "go home" in t or "back home" in t:
        return [{"action": "return_home"}]

    # --- EXPLORE ---
    if "explore" in t or "scout" in t or "wander" in t:
        steps = []
        for _ in range(10):
            steps.append({"action": "explore"})
        return steps

    # fallback: se non capisce, esplora un po'
    return [{"action": "explore"} for _ in range(5)]


def next_step(agent, world):
    """
    Esegue/avanza di 1 step del plan.
    Restituisce True se ha consumato uno step, False se no.
    """
    if not agent.current_plan:
        return False

    step = agent.current_plan[0]
    action = step.get("action")

    # 1) gather: il brain già punta la risorsa. Lo step viene consumato quando raccogli.
    # Qui facciamo "consumo immediato" SOLO se già hai raccolto (cioè sei salito di inventory).
    # Per semplicità: se la risorsa è nel tile corrente, world.py già incrementa inventory.
    # Quindi consumiamo lo step quando l'inventario è aumentato rispetto a un contatore locale.
    if action == "gather":
        res = step.get("resource")
        if res not in agent.inventory:
            agent.current_plan.pop(0)
            return True

        # meccanismo semplice: se hai almeno 1 unità del res, consumiamo uno step
        # (non perfetto, ma funziona bene per la base)
        if agent.inventory.get(res, 0) > 0:
            agent.current_plan.pop(0)
            return True

        return False

    # 2) ensure: se inventario < amount, trasformalo in gather steps dinamici
    if action == "ensure":
        res = step.get("resource")
        amt = int(step.get("amount", 1))
        cur = int(agent.inventory.get(res, 0))
        if cur >= amt:
            agent.current_plan.pop(0)
            return True

        # inserisci gather steps prima di questo ensure
        need = amt - cur
        gather_steps = [{"action": "gather", "resource": res} for _ in range(min(need, 5))]
        agent.current_plan = gather_steps + agent.current_plan
        return True

    # 3) return_home: per ora è un marker; il brain può usarlo in futuro.
    # Qui lo consumiamo subito: utile perché non abbiamo ancora home navigation vera.
    if action == "return_home":
        agent.current_plan.pop(0)
        return True

    # 4) build: consumiamo subito; world.py può gestire overlay/house dopo.
    if action == "build":
        agent.current_plan.pop(0)
        return True

    # 5) explore: consumiamo subito (il brain farà random/memory move)
    if action == "explore":
        agent.current_plan.pop(0)
        return True

    # fallback
    agent.current_plan.pop(0)
    return True