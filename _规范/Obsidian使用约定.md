---
分类:
  - 规范
  - Obsidian
状态: 现行
最后更新: 2026-11-13
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

**不要**点 Folder Notes 的「Rename existing folder notes」：它会把 `README.md` 改成与文件夹同名，与本库约定相反。

插件设置存在 `.obsidian/plugins/<插件 id>/data.json`，随仓库同步。

## Waypoint 怎么用

1. 在本级 `README.md` 里选好位置，写一行 `%% Waypoint %%`。
2. 插件在该行处生成目录，列出本目录及子目录的笔记；子目录已有自己的 Waypoint 时，父级只链到子目录的 `README.md`，不重复展开。
3. 生成出来的区块不要手改，插件会在文件增删改名时重写。
4. 目录内容是双链，GitHub 上显示为纯文字；需要 GitHub 可读的索引，继续手写表格。
