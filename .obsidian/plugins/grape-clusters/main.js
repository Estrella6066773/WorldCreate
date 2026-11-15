'use strict';
// One cluster per folder.
const { Plugin, PluginSettingTab, Setting, Notice } = require('obsidian');

const DEFAULTS = { enabled: true, backbone: true, spokes: true, ring: false, spacing: 1, depth: 1, cables: 0.15, inside: 0.4, colorInside: true, summary: false };

// Nodes without links of their own.
const FOLLOWERS = new Set(['tag', 'unresolved', 'attachment']);

// Top folder of a path.
function topFolder(id) {
  const i = id.indexOf('/');
  return i < 0 ? '' : id.slice(0, i);
}

// The folder, as deep as asked.
function folderOf(id, depth) {
  const parts = id.split('/');
  parts.pop();
  return parts.slice(0, Math.max(1, Math.floor(depth) || 1)).join('/');
}

// Is folder a above folder b?
function above(a, b) {
  return a === '' ? b !== '' : b.startsWith(a + '/');
}

// Links the physics may see.
function filterLinks(pairs, ids, typeOf, backbone, depth = 1, spokes = false) {
  const deep = Math.max(1, Math.floor(depth) || 1);
  // Once per note, not per link.
  const folders = new Map();
  const folder = (id) => {
    let f = folders.get(id);
    if (f === undefined) {
      f = deep > 1 ? folderOf(id, deep) : topFolder(id);
      folders.set(id, f);
    }
    return f;
  };
  const kinds = new Map();
  const follows = (id) => {
    let k = kinds.get(id);
    if (k === undefined) {
      k = FOLLOWERS.has(typeOf(id));
      kinds.set(id, k);
    }
    return k;
  };
  const members = new Map();
  for (const id of ids) {
    if (follows(id)) continue;
    const f = folder(id);
    if (!members.has(f)) members.set(f, new Set());
    members.get(f).add(id);
  }
  // Where a follower is used.
  const homes = new Map();
  const home = (id, f) => {
    if (!homes.has(id)) homes.set(id, new Set());
    homes.get(id).add(f);
  };
  // Neighbours inside the folder.
  const inside = new Map();
  const meet = (a, b) => {
    if (!inside.has(a)) inside.set(a, new Set());
    inside.get(a).add(b);
  };
  for (const [a, b] of pairs) {
    const fa = follows(a);
    const fb = follows(b);
    if (fa && !fb) home(a, folder(b));
    else if (fb && !fa) home(b, folder(a));
    else if (!fa && !fb && a !== b && folder(a) === folder(b)) {
      meet(a, b);
      meet(b, a);
    }
  }
  const wheels = new Set();
  const hubOf = new Map();
  // Hub: linked with half its folder.
  const hubs = new Set();
  for (const [f, notes] of members) {
    if (!f) continue;
    const need = Math.ceil((notes.size - 1) / 2);
    let best = 0;
    for (const id of notes) {
      const n = inside.has(id) ? inside.get(id).size : 0;
      if (n < need) continue;
      hubs.add(id);
      wheels.add(f);
      if (n > best) {
        best = n;
        hubOf.set(f, id);
      }
    }
  }
  const soft = [];
  const keep = (a, b) => {
    const fa = follows(a);
    const fb = follows(b);
    if (fa && fb) return true;
    // A follower joins one folder.
    if (fa) return homes.get(a).size === 1;
    if (fb) return homes.get(b).size === 1;
    const A = folder(a);
    const B = folder(b);
    if (A === B) {
      // Spokes: only the hub pulls.
      if (!spokes || !wheels.has(A) || hubs.has(a) || hubs.has(b)) return true;
      soft.push([a, b]);
      return false;
    }
    if (!backbone) return false;
    return (above(A, B) && hubs.has(b)) || (above(B, A) && hubs.has(a));
  };
  const links = pairs.filter(([a, b]) => keep(a, b));
  return {
    links,
    soft,
    folders: [...members.keys()].filter(Boolean),
    hubs: [...hubs],
    wheels: [...wheels],
    hubOf,
    kept: links.length,
    drawnOnly: pairs.length - links.length,
  };
}

// Room a folder needs, roughly.
const SPREAD = 30;
const DEFAULT_DISTANCE = 250;
function clusterRadius(n, distance) {
  const k = Number(n) > 1 ? Number(n) : 1;
  const d = Number(distance) > 0 ? Number(distance) : DEFAULT_DISTANCE;
  // Spokes reach out, or the notes fill a disc.
  return Math.max(d, SPREAD * Math.sqrt(k / Math.PI)) + 40;
}

// Fixed places on a ring.
function ringLayout(folders, counts, rootCount, spacing, distance) {
  const order = [...folders].sort((a, b) => a.localeCompare(b));
  const at = new Map();
  const d = Number(distance) > 0 ? Number(distance) : DEFAULT_DISTANCE;
  const gap = d;
  if (!order.length) return { at, R: 0, gap };
  const r = (f) => clusterRadius(counts[f], d);
  const n = order.length;
  let R = clusterRadius(rootCount, d) + Math.max(...order.map(r)) + gap;
  if (n > 1) {
    const chord = 2 * Math.sin(Math.PI / n);
    for (let i = 0; i < n; i++) {
      const need = (r(order[i]) + r(order[(i + 1) % n]) + gap) / chord;
      if (need > R) R = need;
    }
  }
  R *= Number(spacing) > 0 ? Number(spacing) : 1;
  for (let i = 0; i < n; i++) {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    at.set(order[i], { x: R * Math.cos(angle), y: R * Math.sin(angle) });
  }
  return { at, R, gap };
}

// Color of the folder side.
function colorFor(source, target) {
  const node = topFolder(source.id) ? source : topFolder(target.id) ? target : null;
  return node && node.color ? node.color.rgb : null;
}

class GrapeClusters extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULTS, await this.loadData());
    this.hooks = [];
    this.byRenderer = new WeakMap();
    this.drawing = null;
    this.lastSummary = new WeakMap();
    this.warned = false;
    this.distance = DEFAULT_DISTANCE;
    this.readDistance();
    this.addSettingTab(new GrapeClustersSettingTab(this.app, this));
    this.addCommand({
      id: 'toggle',
      name: 'Toggle folder clusters',
      callback: () => this.setEnabled(!this.settings.enabled, { notify: true }),
    });
    this.app.workspace.onLayoutReady(() => this.scan());
    this.registerEvent(this.app.workspace.on('layout-change', () => this.scan()));
    this.registerEvent(this.app.workspace.on('active-leaf-change', () => this.scan()));
    // Pinned notes snap back.
    const tick = setInterval(() => {
      for (const hook of this.hooks) {
        try {
          if (!hook.ring && hook.pinned && hook.pinned.size) this.send(hook);
          this.pinRing(hook);
        } catch (e) {
          // Keep the graph alive.
        }
      }
    }, 500);
    if (tick && typeof tick.unref === 'function') tick.unref();
    this.tick = tick;
    if (typeof this.registerInterval === 'function') this.registerInterval(tick);
  }

  // What the graph settings say.
  async readDistance() {
    try {
      const raw = await this.app.vault.adapter.read(this.app.vault.configDir + '/graph.json');
      const d = Number(JSON.parse(raw).linkDistance);
      if (d > 0) this.distance = d;
    } catch (e) {
      // No graph settings yet.
    }
  }

  onunload() {
    if (this.tick) clearInterval(this.tick);
    this.tick = null;
    for (const hook of this.hooks) this.detach(hook);
    this.hooks = [];
    if (this.drawing) {
      this.drawing.proto.render = this.drawing.original;
      this.drawing = null;
    }
  }

  async setEnabled(on, { notify = false } = {}) {
    this.settings.enabled = on;
    if (!on) for (const hook of this.hooks) this.unpin(hook);
    await this.save();
    if (notify) new Notice(on ? 'Folder clusters on.' : 'Folder clusters off: the regular graph.');
  }

  async save() {
    await this.saveData(this.settings);
    for (const hook of this.hooks) this.send(hook);
  }

  // Save and redraw only.
  async saveQuiet() {
    await this.saveData(this.settings);
    for (const { renderer } of this.hooks) if (typeof renderer.changed === 'function') renderer.changed();
  }

  // Only the global graph.
  scan() {
    const alive = new Set();
    for (const leaf of this.app.workspace.getLeavesOfType('graph')) {
      const view = leaf.view;
      if (!view || !view.renderer) continue;
      alive.add(view.renderer);
      this.attach(view.renderer);
    }
    this.hooks = this.hooks.filter((h) => alive.has(h.renderer));
  }

  attach(renderer) {
    const known = this.hooks.find((h) => h.renderer === renderer);
    if (known && (known.worker === renderer.worker || !renderer.worker)) return;
    // Obsidian swapped the worker.
    if (known) this.hooks = this.hooks.filter((h) => h !== known);
    const worker = renderer.worker;
    const ok = worker && typeof worker.postMessage === 'function' && Array.isArray(renderer.links);
    if (!ok) {
      this.warnOnce();
      return;
    }
    const original = worker.postMessage;
    const hook = { renderer, worker, original, cross: null, soft: null, ring: null, pinned: new Set(), color: { rgb: 0, a: 0 } };
    const plugin = this;
    worker.postMessage = function (message, ...rest) {
      let result = null;
      const forces = message && message.forces;
      if (forces && Number(forces.linkDistance) > 0) {
        const d = Number(forces.linkDistance);
        if (d !== plugin.distance) {
          plugin.distance = d;
          for (const h of plugin.hooks) h.ring = null;
        }
      }
      if (plugin.settings.enabled && message && Array.isArray(message.links)) {
        result = plugin.filterFor(renderer, message.links);
        plugin.rememberCross(hook, message.links, result.links, result.soft);
        plugin.hookDrawing(renderer);
        try {
          hook.ring = plugin.ringFor(renderer, message.links, result);
        } catch (e) {
          hook.ring = null;
        }
        if (!hook.ring) plugin.unpin(hook);
        message = Object.assign({}, message, { links: result.links });
        plugin.summarize(renderer, result);
      }
      const out = original.call(worker, message, ...rest);
      if (result) {
        try {
          plugin.pinRing(hook);
        } catch (e) {
          // The ring never breaks clusters.
        }
      }
      return out;
    };
    this.hooks.push(hook);
    this.byRenderer.set(renderer, hook);
    if (renderer.links.length) this.send(hook);
  }

  // Resend links through the filter.
  send({ renderer, worker }) {
    const pairs = renderer.links.map((l) => [l.source.id, l.target.id]);
    worker.postMessage({ links: pairs, alpha: 1, run: true });
  }

  detach(hook) {
    this.unpin(hook);
    const { renderer, worker, original } = hook;
    if (worker.postMessage !== original) delete worker.postMessage;
    try {
      const pairs = renderer.links.map((l) => [l.source.id, l.target.id]);
      original.call(worker, { links: pairs, alpha: 1, run: true });
    } catch (e) {
      // The view is already closed.
    }
  }

  filterFor(renderer, pairs) {
    const types = new Map(renderer.nodes.map((n) => [n.id, n.type || '']));
    const typeOf = (id) => types.get(id) || '';
    return filterLinks(pairs, [...types.keys()], typeOf, this.settings.backbone, this.settings.depth, this.settings.spokes);
  }

  // Where every hub belongs.
  ringFor(renderer, pairs, result) {
    if (!this.settings.ring || !result.hubOf || !result.hubOf.size) return null;
    const depth = this.settings.depth;
    const key = (id) => (depth > 1 ? folderOf(id, depth) : topFolder(id));
    const followers = new Set();
    const counts = {};
    let rootCount = 0;
    for (const n of renderer.nodes) {
      if (!n || typeof n.id !== 'string') continue;
      if (FOLLOWERS.has(n.type || '')) {
        followers.add(n.id);
        continue;
      }
      const f = key(n.id);
      if (f) counts[f] = (counts[f] || 0) + 1;
      else rootCount++;
    }
    const layout = ringLayout([...result.hubOf.keys()], counts, rootCount, this.settings.spacing, this.distance);
    const ring = new Map();
    for (const [f, id] of result.hubOf) ring.set(id, layout.at.get(f));
    // Root note with most hubs.
    const hubs = new Set(result.hubs);
    const score = new Map();
    for (const pair of pairs) {
      if (!pair) continue;
      const [a, b] = pair;
      if (typeof a !== 'string' || typeof b !== 'string') continue;
      if (followers.has(a) || followers.has(b)) continue;
      if (!key(a) && hubs.has(b)) score.set(a, (score.get(a) || 0) + 1);
      if (!key(b) && hubs.has(a)) score.set(b, (score.get(b) || 0) + 1);
    }
    let center = null;
    for (const [id, n] of score) if (!center || n > score.get(center)) center = id;
    if (center) ring.set(center, { x: 0, y: 0 });
    return ring;
  }

  // Hold every hub in place.
  pinRing(hook) {
    const { renderer, worker, original } = hook;
    if (!hook.ring || !this.settings.enabled || !this.settings.ring) return;
    const drag = renderer.dragNode || null;
    for (const node of renderer.nodes) {
      const at = hook.ring.get(node.id);
      if (!at || node === drag) continue;
      if (node.fx === at.x && node.fy === at.y) continue;
      const msg = { forceNode: { id: node.id, x: at.x, y: at.y } };
      if (node.fx == null) Object.assign(msg, { alpha: 0.1, run: true });
      node.fx = at.x;
      node.fy = at.y;
      hook.pinned.add(node.id);
      original.call(worker, msg);
    }
  }

  // Let go of everything pinned.
  unpin(hook) {
    const { renderer, worker, original } = hook;
    if (!hook.pinned || !hook.pinned.size) return;
    const byId = new Map(renderer.nodes.map((n) => [n.id, n]));
    let first = true;
    for (const id of hook.pinned) {
      const node = byId.get(id);
      if (node) {
        node.fx = null;
        node.fy = null;
      }
      const msg = { forceNode: { id, x: null, y: null } };
      if (first) {
        Object.assign(msg, { alpha: 0.3, run: true });
        first = false;
      }
      try {
        original.call(worker, msg);
      } catch (e) {
        // The view is already closed.
      }
    }
    hook.pinned.clear();
    hook.ring = null;
  }

  // Links that are only drawn.
  rememberCross(hook, all, kept, soft = []) {
    const keeps = new Map();
    for (const [a, b] of kept) {
      if (!keeps.has(a)) keeps.set(a, new Set());
      keeps.get(a).add(b);
    }
    const cross = new Map();
    for (const [a, b] of all) {
      if (keeps.has(a) && keeps.get(a).has(b)) continue;
      if (!cross.has(a)) cross.set(a, new Set());
      cross.get(a).add(b);
    }
    hook.cross = cross;
    // Released inside a folder.
    const softMap = new Map();
    for (const [a, b] of soft) {
      if (!softMap.has(a)) softMap.set(a, new Set());
      softMap.get(a).add(b);
    }
    hook.soft = softMap;
  }

  // Soft links, colored clusters.
  hookDrawing(renderer) {
    if (this.drawing || !renderer.links.length) return;
    const proto = Object.getPrototypeOf(renderer.links[0]);
    if (!proto || proto === Object.prototype || typeof proto.render !== 'function') return;
    const original = proto.render;
    const plugin = this;
    proto.render = function () {
      const r = this.renderer;
      const hook = r && plugin.byRenderer.get(r);
      if (!hook || !hook.cross || !plugin.settings.enabled || !r.colors || !r.colors.line) return original.call(this);
      const focus = typeof r.getHighlightNode === 'function' ? r.getHighlightNode() : null;
      if (focus && (this.source === focus || this.target === focus)) return original.call(this);
      const line = r.colors.line;
      const own = hook.color;
      const cross = hook.cross.get(this.source.id);
      if (cross && cross.has(this.target.id)) {
        const soft = hook.soft && hook.soft.get(this.source.id);
        const rgb = soft && soft.has(this.target.id) && plugin.settings.colorInside ? colorFor(this.source, this.target) : null;
        own.rgb = rgb === null ? line.rgb : rgb;
        own.a = line.a * plugin.settings.cables;
      } else {
        const rgb = plugin.settings.colorInside ? colorFor(this.source, this.target) : null;
        own.rgb = rgb === null ? line.rgb : rgb;
        own.a = line.a * plugin.settings.inside;
      }
      r.colors.line = own;
      try {
        return original.call(this);
      } finally {
        r.colors.line = line;
      }
    };
    this.drawing = { proto, original };
  }

  summarize(renderer, result) {
    if (!this.settings.summary) return;
    const hubs = result.hubOf ? result.hubOf.size : 0;
    const text = `Grape Clusters: ${result.folders.length} folders, ${hubs} with a main note, ${result.kept} links pull, ${result.drawnOnly} only drawn.`;
    if (this.lastSummary.get(renderer) === text) return;
    this.lastSummary.set(renderer, text);
    new Notice(text, 5000);
  }

  warnOnce() {
    if (this.warned) return;
    this.warned = true;
    new Notice('Grape Clusters does not recognize this version of the graph view, so it changes nothing.', 8000);
  }
}

class GrapeClustersSettingTab extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  slider(containerEl, key, name, desc) {
    new Setting(containerEl)
      .setName(name)
      .setDesc(desc)
      .addSlider((s) =>
        s
          .setLimits(0, 100, 5)
          .setValue(Math.round(this.plugin.settings[key] * 100))
          .setDynamicTooltip()
          .onChange(async (v) => {
            this.plugin.settings[key] = v / 100;
            await this.plugin.saveQuiet();
          })
      );
  }

  toggle(containerEl, key, name, desc, relayout) {
    new Setting(containerEl)
      .setName(name)
      .setDesc(desc)
      .addToggle((t) =>
        t.setValue(this.plugin.settings[key]).onChange(async (v) => {
          this.plugin.settings[key] = v;
          await (relayout ? this.plugin.save() : this.plugin.saveQuiet());
        })
      );
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    this.toggle(containerEl, 'enabled', 'Cluster by folder',
      'Your folders become clusters in the graph. Every link is a pull between two notes; this decides which ones are allowed to pull, and the rest stay on screen but let go. Keep Center force in the graph settings at 0.15 or higher, or the clusters drift apart when you drag a note.', true);
    new Setting(containerEl)
      .setName('Folder depth')
      .setDesc('1 makes a cluster of every top-level folder, 2 gives every subfolder its own, and 3 goes one deeper.')
      .addSlider((s) =>
        s
          .setLimits(1, 3, 1)
          .setValue(this.plugin.settings.depth)
          .setDynamicTooltip()
          .onChange(async (v) => {
            this.plugin.settings.depth = v;
            await this.plugin.save();
          })
      );
    this.toggle(containerEl, 'backbone', 'Backbone',
      'A note outside a folder, in the root of your vault or higher up, keeps pulling on the main note of that folder, so the clusters stay together instead of drifting apart. A main note is one that is linked with at least half of its folder.', true);
    this.toggle(containerEl, 'spokes', 'Spokes',
      'Inside a folder, only the links to a main note pull. The other links in that folder stay visible but let go, so the folder settles into a wheel: the main note in the middle, its notes around it like spokes. A folder can have more than one main note, and a folder without one keeps all its links.', true);
    new Setting(containerEl)
      .setName('Ring')
      .setDesc('The note in the root of your vault that links to the most main notes goes in the middle, and every folder that has a main note gets a fixed place on a ring around it. Each folder keeps its own spot; drag one away and it snaps back. A folder without a main note gets no spot, and without a root note the middle stays empty. Tidy, but it is the one setting that places notes for you instead of letting the pulls decide, and most vaults look better the other way. That is why it is off to begin with.')
      .addToggle((t) =>
        t.setValue(this.plugin.settings.ring).onChange(async (v) => {
          this.plugin.settings.ring = v;
          if (!v) for (const hook of this.plugin.hooks) this.plugin.unpin(hook);
          await this.plugin.save();
        })
      );
    new Setting(containerEl)
      .setName('Ring spacing')
      .setDesc('How much room the folders get on the ring. The ring already follows Link distance in the graph settings; this widens or narrows it further.')
      .addSlider((s) =>
        s
          .setLimits(50, 200, 10)
          .setValue(Math.round(this.plugin.settings.spacing * 100))
          .setDynamicTooltip()
          .onChange(async (v) => {
            this.plugin.settings.spacing = v / 100;
            await this.plugin.save();
          })
      );
    this.slider(containerEl, 'cables', 'Links between clusters',
      'How visible the links are that let go: between two folders, and with Spokes on the ones inside a folder too. 0 hides them, 100 draws them as usual. Hover a note to see all of its links.');
    this.slider(containerEl, 'inside', 'Links inside a cluster',
      'How visible the links are that still pull: to a main note, and the backbone links. Lower is calmer.');
    this.toggle(containerEl, 'colorInside', 'Color links by folder',
      'Links inside a folder take the color of that folder, from the groups in the graph settings.', false);
    this.toggle(containerEl, 'summary', 'Show a summary',
      'Show a short notice whenever the counts change: how many folders there are, how many have a main note, and how many links pull.', false);
  }
}

module.exports = GrapeClusters;
module.exports.filterLinks = filterLinks;
module.exports.topFolder = topFolder;
module.exports.folderOf = folderOf;
module.exports.above = above;
module.exports.colorFor = colorFor;
module.exports.ringLayout = ringLayout;
module.exports.clusterRadius = clusterRadius;
