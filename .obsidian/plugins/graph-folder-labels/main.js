'use strict';

/*
Graph Folder Labels
在关系图谱与局部图谱里改写节点的显示文字。

图谱节点在 initGraphics() 里用 new PIXI.Text(this.getDisplayText()) 建一次文字对象，
之后任何重绘都不会重建它。所以要两条路一起走：
  1. 改写节点原型上的 getDisplayText，管住之后新建的节点与图形重建；
  2. 直接改已有节点文字对象上的 text，管住眼下已经在屏幕上的节点。
只换显示文字，不改 node.id，所以分簇、链接、拖动都不受影响。
*/

const { Plugin, PluginSettingTab, Setting, Notice } = require('obsidian');

const VIEW_TYPES = ['graph', 'localgraph'];
// 原型上记录「已改写」，值为被替换掉的原始方法。
const PATCHED = Symbol('graphFolderLabelsPatched');

const DEFAULTS = {
	enabled: true,
	// 哪些文件名算「文件夹笔记」，用逗号分隔。
	folderNotes: 'README',
	// off：从不加前缀；duplicates：显示名重复时才加；all：一律加。
	parentPrefix: 'duplicates',
	// 逐级加前缀的最大层数。加到这里仍重复，就直接用完整父级路径。
	parentDepth: 3,
};

function isNotePath(path) {
	return typeof path === 'string' && /\.md$/i.test(path);
}

// 把路径拆成父级目录段与不带扩展名的文件名。
function splitPath(path) {
	const parts = String(path).split('/');
	const file = parts.pop() || '';
	return { parts, name: file.replace(/\.md$/i, '') };
}

function folderNoteNames(settings) {
	return String(settings.folderNotes || '')
		.split(',')
		.map((s) => s.trim().toLowerCase())
		.filter(Boolean);
}

// 一个节点的显示名，以及加前缀时可供取用的父级目录段。
// 文件夹笔记把所在文件夹当作自己的名字，父级段则从再往上一级算起。
function anchorOf(path, settings) {
	if (!isNotePath(path)) return null;
	const { parts, name } = splitPath(path);
	const isFolderNote = folderNoteNames(settings).includes(name.toLowerCase());

	if (isFolderNote && parts.length) {
		return { label: parts[parts.length - 1], context: parts.slice(0, -1) };
	}
	return { label: name, context: parts };
}

// 取父级末 k 段拼在显示名前面。k 超过实际层级就退化为整条父级路径。
function withPrefix(anchor, k) {
	if (!anchor.context.length) return anchor.label;
	const take = Math.min(Math.max(1, k), anchor.context.length);
	return `${anchor.context.slice(-take).join('/')}/${anchor.label}`;
}

/*
为整批路径算出显示名。
paths 是库里所有 Markdown 文件的路径。settings.parentPrefix 决定是否加前缀：
  off        一律用基础名
  all        一律按 parentDepth 加前缀
  duplicates 只在显示名重复时逐级加长，直到不再重复
返回 Map<路径, 显示名>。
*/
function buildLabels(paths, settings) {
	const mode = settings.parentPrefix || 'duplicates';
	const maxDepth = Math.max(1, Math.floor(Number(settings.parentDepth) || 1));
	const out = new Map();

	const anchors = new Map();
	for (const p of paths) {
		const a = anchorOf(p, settings);
		if (!a) continue;
		anchors.set(p, a);
		out.set(p, a.label);
	}

	if (mode === 'off') return out;

	if (mode === 'all') {
		for (const [p, a] of anchors) out.set(p, withPrefix(a, maxDepth));
		return out;
	}

	// 逐级加长：每一轮只抬升仍然重名的节点，直到全部唯一或已加满层数。
	for (let depth = 0; depth < maxDepth; depth++) {
		const counts = new Map();
		for (const label of out.values()) counts.set(label, (counts.get(label) || 0) + 1);
		if ([...counts.values()].every((n) => n <= 1)) break;

		let changed = false;
		for (const [p, a] of anchors) {
			if (counts.get(out.get(p)) <= 1) continue;
			const next = withPrefix(a, depth + 1);
			if (next !== out.get(p)) {
				out.set(p, next);
				changed = true;
			}
		}
		if (!changed) break;
	}

	// 加满层数仍重名，用完整父级路径兜底，保证图谱上没有两个同名标签。
	const counts = new Map();
	for (const label of out.values()) counts.set(label, (counts.get(label) || 0) + 1);
	for (const [p, a] of anchors) {
		if (counts.get(out.get(p)) <= 1) continue;
		out.set(p, withPrefix(a, a.context.length || 1));
	}

	return out;
}

function firstNode(nodes) {
	if (!nodes) return null;
	if (typeof nodes.first === 'function') return nodes.first();
	return nodes.length ? nodes[0] : null;
}

// 节点文字对象在渲染后才存在；有的版本是 PIXI.Text，有的是普通对象。
function setNodeText(node, label) {
	const holder = node && node.text;
	if (!holder) return false;
	try {
		if (holder.text !== label) holder.text = label;
		return true;
	} catch (e) {
		return false;
	}
}

class GraphFolderLabels extends Plugin {
	async onload() {
		this.settings = Object.assign({}, DEFAULTS, await this.loadData());
		this.warned = false;
		this.labels = new Map();
		this.timer = null;
		// 标签版本号：每次重算自增，用来判断某个画布是否需要重建图形。
		this.version = 0;
		this.applied = new WeakMap();

		this.addSettingTab(new GraphFolderLabelsSettingTab(this.app, this));

		// 图谱每 1 秒复核一次：视图重开、worker 重建都不发事件，扫描代价很小。
		this.app.workspace.onLayoutReady(() => this.tick());
		this.registerEvent(this.app.workspace.on('layout-change', () => this.tick()));
		this.registerEvent(this.app.workspace.on('active-leaf-change', () => this.tick()));

		const schedule = () => this.schedule();
		this.registerEvent(this.app.vault.on('create', schedule));
		this.registerEvent(this.app.vault.on('delete', schedule));
		this.registerEvent(this.app.vault.on('rename', schedule));

		this.registerInterval(window.setInterval(() => this.tick(), 1000));

		this.addCommand({
			id: 'refresh-graph-labels',
			name: '重新计算图谱节点标签',
			callback: () => {
				this.rebuild();
				this.tick(true);
				new Notice('图谱节点标签已刷新。');
			},
		});

		this.addCommand({
			id: 'diagnose-graph-labels',
			name: '诊断图谱标签状态',
			callback: () => this.diagnose(),
		});

		this.rebuild();
	}

	onunload() {
		if (this.timer) window.clearTimeout(this.timer);
		for (const view of this.views()) this.restore(view.renderer);
	}

	views() {
		const list = [];
		for (const type of VIEW_TYPES) {
			let leaves = [];
			try {
				leaves = this.app.workspace.getLeavesOfType(type);
			} catch (e) {
				leaves = [];
			}
			for (const leaf of leaves) {
				if (leaf && leaf.view && leaf.view.renderer) list.push(leaf.view);
			}
		}
		return list;
	}

	schedule() {
		if (this.timer) window.clearTimeout(this.timer);
		this.timer = window.setTimeout(() => {
			this.rebuild();
			this.tick(true);
		}, 400);
	}

	// 按当前设置重算整库的显示名。结果没变就不动版本号，免得每秒重建图形。
	rebuild() {
		let files = [];
		try {
			files = this.app.vault.getMarkdownFiles().map((f) => f.path);
		} catch (e) {
			files = [];
		}
		const next = buildLabels(files, this.settings);
		if (next.size === this.labels.size) {
			let same = true;
			for (const [k, v] of next) {
				if (this.labels.get(k) !== v) {
					same = false;
					break;
				}
			}
			if (same) return;
		}
		this.labels = next;
		this.version++;
	}

	tick(force = false) {
		for (const view of this.views()) {
			if (this.settings.enabled) this.apply(view.renderer, force);
			else this.restore(view.renderer);
		}
	}

	// 给一个画布套上/刷新标签。
	apply(renderer, force = false) {
		if (!renderer) return;
		if (!this.patch(renderer)) return;

		// 标签没变就不碰画布，避免每秒都重建图形。
		const done = this.applied.get(renderer);
		if (!force && done === this.version) {
			// 视图重开后图形是新的，但原型已改写，文字本身已经是对的。
			return;
		}

		this.paint(renderer);
		this.rebuildGraphics(renderer);
		this.applied.set(renderer, this.version);
	}

	// 改写节点原型上的 getDisplayText。同一原型只改一次。
	patch(renderer) {
		const node = firstNode(renderer.nodes);
		if (!node) return false;

		const proto = Object.getPrototypeOf(node);
		if (!proto || typeof proto.getDisplayText !== 'function') {
			this.warnOnce('图谱节点的显示接口与预期不同，本插件未生效。');
			return false;
		}
		if (proto[PATCHED]) return true;

		const original = proto.getDisplayText;
		const plugin = this;
		proto.getDisplayText = function () {
			const label = plugin.labels.get(this.id);
			if (label !== undefined) return label;
			return original.apply(this, arguments);
		};
		proto[PATCHED] = original;
		return true;
	}

	// 把显示名写进已有节点的文字对象。文字对象还没建的节点，等它建时会读改写后的方法。
	paint(renderer, force = false) {
		const nodes = renderer.nodes || [];
		let touched = false;
		for (const node of nodes) {
			if (!node || typeof node.id !== 'string') continue;
			const label = this.labels.get(node.id);
			if (label === undefined) continue;
			const holder = node.text;
			if (!holder) continue;
			if (!force && holder.text === label) continue;
			if (setNodeText(node, label)) touched = true;
		}
		if (touched) this.redraw(renderer);
		return touched;
	}

	// 关掉插件时恢复原文。
	restore(renderer) {
		if (!renderer) return;
		const node = firstNode(renderer.nodes);
		const proto = node && Object.getPrototypeOf(node);
		if (proto && proto[PATCHED]) {
			const original = proto[PATCHED];
			proto.getDisplayText = original;
			delete proto[PATCHED];
		}
		for (const n of renderer.nodes || []) {
			if (!n || !n.text || typeof n.getDisplayText !== 'function') continue;
			setNodeText(n, n.getDisplayText());
		}
		this.applied.delete(renderer);
		this.rebuildGraphics(renderer);
	}

	// 让画布按新文字重绘。changed 在个别版本上可能缺，缺失就跳过。
	redraw(renderer) {
		try {
			if (typeof renderer.changed === 'function') renderer.changed();
		} catch (e) {
			// 视图正在关闭时重绘失败无所谓。
		}
	}

	/*
	重建画布上的文字对象。
	图谱节点在 initGraphics() 里用 new PIXI.Text(this.getDisplayText()) 建文字，只建一次；
	原型改写只对之后新建的节点生效，已经在屏幕上的那些必须重建。
	Obsidian 1.15 里这个入口是 renderer.onIframeLoad()，它会销毁并重新初始化图形。
	*/
	rebuildGraphics(renderer) {
		try {
			if (typeof renderer.onIframeLoad === 'function') {
				renderer.onIframeLoad();
				return true;
			}
		} catch (e) {
			// 个别版本或画布模式下没有 iframe，退回只改文字。
		}
		this.redraw(renderer);
		return false;
	}

	async save() {
		await this.saveData(this.settings);
		this.rebuild();
		this.tick(true);
	}

	warnOnce(text) {
		if (this.warned) return;
		this.warned = true;
		new Notice(text, 8000);
	}

	/*
	排查用：把当前看到的视图、节点与标签打出来。
	图谱没变化时先跑这一条，就知道是没找到视图、原型没改写，还是文字对象没刷新。
	*/
	diagnose() {
		const views = this.views();
		const lines = [
			`设置：enabled=${this.settings.enabled} 模式=${this.settings.parentPrefix} 层数=${this.settings.parentDepth}`,
			`标签 ${this.labels.size} 条，版本 ${this.version}`,
			`图谱视图 ${views.length} 个`,
		];
		views.forEach((view, i) => {
			const nodes = view.renderer.nodes || [];
			const first = firstNode(nodes);
			const proto = first && Object.getPrototypeOf(first);
			const patched = !!(proto && proto[PATCHED]);
			const sample = [];
			for (const n of nodes) {
				if (sample.length >= 3) break;
				if (!n || typeof n.id !== 'string') continue;
				sample.push(`${n.id} -> ${n.text ? n.text.text : '(无文字对象)'}`);
			}
			lines.push(`#${i + 1} 节点 ${nodes.length}，原型已改写 ${patched ? '是' : '否'}`);
			lines.push(...sample.map((s) => `   ${s}`));
			lines.push(`   有 onIframeLoad：${typeof view.renderer.onIframeLoad === 'function' ? '是' : '否'}`);
		});
		const text = lines.join('\n');
		console.log('[graph-folder-labels]\n' + text);
		new Notice(text, 15000);
	}
}

class GraphFolderLabelsSettingTab extends PluginSettingTab {
	constructor(app, plugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display() {
		const { containerEl } = this;
		containerEl.empty();

		new Setting(containerEl)
			.setName('启用')
			.setDesc('改写关系图谱与局部图谱里的节点文字。')
			.addToggle((t) =>
				t.setValue(this.plugin.settings.enabled).onChange(async (v) => {
					this.plugin.settings.enabled = v;
					await this.plugin.save();
				})
			);

		new Setting(containerEl)
			.setName('文件夹笔记的文件名')
			.setDesc('这些文件在图谱里显示为所在文件夹的名字。多个用逗号分隔。')
			.addText((t) =>
				t
					.setPlaceholder('README')
					.setValue(this.plugin.settings.folderNotes)
					.onChange(async (v) => {
						this.plugin.settings.folderNotes = v;
						await this.plugin.save();
					})
			);

		new Setting(containerEl)
			.setName('父级前缀')
			.setDesc('决定什么时候显示成「父级文件夹/文件名」。选「仅重名时」，只有显示名撞车的节点才加前缀，其余保持短名。')
			.addDropdown((d) =>
				d
					.addOption('duplicates', '仅重名时')
					.addOption('all', '全部加')
					.addOption('off', '不加')
					.setValue(this.plugin.settings.parentPrefix || 'duplicates')
					.onChange(async (v) => {
						this.plugin.settings.parentPrefix = v;
						await this.plugin.save();
					})
			);

		new Setting(containerEl)
			.setName('父级层数上限')
			.setDesc('重名时逐级加长，最多加到这里。仍重名就直接用完整父级路径。选「全部加」时也按这一层数加。')
			.addSlider((s) =>
				s
					.setLimits(1, 5, 1)
					.setValue(Number(this.plugin.settings.parentDepth) || 3)
					.setDynamicTooltip()
					.onChange(async (v) => {
						this.plugin.settings.parentDepth = v;
						await this.plugin.save();
					})
			);
	}
}

module.exports = GraphFolderLabels;
// 供验收脚本直接测纯函数与画布写入逻辑，不影响 Obsidian 加载。
module.exports.anchorOf = anchorOf;
module.exports.withPrefix = withPrefix;
module.exports.buildLabels = buildLabels;
module.exports.splitPath = splitPath;
module.exports.setNodeText = setNodeText;
