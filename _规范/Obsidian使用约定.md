---
分类:
  - 规范
  - Obsidian
状态: 现行
最后更新: 2026-11-14
适用范围: 本仓库作为 Obsidian vault 打开时的显示、链接与配置约定
---

# Obsidian 使用约定

本仓库同时是设定库与 Obsidian vault。用 Obsidian 打开**仓库根目录**即可，不要另建子目录当 vault。

## 目录主文件仍是 README.md

各级目录的主文件一律叫 `README.md`，**文件名不改**。GitHub 上照旧按 README 显示，git 历史与链接也不动。

Obsidian 里靠插件把它显示成「文件夹的笔记」：

| 步骤 | 位置 | 设置 |
|------|------|------|
| 1 | Folder Notes → General → Folder note name | 填 `README` |
| 2 | Folder Notes → General → Storage location | 选「文件夹内」（Inside the folder） |
| 3 | Folder Notes → File explorer → Hide folder note | 开启 |
| 4 | Waypoint → Folder Note Style | 选 `Custom Filename`，填 `README` |

设好后在侧栏看到的是文件夹本身，点文件夹名直接打开该目录的 `README.md`；`README.md` 不再单独占一行。Obsidian 记录的仍是 `README.md`，GitHub 与命令行也照旧。

- 子区已有自己的 `README.md` 时，链接一律指向它，不要只链父级。
- 目录里的其他笔记照常显示在文件夹下，不需要别的处理。

## 不要用点开头的目录

Obsidian 不索引 `.xxx/`，里面的笔记点不开、图片不显示。需要收纳就起正常名字，如 `image/`、`草稿/`。

## 链接

- 正文一律写 Markdown 相对链接 `[文字](相对路径.md)`，不写 `[[双链]]`，这样 GitHub 上也能点开。
- `.obsidian/app.json` 已固定：`useMarkdownLinks` 开启、`newLinkFormat` 为 `relative`、`alwaysUpdateLinks` 开启。改名或移动文件时 Obsidian 会同步改链接。
- **例外**：Waypoint 生成的目录区块用双链，这是插件产物，手写正文不跟着用双链。

## 属性

元数据写在文首的 YAML 属性块里，正文不写页脚：

```markdown
---
分类:
  - 参与者
  - 势力
状态: 存续（环带内战参战方）
---
```

- `分类`、`时代`、`故事线` 写成列表，便于 `全库索引.base` 与属性检索按值筛选。
- `状态` 写字符串，说明文档或实体现在的状态。
- 字段含义见 [文档维护与版本策略](文档维护与版本策略.md)。

## Git

- `.obsidian/` 除机器本地状态外都入库，换机器后配置一致。
- 不入库：`workspace.json`、`workspace-mobile.json`、`cache/`、`.trash/`。见根目录 `.gitignore`。
- 换行由 `.gitattributes` 统一为 LF。不要在 Windows 侧改动 `core.autocrlf`，否则整库会显示「已修改」。
- 提交信息与改动范围见 [文档维护与版本策略](文档维护与版本策略.md)。

## 插件

| 插件 | 社区插件 id | 用途 | 设置要点 |
|------|-------------|------|----------|
| Folder Notes | `folder-notes` | 点文件夹名打开该目录的 `README.md` | 名称填 `README`；存放位置「文件夹内」；开启「Hide folder note」 |
| Waypoint | `waypoint` | 在 `README.md` 里生成子笔记目录，随增删改名自动更新 | Folder Note Style 选 `Custom Filename` 并填 `README`；正文写一行 `%% Waypoint %%` 处生成目录 |
| Obsidian Git | `obsidian-git` | 在 Obsidian 内提交与拉取 | 保留手动确认，不要开启自动提交 |
| Graph Folder Labels | `graph-folder-labels` | 让 `README.md` 在关系图谱里显示成所在文件夹的名字 | 文件夹笔记名填 `README`；重名规则选 `duplicates`；层数 3 |

## 关系图谱里的目录名

图谱节点默认显示文件名，所以 85 个目录笔记全都显示成「README」。Graph Folder Labels 只换显示文字，不改磁盘文件名，所以 GitHub 与命令行里仍是 `README.md`。

它改写的是图谱节点的 `getDisplayText`，并同步改写已经在屏幕上的文字对象。节点 id 不动，因此分簇、连线、拖动都不受影响。

设置存在 `.obsidian/plugins/graph-folder-labels/data.json`：

| 项 | 值 | 说明 |
|----|-----|------|
| `enabled` | `true` | 总开关 |
| `folderNotes` | `README` | 哪些文件名算目录笔记，可用逗号分隔多个 |
| `parentPrefix` | `duplicates` | 只在显示名撞车时才加父目录；另有 `off` 与 `all` |
| `parentDepth` | `3` | 逐级加前缀的上限；加满仍重名时用完整父级路径兜底 |

命名规则：文件夹名在全库唯一时直接用；重名时逐级补上父目录，直到能区分。所以击魄那棵明线／暗线镜像结构会显示成 `击魄/01-明线`、`01-明线/03-参与者/势力` 这样的两级或三级名。

结果：85 个目录笔记得到 85 个互不相同的名字，188 个普通笔记的名字一个字不变。新增目录不用改配置，插件按当前目录树重算。

**不要**点 Folder Notes 的「Rename existing folder notes」：它会把 `README.md` 改成与文件夹同名，与本库约定相反。

插件设置存在 `.obsidian/plugins/<插件 id>/data.json`，随仓库同步。

## Waypoint 怎么用

1. 在本级 `README.md` 里选好位置，写一行 `%% Waypoint %%`。
2. 插件在该行处生成目录，列出本目录及子目录的笔记；子目录已有自己的 Waypoint 时，父级只链到子目录的 `README.md`，不重复展开。
3. 生成出来的区块不要手改，插件会在文件增删改名时重写。
4. 目录内容是双链，GitHub 上显示为纯文字；需要 GitHub 可读的索引，继续手写表格。

## 关系图谱配色

图谱节点的颜色按**文件夹**分，配置在 `.obsidian/graph.json` 的 `colorGroups`。颜色组是纯配置，不改任何笔记，也不装插件。

### 顺序即优先级

Obsidian 判断节点颜色时，从 `colorGroups` 第一条开始匹配，**首个命中即取色并停止**：

```javascript
for (let p of e) {
  let f = p.query.match(c, d);
  if (f && p.color) { u = p.color; break }
}
```

所以列表必须从最具体排到最宽泛。例如 `分支时间线/法厄同/云上坟场` 排在同名上层目录之前，否则子集会被父级提前着色。

### 现行色板

| 匹配路径 | 颜色 | 含义 |
|----------|------|------|
| `草稿` | `#8A8A8A` 灰 | 全库草稿，含各集的 `草稿/` |
| `00-总览` | `#D9A441` 金 | 总览与待办入口 |
| `_templates` | `#7E8F7E` 暗灰绿 | 模板 |
| `_规范` | `#6E8C93` 暗青 | 仓库规范与工具 |
| `docs` | `#6E6E6E` 淡灰 | 智能体文档 |
| `原文` | `#9A7B5A` 深棕 | 原始文本 |
| `绘图` | `#C46A9B` 品红 | 设定向绘图 |
| `分支时间线/法厄同/云上坟场` | `#9B6BB5` 紫 | 云上坟场一支 |
| `分支时间线/法厄同/击魄` | `#C25B7C` 玫红 | 击魄一支 |
| `分支时间线/泰拉` | `#5E9E6B` 绿 | 泰拉一支 |
| `分支时间线` | `#8A7CB8` 淡紫 | 其余分支（卢娜、马尔斯、麦哲伦号） |
| `词条/地点` | `#3FA796` 青绿 | 地点词条 |
| `词条/参与者` | `#C05B4D` 赭红 | 参与者词条 |
| `词条/事件` | `#DB8A3B` 橙 | 事件词条 |
| `词条/概念` | `#6C7BC4` 蓝紫 | 概念词条 |
| `词条/时间` | `#7A8CA6` 灰蓝 | 时间词条 |
| `词条` | `#8FA6A0` 淡青 | 其余词条 |

根目录五个入口（`README.md`、`GLOSSARY.md`、`AGENTS.md`、`总世界线.md`、`实体与关系网.md`）不设颜色，保持默认。

### 改色

`graph.json` 里的 `rgb` 是整数，等于 `R×65536 + G×256 + B`。改一处时同步改本表，两处不要各写各的。

`分类` 字段**不参与**配色，它在单个笔记里是多值标签（一条分支可能同时挂「暗线」「参与者」「事件」），不适合当颜色轴。新增顶层目录时，在 `colorGroups` 末尾补一条即可，不会影响已有分组。
