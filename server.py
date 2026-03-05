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
            "role": a.role,
            "current_goal": a.current_goal,
        }
        for a in world.agents
    ]

    food = [{"x": x, "y": y} for (x, y) in world.food]
    wood = [{"x": x, "y": y} for (x, y) in world.wood]
    stone = [{"x": x, "y": y} for (x, y) in world.stone]

    tiles_rows = ["".join(row) for row in world.tiles]

    overlay = [{"x": x, "y": y, "t": t} for (x, y), t in world.overlay.items()]

    return {
        "tick": world.tick,
        "agents_alive": len(world.agents),
        "agents": agents,
        "food": food,
        "wood": wood,
        "stone": stone,
        "tiles": tiles_rows,
        "overlay": overlay,
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
    while True:
        x = random.randint(0, WIDTH - 1)
        y = random.randint(0, HEIGHT - 1)
        if world.is_walkable(x, y):
            break

    pid = str(uuid4())

    player = Agent(
        x,
        y,
        brain=FoodBrain(),
        is_player=True,
        player_id=pid,
        role="player",
    )

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
        "traits": p.traits,
        "personality": p.personality,
        "role": p.role,
        "current_goal": p.current_goal,
        "current_plan": p.current_plan,
        "goals_queue": p.goals_queue,
    }


class Command(BaseModel):
    text: str
    horizon: str = "short"


@app.post("/player/{player_id}/command")
def player_command(player_id: str, command: Command):
    p = find_player(player_id)
    goal = {"text": command.text, "horizon": command.horizon}
    p.goals_queue.append(goal)
    return {"status": "goal_added", "goal": goal}


@app.get("/grid", response_class=PlainTextResponse)
def grid():
    g = world.generate_grid()
    return "\n".join([" ".join(row) for row in g])