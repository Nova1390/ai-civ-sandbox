const Camera = {
  x: 0,
  y: 0,
  cellSize: 24,
  minCellSize: 10,
  maxCellSize: 48,
  followPlayer: true,

  getViewW(canvas) {
    return Math.floor(canvas.width / this.cellSize);
  },

  getViewH(canvas) {
    return Math.floor(canvas.height / this.cellSize);
  },

  clamp(data, canvas) {
    const viewW = this.getViewW(canvas);
    const viewH = this.getViewH(canvas);

    this.x = Math.max(0, Math.min(this.x, Math.max(0, data.width - viewW)));
    this.y = Math.max(0, Math.min(this.y, Math.max(0, data.height - viewH)));
  },

  centerOn(wx, wy, canvas, data) {
    const viewW = this.getViewW(canvas);
    const viewH = this.getViewH(canvas);

    this.x = Math.floor(wx - viewW / 2);
    this.y = Math.floor(wy - viewH / 2);

    this.clamp(data, canvas);
  }
};