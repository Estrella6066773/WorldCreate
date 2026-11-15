"""回填 `tags` 的 `主题/` 组：把旧主题名并入受控词表，再按篇挂上母题。

旧标签的归并规则写在 REMAP，逐条列出原值与去向；改口径就改表，
不要改成按关键词猜测。新挂的取值按词表顺序排列，重跑不产生差异。

用法：
    python _规范/工具/补标签.py            # 只报告
    python _规范/工具/补标签.py --apply    # 写入
"""
import sys, io, os, re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ORDER = ['人的界定', '意识与备份', '污染与异化', '信仰与神性', '以太与航道',
         '技术授权', '失联与自治', '圈内称谓', '执火']

# 旧主题名 -> 词表取值
REMAP = {
    '云上人身份': '人的界定',
    '伊勒信仰': '信仰与神性',
    '穿越机': '污染与异化',
    '路西法': '圈内称谓',
    '执火叙事': '执火',
}

CLOUD = '分支时间线/法厄同/云上坟场/'
JIPO = '分支时间线/法厄同/击魄/'
IDDIR = CLOUD + '02-暗线/03-人类身份界定/'
TRUTH = CLOUD + '02-暗线/05-玩家真相/'
ASTATION = CLOUD + '02-暗线/04-A站真相/'
CHENG = '词条/地点/泰拉/地面/诸城所在之地/'

# 文件 -> 该篇所属的母题。已核对正文，不按标题猜。
TABLE = {
    # 词条·参与者
    '词条/参与者/人工智能.md': ['人的界定'],
    '词条/参与者/机魂.md': ['人的界定'],
    '词条/参与者/族群/云上人.md': ['人的界定'],
    '词条/参与者/族群/城市人.md': ['人的界定'],
    '词条/参与者/族群/荒原人.md': ['人的界定', '信仰与神性', '执火'],
    '词条/参与者/族群/精灵.md': ['信仰与神性'],
    '词条/参与者/势力/云邦.md': ['失联与自治'],
    '词条/参与者/势力/矿业联盟.md': ['失联与自治'],
    '词条/参与者/势力/智库.md': ['技术授权'],
    '词条/参与者/势力/马尔斯航天.md': ['技术授权'],
    '词条/参与者/势力/海潮派.md': ['信仰与神性'],
    '词条/参与者/势力/牧群派.md': ['信仰与神性'],
    '词条/参与者/势力/执火者.md': ['执火'],
    '词条/参与者/势力/执火军.md': ['执火'],
    '词条/参与者/人物/昏昼.md': ['信仰与神性', '圈内称谓', '执火'],
    '词条/参与者/人物/晨昏星.md': ['信仰与神性', '圈内称谓', '执火'],
    '词条/参与者/至高存在/伊勒.md': ['信仰与神性', '圈内称谓'],
    '词条/参与者/至高存在/巴力.md': ['信仰与神性'],
    '词条/参与者/至高存在/灵界至高存在.md': ['信仰与神性'],
    '词条/参与者/污染/异魔.md': ['污染与异化', '圈内称谓'],
    '词条/参与者/污染/穿越机.md': ['污染与异化', '技术授权'],

    # 词条·地点
    '词条/地点/以太界/以太.md': ['信仰与神性', '以太与航道'],
    '词条/地点/以太界/README.md': ['以太与航道'],
    '词条/地点/云城.md': ['失联与自治'],
    '词条/地点/法厄同/README.md': ['以太与航道', '失联与自治'],
    '词条/地点/泰拉/轨道/轨道研究站/README.md': ['以太与航道', '意识与备份'],
    '词条/地点/泰拉/地面/世界树/README.md': ['信仰与神性'],
    '词条/地点/泰拉/地面/深渊/README.md': ['圈内称谓'],
    CHENG + '执火者旧占领区/README.md': ['执火'],

    # 词条·事件与概念
    '词条/事件/大天灾.md': ['失联与自治', '圈内称谓'],
    '词条/事件/外溢与坠落/异魔结构坠落泰拉地面.md': ['污染与异化', '圈内称谓'],
    '词条/事件/外溢与坠落/穿越机污染外溢进入法厄同.md': ['污染与异化'],
    '词条/事件/技术一次交付/轨道研究站向云城网络交付以太航行技术.md': ['以太与航道', '技术授权'],
    '词条/事件/技术一次交付/轨道研究站向节点城交付以太壁垒技术.md': ['技术授权'],
    '词条/事件/权限/马尔斯航天理事会封存修剪智库.md': ['技术授权'],
    '词条/事件/航路/麦哲伦号从法厄同旁高速经过并送出消息.md': ['以太与航道'],
    '词条/概念/信息海.md': ['以太与航道', '意识与备份'],

    # 分支正文·主线
    '分支时间线/泰拉/轨道/源质实体的起源.md': ['以太与航道', '意识与备份'],
    '分支时间线/泰拉/地面/诸城所在之地/城市与城邦.md': ['信仰与神性', '失联与自治', '执火'],
    '分支时间线/泰拉/地面/世界树/自远方祖树而来的精灵们.md': ['信仰与神性'],
    '分支时间线/卢娜/月面/月人的起源.md': ['污染与异化', '失联与自治'],
    '分支时间线/马尔斯/开拓马尔斯.md': ['技术授权', '失联与自治'],
    '分支时间线/法厄同/环带前史.md': ['以太与航道', '失联与自治'],
    '分支时间线/麦哲伦号/循光之城.md': ['以太与航道'],

    # 分支正文·云上坟场
    CLOUD + '01-明线/站内社会/云上人.md': ['人的界定'],
    CLOUD + '01-明线/站内社会/共信会.md': ['信仰与神性'],
    CLOUD + '02-暗线/02-势力/共信会（暗线真相）.md': ['信仰与神性'],
    CLOUD + '01-明线/驾驶员/驾驶员.md': ['人的界定'],
    CLOUD + '01-明线/出站作业/离散AI.md': ['人的界定'],
    CLOUD + '01-明线/出站作业/智能载具.md': ['意识与备份'],
    IDDIR + '云上人与人工智能.md': ['人的界定'],
    IDDIR + '人工智能认知与记忆.md': ['人的界定'],
    IDDIR + '云邦官方授权.md': ['人的界定', '技术授权'],
    IDDIR + '人格化人工智能禁令.md': ['人的界定'],
    IDDIR + '思维上传的合法标准.md': ['人的界定', '技术授权'],
    ASTATION + '自由政府（非法人工智能）.md': ['人的界定'],
    ASTATION + '思维上传与逃难.md': ['意识与备份'],
    ASTATION + '技术官僚（受害者与施救者）.md': ['技术授权'],
    TRUTH + '驾驶员（人格化人工智能）.md': ['人的界定'],
    TRUTH + '克隆人虚构叙事.md': ['人的界定'],
    TRUTH + '复活与人工智能备份.md': ['意识与备份'],

    # 分支正文·击魄
    JIPO + '01-明线/03-参与者/污染/异魔.md': ['污染与异化', '圈内称谓'],
    JIPO + '01-明线/03-参与者/污染/腐化.md': ['污染与异化'],
    JIPO + '02-暗线/03-参与者/污染/异魔.md': ['污染与异化', '圈内称谓'],
    JIPO + '02-暗线/03-参与者/污染/腐化.md': ['污染与异化'],

    # 总览
    '00-总览/知情对照表.md': ['圈内称谓'],
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


def main():
    do_apply = '--apply' in sys.argv
    log, missing = [], []

    for rel, themes in TABLE.items():
        path = os.path.join(ROOT, rel.replace('/', os.sep))
        if not os.path.exists(path):
            missing.append(rel)
            continue
        text = open(path, encoding='utf-8').read()
        nl = '\r\n' if '\r\n' in text else '\n'
        m = re.match(r'^---\r?\n([\s\S]*?)\r?\n---', text)
        if not m:
            missing.append(rel + '（无属性块）')
            continue
        head, tail = text[:m.start(1)], text[m.end(1):]
        blocks = split_blocks(m.group(1).split(nl))
        keys = [b[0] for b in blocks]

        old, idx = [], None
        if 'tags' in keys:
            idx = keys.index('tags')
            head_line = blocks[idx][1][0].split(':', 1)[1].strip()
            if head_line:
                old.append(head_line)
            old += [l.strip()[2:].strip() for l in blocks[idx][1][1:] if l.strip().startswith('- ')]

        # 保留非主题组（核实、来源），主题组按词表重排
        kept = [v for v in old if not v.startswith('主题/')]
        want = ['主题/' + t for t in ORDER if t in themes] + kept
        if idx is not None and want == old:
            continue

        if idx is not None:
            del blocks[idx]
            keys.pop(idx)

        anchor = '故事线' if '故事线' in keys else ('文档状态' if '文档状态' in keys else '类型')
        pos = keys.index(anchor) + 1 if anchor in keys else len(blocks)
        blocks.insert(pos, ('tags', ['tags:'] + ['  - %s' % v for v in want]))
        log.append((rel, [v[3:] for v in want if v.startswith('主题/')]))

        if do_apply:
            body = [l for b in blocks for l in b[1]]
            while body and not body[-1].strip():
                body.pop()
            open(path, 'w', encoding='utf-8', newline='').write(head + nl.join(body) + tail)

    for rel, themes in log:
        print('%-62s %s' % (rel, ' · '.join(themes)))
    if missing:
        print('\n找不到或不能改：')
        for rel in missing:
            print('   ' + rel)
    print('\n合计 %d 篇%s' % (len(log), '' if do_apply else '（未写入，加 --apply 才写）'))


if __name__ == '__main__':
    main()
