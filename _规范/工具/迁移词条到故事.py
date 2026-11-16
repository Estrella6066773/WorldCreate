import sys, io, os, re, subprocess, argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]

MARS = '分支时间线/马尔斯/词条/参与者'
RING = '分支时间线/法厄同/词条'
JIPO = '分支时间线/法厄同/击魄/词条/参与者'
CITY = '分支时间线/泰拉/地面/诸城所在之地/词条/参与者'
TREE = '分支时间线/泰拉/地面/世界树/词条/参与者'

# 单词条按故事归位：一个事实只有一篇权威。
# 时间、地点、事件三轴不搬：时间是一套刻度，地点是共用空间坐标，事件是跨区接口。
MOVES = {
    # 开拓马尔斯
    '词条/参与者/势力/马尔斯航天.md': f'{MARS}/势力/马尔斯航天.md',
    '词条/参与者/势力/智库.md': f'{MARS}/势力/智库.md',
    '词条/参与者/污染/穿越机.md': f'{MARS}/污染/穿越机.md',
    # 环带前史
    '词条/参与者/势力/云邦.md': f'{RING}/参与者/势力/云邦.md',
    '词条/参与者/势力/矿业联盟.md': f'{RING}/参与者/势力/矿业联盟.md',
    '词条/参与者/族群/云上人.md': f'{RING}/参与者/族群/云上人.md',
    '词条/概念/云上世界.md': f'{RING}/概念/云上世界.md',
    '词条/概念/信息海.md': f'{RING}/概念/信息海.md',
    # 击魄
    '词条/参与者/人工智能.md': f'{JIPO}/人工智能.md',
    '词条/参与者/机魂.md': f'{JIPO}/机魂.md',
    # 城市与城邦
    '词条/参与者/人物/昏昼.md': f'{CITY}/人物/昏昼.md',
    '词条/参与者/人物/晨昏星.md': f'{CITY}/人物/晨昏星.md',
    '词条/参与者/势力/执火军.md': f'{CITY}/势力/执火军.md',
    '词条/参与者/势力/执火者.md': f'{CITY}/势力/执火者.md',
    '词条/参与者/势力/日暮驿站.md': f'{CITY}/势力/日暮驿站.md',
    '词条/参与者/势力/海潮派.md': f'{CITY}/势力/海潮派.md',
    '词条/参与者/势力/牧群派.md': f'{CITY}/势力/牧群派.md',
    '词条/参与者/族群/城市人.md': f'{CITY}/族群/城市人.md',
    '词条/参与者/族群/天赋者.md': f'{CITY}/族群/天赋者.md',
    '词条/参与者/族群/荒原人.md': f'{CITY}/族群/荒原人.md',
    '词条/参与者/至高存在/伊勒.md': f'{CITY}/至高存在/伊勒.md',
    '词条/参与者/至高存在/巴力.md': f'{CITY}/至高存在/巴力.md',
    # 自远方祖树而来的精灵们
    '词条/参与者/族群/精灵.md': f'{TREE}/族群/精灵.md',
}

LINK = re.compile(r'(!?\[[^\]]*\]\()([^)\s]+)(\))')
SKIP_DIRS = {'.git', '.obsidian', 'node_modules', '.trash'}


def md_files():
    for p in ROOT.rglob('*.md'):
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        yield p


def posix(p):
    return p.relative_to(ROOT).as_posix()


def rewrite(text, old_rel, new_rel):
    old_path = Path(old_rel)
    new_path = Path(new_rel)
    moved_file = old_rel != new_rel
    changed = 0

    def sub(m):
        nonlocal changed
        head, target, tail = m.group(1), m.group(2), m.group(3)
        if target.startswith(('http://', 'https://', 'mailto:', '#', '/')) or '://' in target:
            return m.group(0)
        if '{' in target or '}' in target:
            return m.group(0)
        if '#' in target:
            target_path, _, anchor = target.partition('#')
            suffix = '#' + anchor
        else:
            target_path, suffix = target, ''
        if not target_path:
            return m.group(0)
        resolved_old = Path(os.path.normpath(str(old_path.parent / target_path))).as_posix()
        in_moves = resolved_old in MOVES
        # 文件没动、目标也没动：保持原样
        if not moved_file and not in_moves:
            return m.group(0)
        resolved_new = MOVES.get(resolved_old, resolved_old)
        new_target = Path(os.path.relpath(resolved_new, new_path.parent)).as_posix()
        if new_target == target_path:
            return m.group(0)
        changed += 1
        return head + new_target + suffix + tail

    return LINK.sub(sub, text), changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    missing = [s for s in MOVES if not (ROOT / s).exists()]
    if missing:
        print('缺文件，停止（可能已迁移过）：')
        for m in missing:
            print('  ' + m)
        return 1

    texts = {}
    total_links = 0
    for p in md_files():
        old_rel = posix(p)
        new_rel = MOVES.get(old_rel, old_rel)
        new_text, n = rewrite(p.read_text(encoding='utf-8'), old_rel, new_rel)
        texts[(old_rel, new_rel)] = new_text
        total_links += n

    print(f'待移动 {len(MOVES)} 个文件，需改写 {total_links} 条相对链接。')
    if not args.apply:
        for s, d in MOVES.items():
            print(f'  {s}\n    -> {d}')
        print('未写入。加 --apply 执行。')
        return 0

    for s, d in MOVES.items():
        dst = ROOT / d
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'mv', '--force', s, d], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
    for (old_rel, new_rel), text in texts.items():
        (ROOT / new_rel).write_text(text, encoding='utf-8', newline='\n')
    print('已移动并改写链接。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
