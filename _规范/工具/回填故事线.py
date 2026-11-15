"""回填 `故事线` 属性：去掉链接写法、按受控词表写纯名、补齐缺的。

取值来源有两条：
  1. 分支正文里链到这一篇的线（客观引用关系）；
  2. 地点子区按所属主线继承；事件与概念按两端所属的线写。

只改文首属性块，不动正文。用法：
    python _规范/工具/回填故事线.py            # 只报告
    python _规范/工具/回填故事线.py --apply    # 写入
"""
import sys, io, os, re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 分支目录 -> 主线名。顺序从具体到宽泛，先命中先用。
LINE_RULES = [
    ('分支时间线/泰拉/轨道/', '源质实体的起源'),
    ('分支时间线/泰拉/地面/诸城所在之地/', '城市与城邦'),
    ('分支时间线/泰拉/地面/世界树/', '自远方祖树而来的精灵们'),
    ('分支时间线/卢娜/', '月人的起源'),
    ('分支时间线/马尔斯/', '开拓马尔斯'),
    ('分支时间线/法厄同/云上坟场/', '云上坟场'),
    ('分支时间线/法厄同/击魄/', '击魄'),
    ('分支时间线/麦哲伦号/', '循光之城'),
    ('分支时间线/法厄同/', '环带前史'),
]

# 由分支正文的实际引用推导出的归属。改动引用后重跑可以复核。
DERIVED = {
    '词条/事件/权限/马尔斯航天理事会封存修剪智库.md': ['开拓马尔斯', '环带前史'],
    '词条/参与者/人工智能.md': ['击魄'],
    '词条/参与者/人物/昏昼.md': ['城市与城邦'],
    '词条/参与者/人物/晨昏星.md': ['城市与城邦'],
    '词条/参与者/势力/云邦.md': ['云上坟场', '击魄', '环带前史'],
    '词条/参与者/势力/智库.md': ['开拓马尔斯'],
    '词条/参与者/势力/海潮派.md': ['城市与城邦'],
    '词条/参与者/势力/牧群派.md': ['城市与城邦'],
    '词条/参与者/势力/矿业联盟.md': ['击魄', '环带前史'],
    '词条/参与者/势力/马尔斯航天.md': ['开拓马尔斯'],
    '词条/参与者/族群/云上人.md': ['云上坟场', '击魄'],
    '词条/参与者/族群/精灵.md': ['自远方祖树而来的精灵们'],
    '词条/参与者/机魂.md': ['击魄'],
    '词条/参与者/污染/异魔.md': ['云上坟场', '击魄', '开拓马尔斯', '环带前史'],
    '词条/参与者/污染/穿越机.md': ['开拓马尔斯'],
    '词条/地点/法厄同/README.md': ['云上坟场', '击魄', '环带前史'],
    '词条/地点/泰拉/地面/README.md': ['城市与城邦'],
    '词条/地点/泰拉/地面/世界树/README.md': ['自远方祖树而来的精灵们'],
    '词条/地点/泰拉/地面/深渊/README.md': ['城市与城邦'],
    '词条/地点/泰拉/地面/诸城所在之地/README.md': ['城市与城邦', '自远方祖树而来的精灵们'],
    '词条/地点/泰拉/地面/诸城所在之地/亚特兰/README.md': ['城市与城邦'],
    '词条/地点/泰拉/地面/诸城所在之地/巴别尔/README.md': ['城市与城邦'],
    '词条/地点/泰拉/地面/诸城所在之地/自缚之城/README.md': ['城市与城邦'],
    '词条/地点/泰拉/地面/诸城所在之地/节点城网络/README.md': ['城市与城邦', '源质实体的起源'],
    '词条/地点/泰拉/地面/诸城所在之地/雾海/README.md': ['城市与城邦'],
    '词条/地点/泰拉/轨道/README.md': ['源质实体的起源'],
    '词条/地点/泰拉/轨道/泰拉轨道服务器阵列/README.md': ['环带前史'],
    '词条/地点/泰拉/轨道/轨道研究站/README.md': ['源质实体的起源'],
    '词条/地点/马尔斯/README.md': ['击魄', '开拓马尔斯'],
    '词条/概念/云上世界.md': ['云上坟场', '环带前史'],
    '词条/概念/信息海.md': ['环带前史'],
}

# 没有分支引用可依的词条：按事件两端的线、或按跨线共用来定。
MANUAL = {
    '词条/事件/大天灾.md': ['通用'],
    '词条/事件/技术一次交付/轨道研究站向节点城交付以太壁垒技术.md': ['源质实体的起源', '城市与城邦'],
    '词条/事件/技术一次交付/轨道研究站向云城网络交付以太航行技术.md': ['源质实体的起源', '环带前史'],
    '词条/事件/外溢与坠落/异魔结构坠落泰拉地面.md': ['开拓马尔斯', '城市与城邦'],
    '词条/事件/外溢与坠落/穿越机污染外溢进入法厄同.md': ['开拓马尔斯', '击魄'],
    '词条/事件/航路/麦哲伦号从法厄同旁高速经过并送出消息.md': ['环带前史'],
    '词条/参与者/势力/执火者.md': ['城市与城邦'],
    '词条/参与者/势力/执火军.md': ['城市与城邦'],
    '词条/参与者/势力/日暮驿站.md': ['城市与城邦'],
    '词条/参与者/族群/城市人.md': ['城市与城邦'],
    '词条/参与者/族群/天赋者.md': ['城市与城邦'],
    '词条/参与者/族群/荒原人.md': ['城市与城邦'],
    '词条/参与者/至高存在/伊勒.md': ['城市与城邦'],
    '词条/参与者/至高存在/巴力.md': ['城市与城邦', '自远方祖树而来的精灵们'],
    '词条/参与者/至高存在/灵界至高存在.md': ['通用'],
    '词条/地点/README.md': ['通用'],
    '词条/地点/云城.md': ['通用'],
    '词条/地点/以太界/README.md': ['通用'],
    '词条/地点/以太界/以太.md': ['通用'],
    '词条/地点/泰拉/README.md': ['源质实体的起源', '城市与城邦', '自远方祖树而来的精灵们'],
    '词条/时间/时代.md': ['通用'],
}


def line_of(rel):
    for prefix, name in LINE_RULES:
        if rel.startswith(prefix):
            return name
    return None


def story_lines_for(rel):
    """地点子区继承所在主线；其余落到城市与城邦之外时由 MANUAL 兜底。"""
    if rel in DERIVED:
        return DERIVED[rel]
    if rel in MANUAL:
        return [MANUAL[rel]] if isinstance(MANUAL[rel], str) else MANUAL[rel]
    if rel.startswith('词条/地点/泰拉/地面/诸城所在之地/') or rel.startswith('词条/地点/泰拉/地面/深渊/'):
        return ['城市与城邦']
    if rel.startswith('词条/地点/泰拉/轨道/'):
        return ['源质实体的起源']
    if rel.startswith('词条/地点/泰拉/地面/世界树/'):
        return ['自远方祖树而来的精灵们']
    return None


def split_blocks(meta):
    """把属性块切成 [(键, [原始行])]。"""
    blocks, cur = [], None
    for line in meta:
        m = re.match(r'^([^\s#\-][^:]*):', line)
        if m:
            cur = (m.group(1).strip(), [line])
            blocks.append(cur)
        elif cur and re.match(r'^\s+-\s', line):
            cur[1].append(line)
        else:
            if cur is not None and line.strip():
                cur[1].append(line)
    return blocks


def render(key, values, indent=''):
    if not values:
        return ['%s%s:' % (indent, key)]
    return ['%s%s:' % (indent, key)] + ['  - %s' % v for v in values]


def apply_file(path, rel, report, do_apply):
    text = open(path, encoding='utf-8').read()
    nl = '\r\n' if '\r\n' in text else '\n'
    m = re.match(r'^---\r?\n([\s\S]*?)\r?\n---', text)
    if not m:
        return
    head, tail = text[:m.start(1)], text[m.end(1):]
    blocks = split_blocks(m.group(1).split(nl))
    keys = [b[0] for b in blocks]

    # 值没变、也没有残留链接时直接跳过，重跑不会产生假改动
    cur = []
    if '故事线' in keys:
        i = keys.index('故事线')
        head_line = blocks[i][1][0].split(':', 1)[1].strip().strip('"').strip("'")
        if head_line:
            cur = [head_line]
        cur += [l.strip()[2:].strip().strip('"').strip("'")
                for l in blocks[i][1][1:] if l.strip().startswith('- ')]
    want = story_lines_for(rel)
    if want and cur == want:
        return

    changed = False
    old = None
    if '故事线' in keys:
        idx = keys.index('故事线')
        old = [l for l in blocks[idx][1][1:] if l.strip().startswith('- ')]
        del blocks[idx]
        keys.pop(idx)
        changed = True

    if not want:
        if changed:
            report.append((rel, '删除旧值，未定新值', old))
        if changed and do_apply:
            open(path, 'w', encoding='utf-8', newline='').write(head + nl.join(sum([b[1] for b in blocks], [])) + tail)
        return

    anchor = '文档状态' if '文档状态' in keys else ('类型' if '类型' in keys else None)
    pos = keys.index(anchor) + 1 if anchor else 0
    blocks.insert(pos, ('故事线', render('故事线', want)))
    report.append((rel, ' -> '.join(want), old))

    if do_apply:
        body = sum([b[1] for b in blocks], [])
        open(path, 'w', encoding='utf-8', newline='').write(head + nl.join(body) + tail)


def main():
    do_apply = '--apply' in sys.argv
    report = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {'.git', '.obsidian', '.idea', '.cursor'}]
        for name in filenames:
            if not name.endswith('.md'):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace('\\', '/')
            text = open(path, encoding='utf-8').read()
            m = re.match(r'^---\r?\n([\s\S]*?)---', text)
            if not m:
                continue
            km = re.search(r'^类型:\s*(.+)$', m.group(1), re.M)
            if not km or km.group(1).strip() != '词条':
                continue
            apply_file(path, rel, report, do_apply)

    for rel, want, old in report:
        mark = '（原为链接写法）' if old and any('](' in l for l in old) else ''
        print('%-56s %s%s' % (rel, want, mark))
    print('\n合计 %d 篇%s' % (len(report), '' if do_apply else '（未写入，加 --apply 才写）'))


if __name__ == '__main__':
    main()
