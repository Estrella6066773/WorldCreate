"""检查文首属性块：受控取值、缺失字段、故事线矛盾、污染标签、路径冲突。

取值词表从 `_规范/属性与标签规范.md` 末尾的 YAML 区块读取，本脚本不另存一份。
只报告，不改文件。用法：python _规范/工具/查属性.py
"""
import sys, io, os, re, collections

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, '_规范', '属性与标签规范.md')
SKIP_DIRS = {'.git', '.obsidian', '.idea', '.cursor'}

FIELDS = ('类型', '文档状态', '故事线', '状态', '时代')
CITABLE = ('词条', '分支正文', '规范', '索引')

# `故事线` 与路径矛盾的判据：地点词条允许出现的主线，按路径从具体到宽泛排列。
REGION_LINES = [
    ('词条/地点/泰拉/轨道/', {'源质实体的起源', '环带前史', '通用'}),
    ('词条/地点/泰拉/地面/世界树/', {'自远方祖树而来的精灵们', '通用'}),
    ('词条/地点/泰拉/地面/诸城所在之地/', {'城市与城邦', '自远方祖树而来的精灵们', '源质实体的起源', '通用'}),
    ('词条/地点/泰拉/地面/深渊/', {'城市与城邦', '通用'}),
    ('词条/地点/泰拉/', {'源质实体的起源', '城市与城邦', '自远方祖树而来的精灵们', '通用'}),
    ('词条/地点/法厄同/', {'环带前史', '云上坟场', '击魄', '通用'}),
    ('词条/地点/马尔斯/', {'开拓马尔斯', '击魄', '通用'}),
    ('词条/地点/以太界/', {'通用'}),
]


def load_vocab():
    """从规范文档末尾的 yaml 区块读出受控取值。"""
    text = open(SPEC, encoding='utf-8').read()
    block = re.search(r'```yaml\n(类型[\s\S]*?)```', text)
    if not block:
        raise SystemExit('在 ' + SPEC + ' 里找不到受控取值区块')
    vocab = {}
    for line in block.group(1).splitlines():
        m = re.match(r'^(\S+?):\s*\[(.*)\]\s*$', line)
        if not m:
            continue
        values = [v.strip() for v in m.group(2).split(',') if v.strip()]
        vocab[m.group(1)] = values
    return vocab


def collect():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith('.md'):
                files.append(os.path.join(dirpath, name))
    return sorted(files)


def parse_front(path):
    """返回 (键 -> [值], 是否有属性块)。"""
    text = open(path, encoding='utf-8', errors='ignore').read()
    m = re.match(r'^---\r?\n([\s\S]*?)\r?\n---', text)
    if not m:
        return {}, False
    data, key = {}, None
    for line in m.group(1).splitlines():
        item = re.match(r'^([^\s#][^:]*):\s*(.*)$', line)
        if item:
            key = item.group(1).strip()
            rest = item.group(2).strip().strip('"').strip("'")
            data[key] = [rest] if rest else []
            continue
        if key and line.strip().startswith('- '):
            data[key].append(line.strip()[2:].strip().strip('"').strip("'"))
    return data, True


def allowed_lines(rel):
    """返回该路径允许的 `故事线` 取值；返回 None 表示不做约束。"""
    if rel in ('词条/地点/README.md', '词条/地点/云城.md'):
        return {'通用'}
    for prefix, allowed in REGION_LINES:
        if rel.startswith(prefix):
            return allowed
    return None


def main():
    vocab = load_vocab()
    errors = collections.defaultdict(list)
    legacy_cls, no_type, no_front, no_docstate = [], [], [], []
    stray_story, bad_story, bad_tags = [], [], []

    for path in collect():
        rel = os.path.relpath(path, ROOT).replace('\\', '/')
        data, has_front = parse_front(path)
        if not has_front:
            no_front.append(rel)
            continue
        if '分类' in data:
            legacy_cls.append((rel, data['分类']))
        if not data.get('类型'):
            no_type.append(rel)
        kind = (data.get('类型') or [''])[0]
        if kind in CITABLE and not data.get('文档状态'):
            no_docstate.append(rel)
        if data.get('故事线') and kind != '词条':
            stray_story.append((rel, kind))
        allowed = allowed_lines(rel)
        if allowed is not None:
            for value in data.get('故事线', []):
                if value and value not in allowed:
                    bad_story.append((rel, value))
        for value in data.get('tags', []):
            if not value:
                continue
            if not re.match(r'^(主题|核实|来源)/', value):
                bad_tags.append((rel, value, '裸标签或组名不在三组内'))
                continue
            group, _, leaf = value.partition('/')
            if group == '主题' and leaf not in vocab.get('主题', []):
                bad_tags.append((rel, value, '主题不在词表内'))
        for field in FIELDS:
            for value in data.get(field, []):
                if not value or value in vocab.get(field, []):
                    continue
                if re.fullmatch(r'\{.*\}', value):  # 模板占位符，不是取值
                    continue
                errors[field].append((rel, value))

    print('=== 受控取值之外的值 ===')
    for field in FIELDS:
        rows = errors.get(field, [])
        print('\n[%s] %d 处' % (field, len(rows)))
        for rel, value in rows:
            print('   %-52s  %s' % (rel, value))

    print('\n=== 仍写着 `分类` 的文档 ===')
    print('共 %d 篇' % len(legacy_cls))
    counter = collections.Counter()
    for _, values in legacy_cls:
        for v in values:
            counter[v] += 1
    for value, count in counter.most_common(20):
        print('   %3d  %s' % (count, value))

    print('\n=== 缺少 `类型` 的文档 ===')
    print('共 %d 篇' % len(no_type))
    for rel in no_type:
        print('   ' + rel)

    print('\n=== 可引用但缺少 `文档状态` 的文档 ===')
    print('共 %d 篇' % len(no_docstate))
    for rel in no_docstate:
        print('   ' + rel)

    print('\n=== 没有属性块的文档（共 %d 篇）===' % len(no_front))
    for rel in no_front:
        print('   ' + rel)

    print('\n=== `故事线` 与路径矛盾 ===')
    print('共 %d 处' % len(bad_story))
    for rel, value in bad_story:
        print('   %-58s  %s' % (rel, value))

    print('\n=== 非词条写了 `故事线` ===')
    print('共 %d 处' % len(stray_story))
    for rel, kind in stray_story:
        print('   %-58s  类型=%s' % (rel, kind))

    print('\n=== 裸标签或不在三组内的标签 ===')
    print('共 %d 处' % len(bad_tags))
    for rel, value, why in bad_tags:
        print('   %-52s  %-14s %s' % (rel, value, why))

    print('\n=== 同名文件落在不同目录（人工判断是否子类冲突）===')
    by_name = collections.defaultdict(list)
    for path in collect():
        rel = os.path.relpath(path, ROOT)
        name = os.path.splitext(os.path.basename(rel))[0]
        if name == 'README':
            continue
        by_name[name].append(rel)
    for name, rels in sorted(by_name.items()):
        if len(rels) < 2:
            continue
        parents = {os.path.basename(os.path.dirname(r)) for r in rels}
        if len(parents) < 2:
            continue
        # 明线与暗线是同一件事的两层，父目录不同属正常
        if parents <= {'01-明线', '02-暗线', '明线', '暗线'}:
            continue
        print('   %s  (%d 份)' % (name, len(rels)))
        for r in rels:
            print('      ' + r)

    print('\n合计：受控取值越界 %d 处 ｜ 故事线矛盾 %d 处 ｜ 故事线越界 %d 处 ｜ 裸标签 %d 处 ｜ 残留分类 %d 篇 ｜ 缺类型 %d 篇 ｜ 缺文档状态 %d 篇 ｜ 无属性块 %d 篇'
          % (sum(len(v) for v in errors.values()), len(bad_story), len(stray_story), len(bad_tags),
             len(legacy_cls), len(no_type), len(no_docstate), len(no_front)))


if __name__ == '__main__':
    main()
