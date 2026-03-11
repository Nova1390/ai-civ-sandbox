const Renderer = {
  canvas: null,
  ctx: null,
  minimapCanvas: null,
  minimapCtx: null,
  connectionPanel: null,
  summaryPanel: null,
  infraPanel: null,
  civStatsPanel: null,
  villagesMeta: null,
  villageList: null,
  agentsMeta: null,
  agentList: null,
  hoverPanel: null,
  selectionPanel: null,
  layerToggles: null,
  statusBar: null,
  quickStatEls: null,

  selectedTile: null,
  hoverTile: null,
  selectedVillageUid: "",
  _lastDataKey: "",
  _lastHoverKey: "",
  _lastSelectionKey: "",

  onSelectVillage: null,

  init() {
    this.canvas = document.getElementById("world");
    this.ctx = this.canvas.getContext("2d");
    this.minimapCanvas = document.getElementById("minimap");
    this.minimapCtx = this.minimapCanvas ? this.minimapCanvas.getContext("2d") : null;

    this.connectionPanel = document.getElementById("connectionPanel");
    this.summaryPanel = document.getElementById("summaryPanel");
    this.infraPanel = document.getElementById("infraPanel");
    this.civStatsPanel = document.getElementById("civStatsPanel");
    this.villagesMeta = document.getElementById("villagesMeta");
    this.villageList = document.getElementById("villageList");
    this.agentsMeta = document.getElementById("agentsMeta");
    this.agentList = document.getElementById("agentList");
    this.hoverPanel = document.getElementById("hoverPanel");
    this.selectionPanel = document.getElementById("selectionPanel");
    this.layerToggles = document.getElementById("layerToggles");
    this.statusBar = document.getElementById("statusBar");
    this.quickStatEls = {
      tick: document.getElementById("qsTick"),
      population: document.getElementById("qsPopulation"),
      villages: document.getElementById("qsVillages"),
      farms: document.getElementById("qsFarms"),
      houses: document.getElementById("qsHouses"),
      agents: document.getElementById("qsAgents"),
    };

    this.bindLayerToggles();
    this.bindVillageList();
  },

  bindLayerToggles() {
    this.layerToggles.innerHTML = "";
    const keys = Object.keys(Layers.toggles);
    for (const key of keys) {
      const id = `layer_${key}`;
      const label = document.createElement("label");
      label.className = "toggle-item";
      label.setAttribute("for", id);

      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = id;
      input.checked = !!Layers.toggles[key];
      input.addEventListener("change", () => {
        Layers.toggles[key] = input.checked;
      });

      const text = document.createElement("span");
      text.textContent = key;

      label.appendChild(input);
      label.appendChild(text);
      this.layerToggles.appendChild(label);
    }
  },

  bindVillageList() {
    this.villageList.addEventListener("click", (event) => {
      const row = event.target.closest(".list-item[data-vuid]");
      if (!row) return;
      const uid = String(row.dataset.vuid || "");
      this.selectedVillageUid = uid;
      if (typeof this.onSelectVillage === "function") {
        this.onSelectVillage(uid);
      }
    });
  },

  setHoverTile(tile) {
    this.hoverTile = tile;
  },

  setSelectedTile(tile) {
    this.selectedTile = tile;
  },

  setSelectedVillage(uid) {
    this.selectedVillageUid = String(uid || "");
  },

  draw() {
    const data = State.data;
    if (!data) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.renderStatusBar(null);
      this.renderConnection();
      return;
    }

    const selectedVillage = this.getSelectedVillage(data);

    Layers.draw(this.ctx, data, State.indexes || State.buildIndexes(data), Camera, this.canvas, {
      selectedTile: this.selectedTile,
      hoverTile: this.hoverTile,
      selectedVillageUid: this.selectedVillageUid,
      selectedVillage,
    });
    this.drawMinimap(data);

    this.renderStatusBar(data);
    this.renderConnection();

    const dataKey = `${this.v(data.state_version)}|${this.v(data.tick)}|${this.v(data.villages?.length)}|${this.v(data.agents?.length)}|${this.v(State.status.lastDynamicAt)}`;
    if (dataKey !== this._lastDataKey) {
      this._lastDataKey = dataKey;
      this.renderSummary(data);
      this.renderInfrastructure(data);
      this.renderCivStats(data);
      this.renderVillageList(data);
      this.renderAgentList(data);
    }

    const hoverKey = this.hoverTile ? `${this.hoverTile.x},${this.hoverTile.y}|${dataKey}` : `none|${dataKey}`;
    if (hoverKey !== this._lastHoverKey) {
      this._lastHoverKey = hoverKey;
      this.renderHoverPanel(data);
    }

    const selectionKey = `${this.selectedVillageUid}|${this.selectedTile ? `${this.selectedTile.x},${this.selectedTile.y}` : "none"}|${dataKey}`;
    if (selectionKey !== this._lastSelectionKey) {
      this._lastSelectionKey = selectionKey;
      this.renderSelectionPanel(data, selectedVillage);
    }
  },

  kvGrid(el, rows) {
    el.innerHTML = rows.map(([k, v]) => `<div class="kv-k">${this.escapeHtml(k)}</div><div>${this.escapeHtml(v)}</div>`).join("");
  },

  renderConnection() {
    const s = State.status;
    this.kvGrid(this.connectionPanel, [
      ["API base", State.apiBase || "(same origin)"],
      ["/state/static", s.staticOk ? "ok" : "error"],
      ["/state", s.dynamicOk ? "ok" : "error"],
      ["last static", this.formatTime(s.lastStaticAt)],
      ["last dynamic", this.formatTime(s.lastDynamicAt)],
      ["static error", s.staticError || "-"],
      ["dynamic error", s.dynamicError || "-"],
    ]);

    const values = this.connectionPanel.querySelectorAll("div:nth-child(even)");
    if (values[1]) values[1].className = State.status.staticOk ? "ok" : "bad";
    if (values[2]) values[2].className = State.status.dynamicOk ? "ok" : "bad";
  },

  renderStatusBar(data) {
    if (!this.statusBar) return;
    const s = State.status || {};
    const staticPart = s.staticOk ? "ok" : "error";
    const dynamicPart = s.dynamicOk ? "ok" : "error";
    const tick = data ? this.v(data.tick) : "-";
    const stateVersion = data ? this.v(data.state_version) : "-";
    const updated = this.formatTime(s.lastDynamicAt || s.lastStaticAt);
    const err = s.dynamicError || s.staticError || "";

    this.statusBar.innerHTML = [
      `<div class="status-tile"><div class="status-k">static</div><div class="status-v ${s.staticOk ? "ok" : "bad"}">${this.escapeHtml(staticPart)}</div></div>`,
      `<div class="status-tile"><div class="status-k">dynamic</div><div class="status-v ${s.dynamicOk ? "ok" : "bad"}">${this.escapeHtml(dynamicPart)}</div></div>`,
      `<div class="status-tile"><div class="status-k">tick</div><div class="status-v">${this.escapeHtml(tick)}</div></div>`,
      `<div class="status-tile"><div class="status-k">state version</div><div class="status-v">${this.escapeHtml(stateVersion)}</div></div>`,
      `<div class="status-tile"><div class="status-k">updated</div><div class="status-v">${this.escapeHtml(updated)}</div></div>`,
      `<div class="status-tile"><div class="status-k">error</div><div class="status-v ${err ? "bad" : ""}">${this.escapeHtml(err || "-")}</div></div>`,
    ].join("");
  },

  renderSummary(data) {
    if (this.quickStatEls) {
      if (this.quickStatEls.tick) this.quickStatEls.tick.textContent = this.v(data.tick);
      if (this.quickStatEls.population) this.quickStatEls.population.textContent = this.v(data.population);
      if (this.quickStatEls.villages) this.quickStatEls.villages.textContent = this.v(data.villages_count);
      if (this.quickStatEls.farms) this.quickStatEls.farms.textContent = this.v(data.farms_count);
      if (this.quickStatEls.houses) this.quickStatEls.houses.textContent = this.v(data.houses_count);
      if (this.quickStatEls.agents) this.quickStatEls.agents.textContent = this.v((data.agents || []).length);
    }

    this.kvGrid(this.summaryPanel, [
      ["schema_version", this.v(data.schema_version)],
      ["state_version", this.v(data.state_version)],
      ["tick", this.v(data.tick)],
      ["population", this.v(data.population)],
      ["players", this.v(data.players)],
      ["npcs", this.v(data.npcs)],
      ["avg_hunger", this.v(data.avg_hunger)],
      ["food_count", this.v(data.food_count)],
      ["wood_count", this.v(data.wood_count)],
      ["stone_count", this.v(data.stone_count)],
      ["houses_count", this.v(data.houses_count)],
      ["villages_count", this.v(data.villages_count)],
      ["farms_count", this.v(data.farms_count)],
      ["leaders_count", this.v(data.leaders_count)],
      ["llm_interactions", this.v(data.llm_interactions)],
    ]);
  },

  renderInfrastructure(data) {
    const systems = Array.isArray(data.infrastructure_systems_available)
      ? data.infrastructure_systems_available.join(", ")
      : "-";

    const counts = data.transport_network_counts && typeof data.transport_network_counts === "object"
      ? Object.entries(data.transport_network_counts).map(([k, v]) => `${k}:${v}`).join(", ")
      : "-";

    this.kvGrid(this.infraPanel, [
      ["systems", systems || "-"],
      ["transport_network_counts", counts || "-"],
    ]);
  },

  renderCivStats(data) {
    const c = data.civ_stats || {};
    this.kvGrid(this.civStatsPanel, [
      ["largest_village_id", this.v(c.largest_village_id)],
      ["largest_village_houses", this.v(c.largest_village_houses)],
      ["strongest_village_id", this.v(c.strongest_village_id)],
      ["strongest_village_power", this.v(c.strongest_village_power)],
      ["expanding_village_id", this.v(c.expanding_village_id)],
      ["warring_villages", this.v(c.warring_villages)],
      ["migrating_villages", this.v(c.migrating_villages)],
    ]);
  },

  renderVillageList(data) {
    const villages = Array.isArray(data.villages) ? data.villages : [];
    this.villagesMeta.textContent = `${villages.length} villages`;

    const rows = villages.map((v) => {
      const idOrUid = v.id != null ? `V${v.id}` : String(v.village_uid || "-");
      const title = `${idOrUid} pop=${this.v(v.population)} houses=${this.v(v.houses)} pri=${this.v(v.priority)} strat=${this.v(v.strategy)} rel=${this.v(v.relation)} power=${this.v(v.power)}`;
      const selected = String(v.village_uid || "") === String(this.selectedVillageUid || "") ? " selected" : "";
      return `<div class="list-item${selected}" data-vuid="${this.escapeAttr(String(v.village_uid || ""))}">${this.escapeHtml(title)}</div>`;
    });

    this.villageList.innerHTML = rows.join("") || '<div class="list-item">-</div>';
  },

  renderAgentList(data) {
    const all = Array.isArray(data.agents) ? data.agents : [];
    const filter = String(document.getElementById("agentFilterInput")?.value || "").trim().toLowerCase();
    const cap = Number(document.getElementById("agentCapSelect")?.value || 100);

    const filtered = filter
      ? all.filter((a) => {
          const hay = `${a.agent_id || ""} ${a.role || ""} ${a.task || ""} ${a.village_id ?? ""}`.toLowerCase();
          return hay.includes(filter);
        })
      : all;

    const capped = filtered.slice(0, cap);
    this.agentsMeta.textContent = `showing ${capped.length}/${filtered.length} (total ${all.length})`;

    const rows = capped.map((a) => {
      const who = a.is_player ? "player" : "npc";
      const label = `${a.agent_id || "-"} @ (${a.x},${a.y}) ${who} role=${a.role || "-"} task=${a.task || "-"} v=${a.village_id ?? "-"}`;
      return `<div class="list-item">${this.escapeHtml(label)}</div>`;
    });

    this.agentList.innerHTML = rows.join("") || '<div class="list-item">-</div>';
  },

  renderHoverPanel(data) {
    const tile = this.hoverTile;
    if (!tile) {
      this.hoverPanel.innerHTML = this.inspectGroup(
        "Hover Tile",
        this.inspectRow("status", "none"),
      );
      return;
    }

    const idx = State.indexes || State.buildIndexes(data);
    const key = `${tile.x},${tile.y}`;

    const row = Array.isArray(data.tiles) ? data.tiles[tile.y] : null;
    const terrain = (Array.isArray(row) ? row[tile.x] : null);
    const farm = idx.farmsByTile.get(key) || null;
    const buildings = idx.buildingsByTile.get(key) || [];
    const villages = idx.villagesByTile.get(key) || [];
    const agents = idx.agentsByTile.get(key) || [];

    const resourceKinds = [
      idx.foodSet.has(key) ? "food" : null,
      idx.woodSet.has(key) ? "wood" : null,
      idx.stoneSet.has(key) ? "stone" : null,
    ].filter(Boolean).join(", ") || "none";

    const groups = [];
    groups.push(this.inspectGroup("Tile", [
      this.inspectRow("coordinates", `(${tile.x}, ${tile.y})`),
      this.inspectRow("terrain", `${this.v(terrain)} (${this.terrainLabel(terrain)})`),
      this.inspectRow("resources", resourceKinds),
    ].join("")));

    groups.push(this.inspectGroup("Overlay", [
      this.inspectRow("farm", farm ? `${this.v(farm.state)} g=${this.v(farm.growth)} v=${this.v(farm.village_id)}` : "none"),
      this.inspectRow("road", idx.roadsSet.has(key) ? "yes" : "no"),
      this.inspectRow("legacy structure", idx.structuresSet.has(key) ? "yes" : "no"),
      this.inspectRow("legacy storage", idx.storageLegacySet.has(key) ? "yes" : "no"),
      this.inspectRow("buildings", String(buildings.length)),
      this.inspectRow("villages", String(villages.length)),
      this.inspectRow("agents", String(agents.length)),
    ].join("")));

    this.hoverPanel.innerHTML = groups.join("");
  },

  renderSelectionPanel(data, selectedVillage) {
    const tile = this.selectedTile;
    if (!tile || !this.isTileInside(tile, data)) {
      this.selectionPanel.innerHTML = this.inspectGroup("Selected Tile", this.inspectRow("status", "none"));
      return;
    }

    const idx = State.indexes || State.buildIndexes(data);
    const key = `${tile.x},${tile.y}`;
    const row = Array.isArray(data.tiles) ? data.tiles[tile.y] : null;
    const terrainCode = (Array.isArray(row) ? row[tile.x] : null);
    const terrainLabel = this.terrainLabel(terrainCode);
    const farm = idx.farmsByTile.get(key) || null;
    const hasRoad = idx.roadsSet.has(key);
    const hasStructure = idx.structuresSet.has(key);
    const hasStorageLegacy = idx.storageLegacySet.has(key);
    const buildings = idx.buildingsByTile.get(key) || [];
    const villages = idx.villagesByTile.get(key) || [];
    const agents = idx.agentsByTile.get(key) || [];

    const parts = [];
    parts.push(this.inspectGroup("Selected Tile", [
      this.inspectRow("coordinates", `(${tile.x}, ${tile.y})`),
    ].join("")));

    parts.push(this.inspectGroup("Terrain", [
      this.inspectRow("code", this.v(terrainCode)),
      this.inspectRow("label", terrainLabel),
    ].join("")));

    parts.push(this.inspectGroup("Resources", [
      this.inspectRow("food", idx.foodSet.has(key) ? "yes" : "no"),
      this.inspectRow("wood", idx.woodSet.has(key) ? "yes" : "no"),
      this.inspectRow("stone", idx.stoneSet.has(key) ? "yes" : "no"),
    ].join("")));

    parts.push(this.inspectGroup("Farm", farm ? [
      this.inspectRow("exists", "yes"),
      this.inspectRow("state", this.v(farm.state)),
      this.inspectRow("growth", this.v(farm.growth)),
      this.inspectRow("village_id", this.v(farm.village_id)),
    ].join("") : this.inspectRow("exists", "no")));

    parts.push(this.inspectGroup("Infrastructure", [
      this.inspectRow("road", hasRoad ? "yes" : "no"),
      this.inspectRow("structure", hasStructure ? "yes" : "no"),
      this.inspectRow("storage_building", hasStorageLegacy ? "yes" : "no"),
    ].join("")));

    const buildingItems = buildings.map((b, i) => this.inspectItem(
      `Building ${i + 1}`,
      [
        this.inspectRow("building_id", this.v(b.building_id)),
        this.inspectRow("type", this.v(b.type)),
        this.inspectRow("category", this.v(b.category)),
        this.inspectRow("tier", this.v(b.tier)),
        this.inspectRow("village_id", this.v(b.village_id)),
        this.inspectRow("village_uid", this.v(b.village_uid)),
        this.inspectRow("connected_to_road", this.v(b.connected_to_road)),
        this.inspectRow("operational_state", this.v(b.operational_state)),
        this.inspectRow("linked_resource_type", this.v(b.linked_resource_type)),
        this.inspectRow("linked_resource_tiles_count", this.v(b.linked_resource_tiles_count)),
        this.inspectRow("storage", this.stringify(b.storage)),
        this.inspectRow("storage_capacity", this.v(b.storage_capacity)),
        this.inspectRow("construction_progress", this.v(b.construction_progress)),
        this.inspectRow("construction_required_work", this.v(b.construction_required_work)),
        this.inspectRow("construction_complete_ratio", this.v(b.construction_complete_ratio)),
      ].join(""),
    ));
    parts.push(this.inspectGroup(
      "Buildings (canonical)",
      buildings.length > 0 ? `<div class="inspect-sublist">${buildingItems.join("")}</div>` : this.inspectRow("status", "none"),
    ));

    const villageItems = villages.map((v, i) => this.inspectItem(
      `Village ${i + 1}`,
      [
        this.inspectRow("id", this.v(v.id)),
        this.inspectRow("village_uid", this.v(v.village_uid)),
        this.inspectRow("center", this.stringify(v.center)),
        this.inspectRow("houses", this.v(v.houses)),
        this.inspectRow("population", this.v(v.population)),
        this.inspectRow("strategy", this.v(v.strategy)),
        this.inspectRow("priority", this.v(v.priority)),
        this.inspectRow("relation", this.v(v.relation)),
        this.inspectRow("power", this.v(v.power)),
        this.inspectRow("leader_id", this.v(v.leader_id)),
        this.inspectRow("target_village_id", this.v(v.target_village_id)),
        this.inspectRow("migration_target_id", this.v(v.migration_target_id)),
        this.inspectRow("storage", this.stringify(v.storage)),
        this.inspectRow("farm_zone_center", this.stringify(v.farm_zone_center)),
        this.inspectRow("metrics", this.stringify(v.metrics)),
        this.inspectRow("needs", this.stringify(v.needs)),
        this.inspectRow("phase", this.v(v.phase)),
      ].join(""),
    ));
    parts.push(this.inspectGroup(
      "Village",
      villages.length > 0 ? `<div class="inspect-sublist">${villageItems.join("")}</div>` : this.inspectRow("status", "none"),
    ));

    const agentItems = agents.map((a, i) => this.inspectItem(
      `Agent ${i + 1}`,
      [
        this.inspectRow("agent_id", this.v(a.agent_id)),
        this.inspectRow("is_player", this.v(a.is_player)),
        this.inspectRow("player_id", this.v(a.player_id)),
        this.inspectRow("role", this.v(a.role)),
        this.inspectRow("village_id", this.v(a.village_id)),
        this.inspectRow("task", this.v(a.task)),
        this.inspectRow("inventory", this.stringify(a.inventory)),
        this.inspectRow("max_inventory", this.v(a.max_inventory)),
      ].join(""),
    ));
    parts.push(this.inspectGroup(
      "Agents",
      agents.length > 0 ? `<div class="inspect-sublist">${agentItems.join("")}</div>` : this.inspectRow("status", "none"),
    ));

    this.selectionPanel.innerHTML = parts.join("");
  },

  getSelectedVillage(data) {
    if (!this.selectedVillageUid) return null;
    const idx = State.indexes || State.buildIndexes(data);
    return idx.villagesByUid.get(String(this.selectedVillageUid)) || null;
  },

  worldToTile(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    const wx = Math.floor(Camera.x + (px / Camera.cellSize));
    const wy = Math.floor(Camera.y + (py / Camera.cellSize));
    return { x: wx, y: wy };
  },

  isTileInside(tile, data) {
    if (!tile || !data) return false;
    const w = Number(data.width);
    const h = Number(data.height);
    if (!Number.isFinite(w) || !Number.isFinite(h)) return false;
    return tile.x >= 0 && tile.y >= 0 && tile.x < w && tile.y < h;
  },

  selectVillageByTile(tile, data) {
    const idx = State.indexes || State.buildIndexes(data);
    const villages = idx.villagesByTile.get(`${tile.x},${tile.y}`) || [];
    if (villages.length > 0) {
      this.selectedVillageUid = String(villages[0].village_uid || "");
      return;
    }

    const centered = idx.villagesByCenter.get(`${tile.x},${tile.y}`);
    if (centered) {
      this.selectedVillageUid = String(centered.village_uid || "");
      return;
    }

    this.selectedVillageUid = "";
  },

  formatTime(ts) {
    if (!ts) return "-";
    const d = new Date(ts);
    return `${d.toLocaleTimeString()} (${d.toLocaleDateString()})`;
  },

  v(value) {
    return value == null ? "-" : String(value);
  },

  stringify(value) {
    if (value == null) return "-";
    if (typeof value === "string") return value;
    try {
      return JSON.stringify(value);
    } catch (_) {
      return String(value);
    }
  },

  escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  },

  escapeAttr(value) {
    return this.escapeHtml(value).replaceAll("`", "");
  },

  inspectRow(key, value) {
    return `<div class="inspect-row"><div class="inspect-key">${this.escapeHtml(key)}</div><div class="inspect-val">${this.inspectValueHtml(value)}</div></div>`;
  },

  inspectGroup(title, body) {
    return `<div class="inspect-group"><div class="inspect-title">${this.escapeHtml(title)}</div>${body}</div>`;
  },

  inspectItem(title, body) {
    return `<div class="inspect-item"><div class="inspect-title">${this.escapeHtml(title)}</div>${body}</div>`;
  },

  inspectValueHtml(value) {
    const raw = value == null ? "-" : String(value);
    const lower = raw.toLowerCase();
    if (lower === "yes") return '<span class="inspect-badge inspect-badge--yes">yes</span>';
    if (lower === "no") return '<span class="inspect-badge inspect-badge--no">no</span>';
    if (lower === "none" || lower === "-") return `<span class="inspect-badge">${this.escapeHtml(raw)}</span>`;
    if (raw.length <= 22) return `<span class="inspect-badge inspect-badge--value">${this.escapeHtml(raw)}</span>`;
    return this.escapeHtml(raw);
  },

  terrainLabel(code) {
    if (code === "G") return "grass";
    if (code === "F") return "forest";
    if (code === "M") return "mountain";
    if (code === "W") return "water";
    if (code === "H") return "hill";
    return "unknown";
  },

  drawMinimap(data) {
    if (!this.minimapCanvas || !this.minimapCtx) return;
    const ctx = this.minimapCtx;
    const canvas = this.minimapCanvas;
    const w = canvas.width;
    const h = canvas.height;
    const worldW = Math.max(1, Number(data.width) || 1);
    const worldH = Math.max(1, Number(data.height) || 1);
    const sx = w / worldW;
    const sy = h / worldH;

    ctx.clearRect(0, 0, w, h);

    const step = Math.max(1, Math.floor(worldW / 180));
    for (let y = 0; y < worldH; y += step) {
      const row = Array.isArray(data.tiles) ? data.tiles[y] : null;
      for (let x = 0; x < worldW; x += step) {
        const code = Array.isArray(row) ? row[x] : null;
        ctx.fillStyle = Layers.terrainColor(code);
        ctx.fillRect(x * sx, y * sy, step * sx, step * sy);
      }
    }

    for (const r of data.roads || []) {
      ctx.fillStyle = "#c2a27a";
      ctx.fillRect(r.x * sx, r.y * sy, Math.max(1, sx), Math.max(1, sy));
    }

    for (const f of data.farms || []) {
      ctx.fillStyle = Layers.farmColor(String(f.state || ""));
      ctx.fillRect(f.x * sx, f.y * sy, Math.max(1, sx), Math.max(1, sy));
    }

    for (const b of data.buildings || []) {
      const footprint = Array.isArray(b.footprint) && b.footprint.length > 0 ? b.footprint : [{ x: b.x, y: b.y }];
      for (const t of footprint) {
        ctx.fillStyle = Layers.buildingFill(b);
        ctx.fillRect(t.x * sx, t.y * sy, Math.max(1, sx), Math.max(1, sy));
      }
    }

    for (const a of data.agents || []) {
      ctx.fillStyle = a.is_player ? "#ff6464" : "#63b7ff";
      ctx.fillRect(a.x * sx, a.y * sy, Math.max(1, sx), Math.max(1, sy));
    }

    if (this.selectedTile && this.isTileInside(this.selectedTile, data)) {
      ctx.strokeStyle = "#ffe38d";
      ctx.lineWidth = 1;
      ctx.strokeRect(this.selectedTile.x * sx, this.selectedTile.y * sy, Math.max(1, sx), Math.max(1, sy));
    }

    const viewW = Camera.getViewWidth(this.canvas);
    const viewH = Camera.getViewHeight(this.canvas);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    ctx.strokeRect(Camera.x * sx, Camera.y * sy, Math.max(2, viewW * sx), Math.max(2, viewH * sy));
  },
};
