import time
import json
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "phi3"
THINK_INTERVAL = 60  # secondi tra un "pensiero" e l'altro


def should_think(agent):
    now = time.time()
    last = getattr(agent, "last_think", 0)
    if now - last >= THINK_INTERVAL:
        agent.last_think = now
        return True
    return False


def build_prompt(agent, world):
    # stato minimo per decisione strategica
    tile = world.tiles[agent.y][agent.x]
    prompt = f"""
You are the strategic brain of an AI agent in a sandbox world.

Agent status:
- position: ({agent.x},{agent.y})
- hunger: {agent.hunger}
- inventory: {agent.inventory}
- biome: {tile}

Environment:
- villages exist
- forest contains wood
- mountains contain stone
- grassland contains food

Available goals:
- gather food
- gather wood
- gather stone
- explore
- return home
- build house

Choose ONE goal for the next minutes.

Respond ONLY in JSON like:
{{"goal":"gather wood"}}
"""
    return prompt.strip()


def ask_llm(prompt: str) -> str:
    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())

    return result["response"]


def think(agent, world):

    prompt = build_prompt(agent, world)

    try:

        response = ask_llm(prompt)

        # debug utile
        print("LLM raw response:", response)

        # trova il JSON nella risposta
        start = response.find("{")
        end = response.rfind("}") + 1

        if start == -1 or end == -1:
            print("LLM: no JSON found")
            return

        json_text = response[start:end]

        data = json.loads(json_text)

        goal = data.get("goal")

        if goal:
            agent.goals_queue.append({
                "text": goal,
                "horizon": "medium"
            })

            print("LLM goal:", goal)

    except Exception as e:
        print("LLM error:", e)