# 本地 Cursor 规则（WorldCreate）

| 目录 | 纳入本仓库 Git | 说明 |
|------|----------------|------|
| `.cursor/rules/common/` | **否** | junction → `cursor-workflow-rules/packages/` |
| `.cursor/rules/local/` | **是** | 仅本项目的补充规则 |

## 通用规则（junction，勿在本仓库改）

在 [cursor-workflow-rules](D:\OneDrive\MyProjects\cursor-workflow-rules) 编辑 `packages/` 后 `git push` 即可，**无需** Pull 脚本。

本项目选配见 rules 仓库 `profiles/worldcreate.md`（`common` + `lore`）。junction 指向整个 `packages/`，下列与设定库直接相关：

| 包 / 规则 | 作用 |
|-----------|------|
| `common/zh-cn-response-style` | 简体中文交流与推理 |
| `common/no-coined-terms` | 禁止自造词、写作禁用词 |
| `lore/lore-docs-zh-prose` | 设定 / 时间线中文书面语（通用） |
| `lore/lore-location-readme` | 地点类文件夹 + README 结构（通用） |
| `lore/dialogue-secrecy` | 对话知情分层 |

## 本地规则（仅写本项目专有内容）

**不要**在 local 重复通用库已有全文；只放索引、定型术语、区位树等 WorldCreate 专有部分。

| 文件 | 作用 |
|------|------|
| `worldcreate-lore-terms.mdc` | 定型术语（链接、执火派/执火者、地面线专名等）与索引入口 |
| `worldcreate-location-tree.mdc` | 地球地面「众城所在地」目标目录树与范例 |

## 联接失效时

在 rules 仓库运行：

```powershell
.\scripts\Install-JunctionToProject.ps1 -TargetRoot "D:\OneDrive\MyProjects\WorldCreate" -Packages common,lore -InitGitignore
```

## 新增本地规则

- 文件名建议 `worldcreate-*.mdc`，避免与 `packages/lore/*.mdc` 同名。
- 在 frontmatter 用 `globs` 收窄到本项目路径；正文开头链到对应的 `../common/...` 通用规则。
