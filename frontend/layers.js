const Layers = {
  overlays: {
    roads: true,
    farms: true,
    villages: true,
    heat: true,
  },

  tileColor(t) {
    if (t === "G") return "#6fcf6a";
    if (t === "F") return "#2f8f45";
    if (t === "M") return "#999999";
    if (t === "W") return "#4da6ff";
    return "#ffffff";
  },

  farmColor(state) {
    if (state === "prepared") return "#b38b5a";
    if (state === "planted") return "#2f6f2f";
    if (state === "growing") return "#4caf50";
    if (state === "ripe") return "#d4b000";
    return "#b38b5a";
  },

  strategyColor(strategy) {
    const s = (strategy || "").toLowerCase();
    if (s.includes("food") || s.includes("hunt") || s.includes("eat")) return "lime";
    if (s.includes("wood") || s.includes("tree") || s.includes("legn")) return "#6b4f2a";
    if (s.includes("stone") || s.includes("rock") || s.includes("pietr")) return "#bbbbbb";
    if (s.includes("expand") || s.includes("build") || s.includes("house") || s.includes("village")) return "gold";
    if (s.includes("explore") || s.includes("esplora")) return "violet";
    return "gold";
  },

  buildHouseColorMap(villages) {
    const map = new Map();
    for (const v of (villages || [])) {
      for (const tile of (v.tiles || [])) {
        map.set(`${tile.x},${tile.y}`, v.color || "#8b4513");
      }
    }
    return map;
  },

  terrain(ctx, data, camera, canvas) {
    const s = camera.cellSize;
    const viewW = camera.getViewW(canvas);
    const viewH = camera.getViewH(canvas);

    for (let y = 0; y < viewH; y++) {
      for (let x = 0; x < viewW; x++) {
        const wx = x + camera.x;
        const wy = y + camera.y;

        if (wx < 0 || wy < 0 || wx >= data.width || wy >= data.height) continue;

        ctx.fillStyle = this.tileColor(data.tiles[wy][wx]);
        ctx.fillRect(x * s, y * s, s, s);
      }
    }
  },

  roads(ctx, data, camera, canvas) {
    if (!this.overlays.roads) return;

    const s = camera.cellSize;

    (data.roads || []).forEach(r => {
      const sx = (r.x - camera.x) * s;
      const sy = (r.y - camera.y) * s;

      if (sx < -s || sy < -s || sx > canvas.width || sy > canvas.height) return;

      const pad = Math.floor(s * 0.38);
      ctx.fillStyle = "#c2a27a";
      ctx.fillRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
    });
  },

  resources(ctx, data, camera, canvas) {
    const s = camera.cellSize;

    const drawCell = (x, y, color) => {
      const sx = (x - camera.x) * s;
      const sy = (y - camera.y) * s;

      if (sx < -s || sy < -s || sx > canvas.width || sy > canvas.height) return;

      const pad = Math.floor(s * 0.2);
      ctx.fillStyle = color;
      ctx.fillRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
    };

    (data.food || []).forEach(f => drawCell(f.x, f.y, "#00aa00"));
    (data.wood || []).forEach(w => drawCell(w.x, w.y, "#0b3d1e"));
    (data.stone || []).forEach(st => drawCell(st.x, st.y, "#d3d3d3"));
  },

  buildings(ctx, data, camera, canvas) {
    const s = camera.cellSize;
    const houseColorMap = this.buildHouseColorMap(data.villages);

    (data.structures || []).forEach(h => {
      const sx = (h.x - camera.x) * s;
      const sy = (h.y - camera.y) * s;

      if (sx < -s || sy < -s || sx > canvas.width || sy > canvas.height) return;

      const color = houseColorMap.get(`${h.x},${h.y}`) || "#8b4513";
      ctx.fillStyle = color;
      ctx.fillRect(sx, sy, s, s);
      ctx.strokeStyle = "#1a1a1a";
      ctx.strokeRect(sx, sy, s, s);
    });

    (data.storage_buildings || []).forEach(sb => {
      const sx = (sb.x - camera.x) * s;
      const sy = (sb.y - camera.y) * s;

      if (sx < -s || sy < -s || sx > canvas.width || sy > canvas.height) return;

      const pad = Math.floor(s * 0.18);
      ctx.fillStyle = "#5b3a29";
      ctx.fillRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
      ctx.strokeStyle = "#f5deb3";
      ctx.strokeRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
    });
  },

  farms(ctx, data, camera, canvas) {
    if (!this.overlays.farms) return;

    const s = camera.cellSize;

    (data.farms || []).forEach(f => {
      const sx = (f.x - camera.x) * s;
      const sy = (f.y - camera.y) * s;

      if (sx < -s || sy < -s || sx > canvas.width || sy > canvas.height) return;

      const pad = Math.floor(s * 0.12);
      ctx.fillStyle = this.farmColor(f.state);
      ctx.fillRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
      ctx.strokeStyle = "#222";
      ctx.strokeRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
    });
  },

  villages(ctx, data, camera, canvas) {
    if (!this.overlays.villages) return;

    const s = camera.cellSize;

    if (this.overlays.heat) {
      (data.villages || []).forEach(v => {
        const sx = (v.center.x - camera.x) * s + s / 2;
        const sy = (v.center.y - camera.y) * s + s / 2;

        if (sx < -s || sy < -s || sx > canvas.width + s || sy > canvas.height + s) return;

        const radius = Math.max(8, (v.population || 0) * 0.8);
        const alpha = Math.min(0.25, 0.05 + (v.population || 0) * 0.008);

        ctx.beginPath();
        ctx.arc(sx, sy, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 80, 0, ${alpha})`;
        ctx.fill();
      });
    }

    (data.villages || []).forEach(v => {
      const storagePos = v.storage_pos;
      if (storagePos) {
        const sx = (storagePos.x - camera.x) * s;
        const sy = (storagePos.y - camera.y) * s;

        if (!(sx < -s || sy < -s || sx > canvas.width || sy > canvas.height)) {
          const pad = Math.floor(s * 0.28);
          ctx.fillStyle = "#5b3a29";
          ctx.fillRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
          ctx.strokeStyle = "#f5deb3";
          ctx.strokeRect(sx + pad, sy + pad, s - pad * 2, s - pad * 2);
        }
      }

      const farmZone = v.farm_zone_center;
      if (farmZone) {
        const sx = (farmZone.x - camera.x) * s + s / 2;
        const sy = (farmZone.y - camera.y) * s + s / 2;

        if (!(sx < -s || sy < -s || sx > canvas.width + s || sy > canvas.height + s)) {
          ctx.beginPath();
          ctx.arc(sx, sy, Math.max(2, s * 0.08), 0, Math.PI * 2);
          ctx.fillStyle = "#c7a94a";
          ctx.fill();
        }
      }

      const cx = (v.center.x - camera.x) * s + s / 2;
      const cy = (v.center.y - camera.y) * s + s / 2;

      if (cx < -s || cy < -s || cx > canvas.width + s || cy > canvas.height + s) return;

      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(4, s * 0.15), 0, Math.PI * 2);
      ctx.fillStyle = this.strategyColor(v.strategy);
      ctx.fill();
      ctx.strokeStyle = "#222";
      ctx.stroke();
    });
  },

  agents(ctx, data, camera, canvas) {
    const s = camera.cellSize;

    (data.agents || []).forEach(a => {
      const sx = (a.x - camera.x) * s;
      const sy = (a.y - camera.y) * s;

      if (sx < -s || sy < -s || sx > canvas.width || sy > canvas.height) return;

      const isPlayer = a.is_player && a.player_id === State.playerId;
      ctx.fillStyle = isPlayer ? "red" : "blue";
      ctx.fillRect(sx, sy, s, s);

      if (a.role === "leader") {
        ctx.beginPath();
        ctx.arc(sx + s / 2, sy + s / 2, Math.max(4, s * 0.18), 0, Math.PI * 2);
        ctx.fillStyle = "orange";
        ctx.fill();
      }

      ctx.strokeStyle = "black";
      ctx.lineWidth = 2;
      ctx.strokeRect(sx, sy, s, s);
      ctx.lineWidth = 1;
    });
  },

  minimap(mctx, minimap, data, camera, worldCanvas) {
    const w = minimap.width;
    const h = minimap.height;
    const sx = w / data.width;
    const sy = h / data.height;

    const step = Math.max(2, Math.floor(data.width / 120));
    mctx.clearRect(0, 0, w, h);

    for (let y = 0; y < data.height; y += step) {
      for (let x = 0; x < data.width; x += step) {
        mctx.fillStyle = this.tileColor(data.tiles[y][x]);
        mctx.fillRect(x * sx, y * sy, step * sx, step * sy);
      }
    }

    if (this.overlays.villages) {
      (data.villages || []).forEach(v => {
        const cx = v.center.x * sx;
        const cy = v.center.y * sy;
        const influenceRadius = Math.max(10, (v.houses || 1) * 1.3);

        mctx.beginPath();
        mctx.arc(cx, cy, influenceRadius, 0, Math.PI * 2);
        mctx.fillStyle = "rgba(255, 215, 0, 0.22)";
        mctx.fill();
      });

      if (this.overlays.heat) {
        (data.villages || []).forEach(v => {
          const cx = v.center.x * sx;
          const cy = v.center.y * sy;
          const pop = v.population || 0;
          const heatRadius = Math.max(6, pop * 0.7);
          const alpha = Math.min(0.40, 0.08 + pop * 0.015);

          mctx.beginPath();
          mctx.arc(cx, cy, heatRadius, 0, Math.PI * 2);
          mctx.fillStyle = `rgba(255, 80, 0, ${alpha})`;
          mctx.fill();
        });
      }
    }

    if (this.overlays.roads) {
      (data.roads || []).forEach(r => {
        mctx.fillStyle = "#c2a27a";
        mctx.fillRect(r.x * sx, r.y * sy, Math.max(1.5, sx), Math.max(1.5, sy));
      });
    }

    const houseColorMap = this.buildHouseColorMap(data.villages);

    (data.structures || []).forEach(house => {
      const color = houseColorMap.get(`${house.x},${house.y}`) || "#5a2d0c";
      mctx.fillStyle = color;
      mctx.fillRect(house.x * sx, house.y * sy, Math.max(2, sx), Math.max(2, sy));
    });

    (data.storage_buildings || []).forEach(sb => {
      mctx.fillStyle = "#5b3a29";
      mctx.fillRect(sb.x * sx, sb.y * sy, Math.max(2, sx), Math.max(2, sy));
    });

    if (this.overlays.farms) {
      (data.farms || []).forEach(f => {
        mctx.fillStyle = this.farmColor(f.state);
        mctx.fillRect(f.x * sx, f.y * sy, Math.max(2, sx), Math.max(2, sy));
      });
    }

    if (this.overlays.villages) {
      (data.villages || []).forEach(v => {
        const cx = v.center.x * sx;
        const cy = v.center.y * sy;

        mctx.beginPath();
        mctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
        mctx.fillStyle = this.strategyColor(v.strategy);
        mctx.fill();
        mctx.strokeStyle = "#222";
        mctx.lineWidth = 1;
        mctx.stroke();
      });
    }

    (data.agents || []).forEach(a => {
      const ax = a.x * sx;
      const ay = a.y * sy;

      if (a.role === "leader") {
        mctx.beginPath();
        mctx.arc(ax, ay, 4, 0, Math.PI * 2);
        mctx.fillStyle = "orange";
        mctx.fill();
        return;
      }

      mctx.fillStyle = a.is_player ? "red" : "blue";
      mctx.fillRect(ax, ay, Math.max(1.5, sx * 0.8), Math.max(1.5, sy * 0.8));
    });

    const viewW = camera.getViewW(worldCanvas);
    const viewH = camera.getViewH(worldCanvas);

    mctx.strokeStyle = "#000";
    mctx.lineWidth = 1;
    mctx.strokeRect(camera.x * sx, camera.y * sy, viewW * sx, viewH * sy);
  }
};