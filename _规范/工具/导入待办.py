import sys, io, os, re, json, subprocess, urllib.parse, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = 'Estrella6066773/WorldCreate'
BASE = f'https://github.com/{REPO}/blob/master/'
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

LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]*)\)')


def parse_file(rel):
    text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith('|'):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) != 8:
            continue
        if cells[0] in ('项',) or set(cells[0]) <= set('-: '):
            continue
        item, src_cell, added, impact, urgency, who, state, detail = cells
        links = [(t, u) for t, u in LINK_RE.findall(src_cell)]
        hint = ''
        if not links:
            m = re.match(r'^`(.+)`$', src_cell)
            hint = m.group(1) if m else src_cell
        rows.append({
            'file': rel,
            'item': item.replace('**', '').strip(),
            'links': links,
            'hint': hint,
            'added': added,
            'impact': impact,
            'urgency': urgency,
            'who': who,
            'state': state,
            'detail': detail,
        })
    return rows


def abs_link(target, from_file):
    """把待办文件里的相对路径换算成仓库内绝对路径，再转成 GitHub 链接。"""
    p = os.path.normpath(os.path.join(os.path.dirname(from_file), urllib.parse.unquote(target)))
    rel = os.path.relpath(p, ROOT).replace('\\', '/')
    return rel, BASE + urllib.parse.quote(rel)


def build_body(row):
    src = []
    for text, target in row['links']:
        rel, url = abs_link(target, row['file'])
        src.append(f'- [{text}]({url})  ·  `{rel}`')
    if row['hint']:
        src.append(f'- 原汇总表记为：{row["hint"]}')
    src.append(f'- 原登记于 `{row["file"]}`，添加时间 {row["added"]}')

    detail = row['detail']
    if detail in ('—', '-', ''):
        detail = '尚未展开。本项来自既有登记，缺什么、依赖什么还没写清；动工时补齐。'

    body = [
        '## 来源', '', *src, '',
        '## 详情', '', detail, '',
        '## 验收', '',
        '- 改动涉及的文件说法一致，不出现两套定义',
        f'- 专名与 [GLOSSARY.md]({BASE}GLOSSARY.md) 一致，不新增未决议词',
        '- 相关词条与总览的链接可点开，必要时同步 `待定项汇总` 的导航',
    ]
    return '\n'.join(body) + '\n'


def gh(args):
    r = subprocess.run(['gh'] + args, cwd=ROOT, capture_output=True,
                       encoding='utf-8', errors='replace', timeout=120)
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()


def main():
    dry = '--dry-run' in sys.argv
    rows = []
    for rel in FILES:
        rows.extend(parse_file(rel))

    print('解析条目数', len(rows))
    for rel in FILES:
        n = sum(1 for r in rows if r['file'] == rel)
        print(f'  {n:3d}  {rel}')

    bad = [r for r in rows if r['impact'] not in ('核心', '重要', '补充')
           or r['urgency'] not in ('高', '中', '低')
           or r['who'] not in ('作者', '编辑', '智能体', '待核实')]
    if bad:
        print('\n!! 标签取值异常', len(bad))
        for r in bad[:10]:
            print('  ', r['impact'], r['urgency'], r['who'], r['item'][:30])
        return

    if dry:
        sample = rows[0]
        print('\n--- 样例标题 ---\n' + sample['item'])
        print('\n--- 样例正文 ---\n' + build_body(sample))
        return

    registry = {'repo': REPO, 'items': []}
    if os.path.exists(REGISTRY):
        registry = json.load(open(REGISTRY, encoding='utf-8'))
    done = {(i['file'], i['item']) for i in registry['items']}

    created = 0
    for row in rows:
        key = (row['file'], row['item'])
        if key in done:
            continue
        labels = [row['impact'], row['urgency'], row['who']]
        args = ['issue', 'create', '-R', REPO,
                '--title', row['item'],
                '--body', build_body(row)]
        for l in labels:
            args += ['--label', l]
        code, out, err = gh(args)
        if code != 0:
            print('!! 失败', row['item'][:40], err[:200])
            continue
        num = int(re.search(r'/issues/(\d+)', out).group(1))
        registry['items'].append({**row, 'number': num, 'url': out})
        created += 1
        if created % 10 == 0:
            print('已创建', created, flush=True)
            json.dump(registry, open(REGISTRY, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
        time.sleep(0.4)

    json.dump(registry, open(REGISTRY, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('本轮创建', created, '登记总计', len(registry['items']))


if __name__ == '__main__':
    main()
