# WorldCreate

击魄／法厄同的独立设定库。术语与写法定本见 `GLOSSARY.md`；本仓库只放设定真相，不写游戏项目的程序设计文档。

## Agent skills

### Issue tracker

issues 与 spec 存放在本仓库的 GitHub Issues（`Estrella6066773/WorldCreate`），用 `gh` CLI 读写。见 `docs/agents/issue-tracker.md`。

### Work labels

issue 标签分三组，全部用中文：影响面 `核心`/`重要`/`补充`、急迫度 `急`/`高`/`中`/`低`、负责 `作者`/`编辑`/`智能体`/`待核实`。见 `docs/agents/labels.md`。

### Pending items

未办结的设定事项登记为 GitHub issue（`Estrella6066773/WorldCreate`），每条三组标签各打一个。各集 `待办/*.md` 是从 issue 生成的表，**不要手工编辑**；改完 issue 跑 `python _规范/工具/同步索引.py` 重建。看全貌用本地表，检索用 `gh issue list --search`。见 `_规范/待办/README.md`。

### Domain docs

single-context：根目录 `GLOSSARY.md` 是词汇正本，决策记录放 `docs/adr/`。见 `docs/agents/domain.md`。
