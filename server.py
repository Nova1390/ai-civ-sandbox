import asyncio
import random
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from config import TICK_SPEED, WIDTH, HEIGHT
from world import World
from agent import Agent
from brain import FoodBrain

app = FastAPI()
world = World()


async def tick_loop():
    while True:
        world.update()
        await asyncio.sleep(TICK_SPEED)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tick_loop())


@app.get("/")
def home():
    return FileResponse("client.html")


@app.get("/state")
def get_state():
    agents = [
        {
            "x": a.x,
            "y": a.y,
            "hunger": a.hunger,
            "is_player": a.is_player,
            "player_id": a.player_id,
            "current_goal": a.current_goal,
        }
        for a in world.agents
    ]
    food = [{"x": fx, "y": fy} for (fx, fy) in world.food]

    return {
        "tick": world.tick,
        "agents_alive": len(world.agents),
        "food_count": len(world.food),
        "last_births": world.last_births,
        "last_deaths": world.last_deaths,
        "last_eaten": world.last_eaten,
        "total_births": world.total_births,
        "total_deaths": world.total_deaths,
        "total_eaten": world.total_eaten,
        "agents": agents,
        "food": food,
        "width": WIDTH,
        "height": HEIGHT,
    }


def find_player(player_id: str) -> Agent:
    for a in world.agents:
        if a.is_player and a.player_id == player_id:
            return a
    raise HTTPException(status_code=404, detail="Player not found")


@app.post("/spawn_player")
def spawn_player():
    x = random.randint(0, WIDTH - 1)
    y = random.randint(0, HEIGHT - 1)

    pid = str(uuid4())

    # per ora: brain semplice così si muove e sopravvive
    player = Agent(x, y, brain=FoodBrain(), is_player=True, player_id=pid)
    player.inventory["food"] = 5

    world.agents.append(player)

    return {"status": "spawned", "player_id": pid, "x": x, "y": y}


@app.get("/player/{player_id}")
def get_player(player_id: str):
    p = find_player(player_id)
    return {
        "player_id": p.player_id,
        "x": p.x,
        "y": p.y,
        "hunger": p.hunger,
        "inventory": p.inventory,
        "current_goal": p.current_goal,
        "current_plan": p.current_plan,
        "goals_queue": p.goals_queue,
    }


@app.post("/player/{player_id}/buy/{item}")
def buy_item(player_id: str, item: str, qty: int = 1):
    if qty < 1 or qty > 100:
        raise HTTPException(status_code=400, detail="qty must be 1..100")

    p = find_player(player_id)

    if item not in p.inventory:
        raise HTTPException(status_code=400, detail="Unknown item")

    # TODO: qui poi verificheremo una tx Solana prima di accreditare
    p.inventory[item] += qty

    return {"status": "ok", "inventory": p.inventory}


class Command(BaseModel):
    text: str
    horizon: str = "short"  # short|medium|long (per ora solo label)


@app.post("/player/{player_id}/command")
def player_command(player_id: str, command: Command):
    p = find_player(player_id)
    goal = {"text": command.text, "horizon": command.horizon}
    p.goals_queue.append(goal)
    return {"status": "goal_added", "goal": goal, "queue_len": len(p.goals_queue)}


@app.get("/grid", response_class=PlainTextResponse)
def grid():
    g = world.generate_grid()
    return "\n".join([" ".join(row) for row in g])