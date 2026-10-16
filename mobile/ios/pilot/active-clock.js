"use strict";
class ActiveClock {
  constructor(now = () => performance.now()) { this.now = now; this.reset(); }
  reset(paused = false) { this.active = 0; this.anchor = this.now(); this.paused = paused; }
  elapsed() { return this.active + (this.paused ? 0 : Math.max(0, this.now() - this.anchor)); }
  pause() { if (!this.paused) { this.active = this.elapsed(); this.paused = true; } }
  resume() { if (this.paused) { this.anchor = this.now(); this.paused = false; } }
}
if (typeof module !== "undefined") module.exports = ActiveClock;
