"""把 `分类` 字段迁移到 `类型`、`时代`、`tags`，其余取值交给路径。

规则见 `_规范/属性与标签规范.md`「迁移：`分类` 的去处」。
默认只报告，不改文件；加 `--apply` 才写入。

用法：
    python _规范/工具/迁移分类.py
    python _规范/工具/迁移分类.py --apply
"""
import sys, io, os, re, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_DIRS = {'.git', '.obsidian', '.idea', '.cursor'}

# 分类取值 -> 类型取值。路径推不出时，这里优先。
TO_TYPE = {
    '词条': '词条',
    '正文': '分支正文',
    '分支时间线': '分支正文',
    '时间线': '分支正文',
    '主题': '分支正文',
    '索引': '索引',
    '总览': '索引',
    '导读': '索引',
    '待办': '索引',
    '待定项': '索引',
    '知情对照': '索引',
    '明暗对照': '索引',
    '仓库入口': '索引',
    '规范': '规范',
    '规则': '规范',
    '仓库级': '规范',
    '创作方针': '规范',
    'Obsidian': '规范',
    '模板': '模板',
    '草稿': '草稿',
    '讨论稿': '草稿',
    '提案': '草稿',
    '设定设计': '草稿',
    '概念设计': '草稿',
    '定名方案': '草稿',
    '待定建议': '草稿',
    '原文': '原文',
    '绘图': '绘图',
}

# 路径 -> 类型。分类推不出类型时按这个兜底，按前缀从长到短匹配。
BY_PATH = [
    ('分支时间线/', '分支正文'),
    ('词条/', '词条'),
    ('草稿/', '草稿'),
    ('原文/', '原文'),
    ('绘图/', '绘图'),
    ('_templates/', '模板'),
    ('_规范/', '规范'),
    ('docs/', '规范'),
]

# 分类取值 -> 标签
TO_TAG = {
    '伊勒信仰': '主题/伊勒信仰',
    '节点城信仰': '主题/伊勒信仰',
    '路西法': '主题/路西法',
    '灵界称谓': '主题/路西法',
    '执火叙事': '主题/执火叙事',
    '云端公民': '主题/云上人身份',
    '人类分支': '主题/云上人身份',
    '存在形式': '主题/云上人身份',
    '穿越机衍生体': '主题/穿越机',
    '以太适应性微械材料': '主题/穿越机',
}

TO_ERA = {'灾变时代': '灾变时代'}
ART_PREFIX = '美术风格'


def split_front(text):
    m = re.match(r'^---\r?\n([\s\S]*?)\r?\n---\r?\n?', text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def read_fields(front):
    """把属性块读成 {键: [值]}，值保持原文（含引号），只去掉首尾空白。"""
    fields, order, key = {}, [], None
    for line in front.splitlines():
        mm = re.match(r'^([^\s#][^:]*):\s*(.*)$', line)
        if mm:
            key = mm.group(1).strip()
            if key not in fields:
                fields[key] = []
                order.append(key)
            value = mm.group(2).strip()
            if value:
                fields[key].append(value)
            continue
        if key and line.strip().startswith('- '):
            fields[key].append(line.strip()[2:].strip())
    return fields, order


def unquote(value):
    return value.strip().strip('"').strip("'")


def type_by_path(rel):
    # 各集自带的 草稿/ 与 归档/ 也算草稿
    if '/草稿/' in rel or '/归档/' in rel or rel.startswith('草稿/'):
        return '草稿'
    # 地点词条以 README 为主文件，它不是索引，是条目本体
    if rel.startswith('词条/地点/') and os.path.basename(rel) == 'README.md':
        return '词条'
    if os.path.basename(rel) == 'README.md':
        return '索引'
    for prefix, value in BY_PATH:
        if rel.startswith(prefix):
            return value
    return None


def new_type(rel, class_values):
    # 目录 README 一律是索引；地点词条的 README 例外，它是条目本体
    by_path = type_by_path(rel)
    if by_path in ('词条', '索引', '模板'):
        return by_path
    for value in class_values:
        if value in TO_TYPE:
            return TO_TYPE[value]
        if value.startswith(ART_PREFIX):
            return '分支正文'
    return by_path


def render(fields, order):
    """按固定顺序输出：类型、文档状态、状态、时代、tags、其余原顺序。"""
    head = ['类型', '文档状态', '状态', '时代', 'tags']
    out = []
    for key in head:
        values = fields.get(key)
        if not values:
            continue
        if len(values) == 1 and key != 'tags':
            out.append('%s: %s' % (key, values[0]))
        else:
            out.append('%s:' % key)
            out.extend('  - ' + v for v in values)
    for key in order:
        if key in head or key == '分类':
            continue
        values = fields.get(key, [])
        if len(values) == 1:
            out.append('%s: %s' % (key, values[0]))
        elif values:
            out.append('%s:' % key)
            out.extend('  - ' + v for v in values)
    return '\n'.join(out)


def plan(rel, raw):
    """返回 (新文本, 类型, 转换出的标签列表, 未映射取值列表)。"""
    front, body = split_front(raw)
    if front is None:
        return None, None, [], []
    fields, order = read_fields(front)
    class_values = [unquote(v) for v in fields.get('分类', [])]
    if not class_values:
        return None, None, [], []

    value_type = new_type(rel, class_values)
    eras = list(fields.get('时代', []))
    tags = list(fields.get('tags', []))
    used_tags, left = [], []
    for value in class_values:
        if value in TO_TAG:
            tag = TO_TAG[value]
            if tag not in tags:
                tags.append(tag)
                used_tags.append(value)
        elif value in TO_ERA and TO_ERA[value] not in eras:
            eras.append(TO_ERA[value])
        elif value in TO_TYPE or value.startswith(ART_PREFIX):
            pass
        else:
            left.append(value)

    if value_type:
        fields['类型'] = [value_type]
    else:
        fields.pop('类型', None)
    if eras:
        fields['时代'] = eras
    else:
        fields.pop('时代', None)
    if tags:
        fields['tags'] = tags
    else:
        fields.pop('tags', None)
    fields.pop('分类', None)

    return '---\n' + render(fields, order) + '\n---\n' + body.lstrip('\r'), value_type, used_tags, left


def fill_type(apply):
    """给没有 `类型` 的文档补上，按路径判定。只加 `类型` 一行，不碰其他内容。"""
    added = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if not name.endswith('.md'):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace('\\', '/')
            raw = open(path, encoding='utf-8', errors='ignore').read()
            front, body = split_front(raw)
            if front is not None:
                if re.search(r'^类型:\s*\S', front, re.M):
                    continue
                value = type_by_path(rel)
                if not value:
                    continue
                new_text = '---\n类型: ' + value + '\n' + front + '\n---\n' + body.lstrip('\r')
            else:
                value = type_by_path(rel)
                if not value:
                    continue
                new_text = '---\n类型: ' + value + '\n---\n\n' + raw.lstrip('\r')
            added.append((rel, value))
            if apply:
                open(path, 'w', encoding='utf-8', newline='\n').write(new_text)
    print('%s %d 篇：补 `类型`' % ('已写入' if apply else '试运行：将补', len(added)))
    for rel, value in added:
        print('   %-12s %s' % (value, rel))
    if not apply:
        print('\n确认后加 --fill-type --apply 写入。')


def main():
    if '--fill-type' in sys.argv:
        fill_type('--apply' in sys.argv)
        return
    if '--show' in sys.argv:
        for rel in sys.argv[sys.argv.index('--show') + 1:]:
            raw = open(os.path.join(ROOT, rel), encoding='utf-8').read()
            text, _, _, _ = plan(rel.replace('\\', '/'), raw)
            print('=== ' + rel)
            if text is None:
                print('（无属性块或无 `分类`，跳过）\n')
                continue
            print('--- 迁移前')
            print(raw.split('---')[1].strip())
            print('--- 迁移后')
            print(text.split('---')[1].strip())
            print()
        return

    apply = '--apply' in sys.argv
    changed, unmapped, taged, no_type = 0, collections.Counter(), collections.Counter(), []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if not name.endswith('.md'):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace('\\', '/')
            raw = open(path, encoding='utf-8', errors='ignore').read()
            new_text, value_type, used_tags, left = plan(rel, raw)
            if new_text is None:
                continue
            for value in used_tags:
                taged[value] += 1
            for value in left:
                unmapped[value] += 1
            if not value_type:
                no_type.append(rel)
            if new_text != raw:
                changed += 1
                if apply:
                    open(path, 'w', encoding='utf-8', newline='\n').write(new_text)

    print(('已写入' if apply else '试运行：将改写') + ' %d 篇' % changed)
    print('\n=== 转为标签的取值 ===')
    for value, count in taged.most_common():
        print('   %3d  %-18s -> %s' % (count, value, TO_TAG[value]))
    print('\n=== 丢弃的取值（路径已表达，或未映射）===')
    for value, count in unmapped.most_common():
        print('   %3d  %s' % (count, value))
    print('\n=== 迁移后仍无 `类型` 的文档 ===')
    for rel in no_type:
        print('   ' + rel)
    if not apply:
        print('\n以上为试运行结果，未改动任何文件。确认后加 --apply 写入。')


if __name__ == '__main__':
    main()
