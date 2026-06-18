# 本地 Cursor 规则

| 目录 | 项目 Git | 说明 |
|------|----------|------|
| `.cursor/rules/common/` | **否** | junction → `cursor-workflow-rules/packages/` |
| `.cursor/rules/local/` | **是** | 仅本项目 |

通用规则在 rules 仓库 `packages/` 维护；改完 `git push` 即可，**无需 Pull 脚本**。

联接失效时在 rules 仓库运行：

```powershell
.\scripts\Install-JunctionToProject.ps1 -TargetRoot "D:\OneDrive\MyProjects\WorldCreate" -Packages common,lore
```
