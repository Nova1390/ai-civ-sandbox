const State = {
  data: null,
  playerData: null,
  playerId: null,

  async update() {
    const r = await fetch("/state", { cache: "no-store" });
    this.data = await r.json();

    if (this.playerId) {
      const pr = await fetch(`/player/${this.playerId}`, { cache: "no-store" });
      if (pr.status === 200) {
        this.playerData = await pr.json();
      } else {
        this.playerData = null;
      }
    } else {
      this.playerData = null;
    }
  },

  async spawnPlayer() {
    const r = await fetch("/spawn_player", { method: "POST" });
    const data = await r.json();
    this.playerId = data.player_id || null;
  }
};