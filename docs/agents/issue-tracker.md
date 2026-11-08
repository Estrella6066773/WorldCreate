# Issue tracker：GitHub

本仓库的 issues 与 spec 存放在 GitHub Issues 中，地址 `Estrella6066773/WorldCreate`。所有操作使用 `gh` CLI。

## 约定

- **新建 issue**：`gh issue create --title "..." --body "..."`。多行 body 用 heredoc。
- **读取 issue**：`gh issue view <number> --json number,title,body,labels,comments`。
- **列出 issue**：`gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`，按需加 `--label` 与 `--state` 过滤。
- **设为子 issue**：`gh issue create --parent <parent> ...`，或事后 `gh issue edit <parent> --add-sub-issue <child>`（`gh` 2.94 及以上）。旧版本用 `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`。用不了 sub-issue 时，在 child body 顶部写 `Part of #<parent>`。
- **阻塞关系**：用 GitHub 原生 issue 依赖，这是界面上看得见的正规表达。`gh issue create --blocked-by <n>,<n> ...` 或 `gh issue edit <child> --add-blocked-by <blocker>`（`gh` 2.94 及以上）。旧版本用 `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`，其中 `<blocker-db-id>` 是 blocker 的数字 database id（`gh api repos/<owner>/<repo>/issues/<n> --jq .id`），不是 `#number`，也不是 `node_id`。依赖接口不可用时，回退到 child body 顶部的 `Blocked by: #<n>, #<n>` 行。所有阻塞项都关闭时，这条 ticket 即为 unblocked。
- **统计未关闭的阻塞项**：`gh api repos/<owner>/<repo>/issues/<n> --jq .issue_dependencies_summary.blocked_by`，只统计仍开着的阻塞项，0 表示可以开工。`gh issue view <n> --json blockedBy` 会连已关闭的一起列出，需要过滤：`--jq '[.blockedBy.nodes[] | select(.state == "OPEN")] | length'`。
- **评论**：`gh issue comment <number> --body "..."`。
- **加标签／去标签**：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`。
- **关闭**：先用 `gh issue comment <number> --body "..."` 发说明，再 `gh issue close <number>`。对已经关闭的 issue，`gh issue close --comment` 会丢掉这条评论，而且仍然以退出码 0 结束，所以不要依赖它。

仓库从 `git remote -v` 推断；在 clone 里运行 `gh` 会自动处理。

只往你自己名下的仓库提 issue。绝不向 `mattpocock/skills`（这些 skill 的来源仓库）提 issue，除非你拥有它。fork 里 `gh` 可能默认指向上游 parent，所以本次会话第一次 `gh issue create` 之前，先用 `gh repo view --json nameWithOwner` 核对目标；目标不对就先问用户。

## 外部 pull request 是否进入分诊队列

本仓库不把外部 pull request 当作功能请求来源。分诊 skill `/triage` 只处理 issue，不处理 pull request。

## skill 说「发布到 issue tracker」时

新建一个 GitHub issue。

## skill 说「取出对应的 ticket」时

按上方「读取 issue」的方式读取。

## Wayfinding 操作

供 `/wayfinder` 使用。**map** 是一个 issue，**child** issues 是它的 tickets。

- **Map**：单个带 `wayfinder:map` 标签的 issue，正文保存 Notes / Decisions-so-far / Fog。`gh issue create --label wayfinder:map`。
- **Child ticket**：通过 GitHub sub-issue 挂到 map 下面（见上文「设为子 issue」）。未启用 sub-issue 时，把 child 加进 map body 的 task list，并在 child body 顶部写 `Part of #<map>`。标签 `wayfinder:<type>`，`<type>` 取 `research`、`prototype`、`grilling`、`task` 之一。被 claim 之后 assign 给执行的人。
- **阻塞**：见「约定」里的「阻塞关系」。
- **Frontier 查询**：列出 map 的 open children（`gh issue list --state open`，限定在 map 的 sub-issues 或 task list 内），丢掉任何还有未关闭阻塞项的、以及已经有 assignee 的；按 map 里的顺序取第一个。
- **Claim**：`gh issue edit <n> --add-assignee @me`，作为本次会话的第一次写入。
- **Resolve**：`gh issue comment <n> --body "<答案>"`，再 `gh issue close <n>`，然后向 map 的 Decisions-so-far 追加一条指针（要点加链接）。
