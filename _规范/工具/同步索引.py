import sys, io, os, re, json, subprocess, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = 'Estrella6066773/WorldCreate'
REGISTRY = os.path.join(ROOT, '_规范', '待办', 'issues.json')

FILES = [
    '_规范/待办/时间.md',
    '_规范/待办/地点.md',
    '_规范/待办/参与者.md',
    '_规范/待办/事件.md',
    '_规范/待办/概念.md',
    '_规范/待办/跨区.md',
    '分支时间线/法厄同/击魄/00-总览/待办/明线.md',
    '分支时间线/法厄同/击魄/00-总览/待办/暗线.md',
    '分支时间线/法厄同/云上坟场/00-总览/待办/明线.md',
    '分支时间线/法厄同/云上坟场/00-总览/待办/暗线.md',
    '分支时间线/法厄同/云上坟场/00-总览/待办/美术.md',
]

TITLES = {
    '_规范/待办/时间.md': ('待办 · 时间', '母设定「时间」轴的未办结项。'),
    '_规范/待办/地点.md': ('待办 · 地点', '母设定「地点」轴的未办结项。'),
    '_规范/待办/参与者.md': ('待办 · 参与者', '母设定「参与者」轴的未办结项。'),
    '_规范/待办/事件.md': ('待办 · 事件', '母设定「事件」轴的未办结项。'),
    '_规范/待办/概念.md': ('待办 · 概念', '母设定「概念」轴的未办结项。'),
    '_规范/待办/跨区.md': ('待办 · 跨区', '跨区与时代层面的未办结项。'),
    '分支时间线/法厄同/击魄/00-总览/待办/明线.md': ('待办 · 击魄 · 明线', '击魄明线（玩家可见）的未办结项。'),
    '分支时间线/法厄同/击魄/00-总览/待办/暗线.md': ('待办 · 击魄 · 暗线', '击魄暗线（设定真相）的未办结项。'),
    '分支时间线/法厄同/云上坟场/00-总览/待办/明线.md': ('待办 · 云上坟场 · 明线', '云上坟场明线（玩家可见）的未办结项。'),
    '分支时间线/法厄同/云上坟场/00-总览/待办/暗线.md': ('待办 · 云上坟场 · 暗线', '云上坟场暗线（设定真相）的未办结项。'),
    '分支时间线/法厄同/云上坟场/00-总览/待办/美术.md': ('待办 · 云上坟场 · 美术', '云上坟场美术风格的未办结项。'),
}

IMPACT_ORDER = {'核心': 0, '重要': 1, '补充': 2}


def gh(args):
    r = subprocess.run(['gh'] + args, cwd=ROOT, capture_output=True,
                       encoding='utf-8', errors='replace', timeout=180)
    if r.returncode != 0:
        raise SystemExit('gh 调用失败: ' + (r.stderr or '')[:300])
    return r.stdout


def rel_link(target, from_file, out_file):
    p = os.path.normpath(os.path.join(os.path.dirname(from_file), urllib.parse.unquote(target)))
    base = os.path.dirname(os.path.join(ROOT, out_file))
    return os.path.relpath(p, base).replace('\\', '/')


def main():
    registry = json.load(open(REGISTRY, encoding='utf-8'))
    data = json.loads(gh(['issue', 'list', '-R', REPO, '--state', 'open',
                          '--limit', '500', '--json', 'number,title,state,url']))
    alive = {i['number']: i for i in data}

    by_file = {}
    for item in registry['items']:
        if item['number'] in alive:
            by_file.setdefault(item['file'], []).append(item)

    total = 0
    for rel in FILES:
        rows = by_file.get(rel, [])
        rows.sort(key=lambda r: (IMPACT_ORDER.get(r['impact'], 9), r['added'], r['item']))
        total += len(rows)
        title, lead = TITLES[rel]
        out = ['# ' + title, '',
               '| 字段 | 内容 |', '|------|------|',
               '| 状态 | 本表由 `_规范/工具/同步索引.py` 从 GitHub issue 生成，不要手工编辑 |',
               '| 最后更新 | 见文件提交时间 |',
               '| 口径 | [' + ('待办口径' if rel.startswith('_规范') else '待办口径') + ']('
               + ('README.md' if rel.startswith('_规范')
                  else '../../../../../_规范/待办/README.md') + ') |',
               '', lead, '',
               '| issue | 项 | 来源 | 添加时间 | 影响面 | 急迫度 | 负责 |',
               '|-------|----|------|----------|--------|--------|------|']
        for r in rows:
            srcs = []
            for text, target in r['links']:
                srcs.append('[' + text + '](' + rel_link(target, r['file'], rel) + ')')
            if not srcs and r['hint']:
                srcs.append('`' + r['hint'] + '`')
            cells = [
                '[#' + str(r['number']) + '](' + r['url'] + ')',
                r['item'],
                '<br>'.join(srcs) if srcs else '—',
                r['added'], r['impact'], r['urgency'], r['who'],
            ]
            out.append('| ' + ' | '.join(cells) + ' |')
        out += ['', '---', '',
                '**分类：** 待办 | ' + ('母设定' if rel.startswith('_规范')
                                       else ('击魄' if '/击魄/' in rel else '云上坟场'))]
        p = os.path.join(ROOT, rel)
        open(p, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
        print(f'{len(rows):3d}  {rel}')

    print('生成合计', total, '｜ 登记', len(registry['items']), '｜ 未关闭', len(alive))


if __name__ == '__main__':
    main()
