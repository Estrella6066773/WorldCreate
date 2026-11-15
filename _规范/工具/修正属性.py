"""修正属性块的四类错位：类型判错、模板未归类、别名字段名、裸标签。

只改文首属性块，不动正文。用法：
    python _规范/工具/修正属性.py            # 只报告
    python _规范/工具/修正属性.py --apply    # 写入
"""
import sys, io, os, re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 世界里成文的规则不是仓库规范，改判分支正文
RETYPE = {
    '分支时间线/法厄同/云上坟场/02-暗线/03-人类身份界定/云上人与人工智能.md',
    '分支时间线/法厄同/云上坟场/02-暗线/03-人类身份界定/云邦官方授权.md',
    '分支时间线/法厄同/云上坟场/02-暗线/03-人类身份界定/人工智能认知与记忆.md',
    '分支时间线/法厄同/云上坟场/02-暗线/03-人类身份界定/人格化人工智能禁令.md',
    '分支时间线/法厄同/云上坟场/02-暗线/03-人类身份界定/思维上传的合法标准.md',
}

# 描述文档性质、不属于世界内状态的说明
DROP_NOTE = ('核心规则', '硬约束')

# 补 aliases：只收指同一个东西的简称、全称、英文名、仍在用的旧称
ALIASES = {
    '词条/地点/泰拉/README.md': ['泰拉', '地球'],
    '词条/地点/法厄同/README.md': ['法厄同', '法厄同环', '法厄同带', '法厄同之环', '环带'],
    '词条/地点/马尔斯/README.md': ['马尔斯', '火星'],
    '词条/地点/云城.md': ['云城', 'Cloud City'],
    '词条/地点/以太界/以太.md': ['以太', '源质'],
    '词条/参与者/势力/云邦.md': ['云邦', '云城邦联', 'Orbis', 'CCC'],
    '词条/参与者/势力/马尔斯航天.md': ['马尔斯航天', '战神航天'],
    '词条/参与者/族群/云上人.md': ['云上人', 'Cloudtype'],
}


def split_blocks(meta):
    blocks, cur = [], None
    for line in meta:
        m = re.match(r'^([^\s#\-][^:]*):', line)
        if m:
            cur = (m.group(1).strip(), [line])
            blocks.append(cur)
        elif cur and (re.match(r'^\s+-\s', line) or not line.strip()):
            cur[1].append(line)
    return blocks


def render(key, values):
    return ['%s:' % key] + ['  - %s' % v for v in values]


# 单值字段写成 `键: 值`，不写成列表。列表会让 Obsidian 把它当多值属性，筛选与排序都会失准。
SCALAR = {'类型', '文档状态', '状态', '最后更新', '英文工程名', '范围'}


def render_scalar(key, values):
    return ['%s: %s' % (key, values[0])] if values else ['%s:' % key]


def load(path):
    text = open(path, encoding='utf-8').read()
    nl = '\r\n' if '\r\n' in text else '\n'
    m = re.match(r'^---\r?\n([\s\S]*?)\r?\n---', text)
    if not m:
        return None
    return text, nl, text[:m.start(1)], m.group(1).split(nl), text[m.end(1):]


def save(path, nl, head, blocks, tail):
    body = [l for b in blocks for l in b[1]]
    while body and not body[-1].strip():
        body.pop()
    open(path, 'w', encoding='utf-8', newline='').write(head + nl.join(body) + tail)


def main():
    do_apply = '--apply' in sys.argv
    log = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {'.git', '.obsidian', '.idea', '.cursor'}]
        for name in filenames:
            if not name.endswith('.md'):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace('\\', '/')
            got = load(path)
            if not got:
                continue
            text, nl, head, meta, tail = got
            blocks = split_blocks(meta)
            keys = [b[0] for b in blocks]
            notes = []
            changed = False

            def setv(key, values, pos=None):
                nonlocal changed
                lines = render_scalar(key, values) if key in SCALAR else render(key, values)
                if key in keys:
                    i = keys.index(key)
                    if blocks[i][1] == lines:
                        return
                    blocks[i] = (key, lines)
                else:
                    if pos is None:
                        pos = len(blocks)
                    blocks.insert(pos, (key, lines))
                    keys.insert(pos, key)
                changed = True

            def drop(key):
                nonlocal changed
                if key in keys:
                    i = keys.index(key)
                    del blocks[i]
                    keys.pop(i)
                    changed = True

            # 1) 模板归位：类型写 模板，去掉 文档状态
            if rel.startswith('_templates/'):
                setv('类型', ['模板'], 0)
                drop('文档状态')
                drop('故事线')
                notes.append('类型→模板')

            # 2) 世界内规则改判分支正文
            if rel in RETYPE:
                setv('类型', ['分支正文'], keys.index('类型') if '类型' in keys else 0)
                notes.append('类型→分支正文')
                if '状态说明' in keys:
                    i = keys.index('状态说明')
                    vals = [l.strip()[2:].strip() for l in blocks[i][1][1:] if l.strip().startswith('- ')]
                    if vals and all(v in DROP_NOTE for v in vals):
                        drop('状态说明')
                        notes.append('删 状态说明（文档性质）')

            # 3) 别名：写 Obsidian 认的 aliases
            if rel in ALIASES:
                setv('aliases', ALIASES[rel], 0)
                notes.append('aliases')

            # 4) 裸标签
            if 'tags' in keys:
                i = keys.index('tags')
                vals = [l.strip()[2:].strip() for l in blocks[i][1][1:] if l.strip().startswith('- ')]
                keep = [v for v in vals if re.match(r'^(主题|核实|来源)/', v)]
                bad = [v for v in vals if v not in keep]
                if bad:
                    if keep:
                        setv('tags', keep, i)
                    else:
                        drop('tags')
                    notes.append('删裸标签 ' + '、'.join(bad))

            if changed:
                log.append((rel, '；'.join(notes)))
                if do_apply:
                    save(path, nl, head, blocks, tail)

    for rel, notes in log:
        print('%-64s %s' % (rel, notes))
    print('\n合计 %d 处%s' % (len(log), '' if do_apply else '（未写入，加 --apply 才写）'))


if __name__ == '__main__':
    main()
