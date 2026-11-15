"""把混合的 `状态` 拆成 `状态`（世界里的存续）与 `文档状态`（能不能引用），并归一 `时代`。

规则见 `_规范/属性与标签规范.md`。默认只报告；加 `--apply` 才写入。

用法：
    python _规范/工具/归一状态与时代.py
    python _规范/工具/归一状态与时代.py --apply
"""
import sys, io, os, re, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_DIRS = {'.git', '.obsidian', '.idea', '.cursor'}

# 原 `状态` 取值 -> (落到哪个字段, 取值, 说明)。说明为 None 表示没有残留信息，丢弃。
SPLIT = {
    # ---- 文档状态：这篇文档写到什么程度 ----
    '现行': ('文档状态', '现行', None),
    '执行规范': ('文档状态', '现行', None),
    '独立子设定集': ('文档状态', '现行', None),
    '随决议更新': ('文档状态', '现行', None),
    '随决议持续更新': ('文档状态', '现行', None),
    '随本集更新': ('文档状态', '现行', None),
    '随词条更新；子设定玩家层对照不收入本表': ('文档状态', '现行', None),
    '随决议持续更新（最后更新：2026-08-12）': ('文档状态', '现行', None),
    '2026-11-08 建立': ('文档状态', '现行', None),
    '2026-08-31 按子设定集总览职责落地': ('文档状态', '现行', None),
    '2026-11-08 改为导航页，条目迁入 `_规范/待办/`': ('文档状态', '现行', None),
    '2026-11-08 改为导航页，条目迁入 `00-总览/待办/`': ('文档状态', '现行', None),
    '2026-08-31 初稿；内容以词条与分支时间线为准': ('文档状态', '现行', None),
    '已自 SpaceShip 设定树完整迁入；与母设定交叉引用持续维护': ('文档状态', '现行', None),
    '本表由 `_规范/工具/同步索引.py` 从 GitHub issue 生成，不要手工编辑': ('文档状态', '现行', None),
    '已定': ('文档状态', '现行', None),
    '已确认': ('文档状态', '现行', None),
    '已确认（2026-08-11·决议六十一）': ('文档状态', '现行', None),
    '已确认——共信会（The Fiducia）；正文词条已更名': ('文档状态', '现行', None),
    '已定名': ('文档状态', '现行', None),
    '已定名（共信会／The Fiducia）；基础性质已确认；细节设计待定': ('文档状态', '现行', '细节设计待定'),
    '中英简称＋全称已确认（2026-08-25 更正为邦联／CCC）': ('文档状态', '现行', None),
    '所见已定': ('文档状态', '现行', None),
    '本集所见已定': ('文档状态', '现行', None),
    '本集时点已定': ('文档状态', '现行', None),
    '所见顺序已定': ('文档状态', '现行', None),
    '阶段顺序已定': ('文档状态', '现行', None),
    '阶段已定': ('文档状态', '现行', None),
    '类型已定': ('文档状态', '现行', None),
    '范围已定': ('文档状态', '现行', None),
    '结果已定': ('文档状态', '现行', None),
    '起源已定': ('文档状态', '现行', None),
    '统称已定': ('文档状态', '现行', None),
    '统称与品类已点名': ('文档状态', '现行', None),
    '身份已定——副官，而不属于驾驶员': ('文档状态', '现行', '副官，不属于驾驶员'),
    '身份已敲定（2026-08-04），行动模式已确认（2026-08-11），动机目的待定': ('文档状态', '现行', '动机目的待定'),
    '索引；细节以游戏工程为准': ('文档状态', '现行', None),
    '法厄同五段已定': ('文档状态', '现行', None),
    '骨架已立': ('文档状态', '骨架', None),
    '接口已定': ('文档状态', '骨架', '仅接口已定'),
    '跨区接口已定': ('文档状态', '骨架', '仅跨区接口已定'),
    '待定': ('文档状态', '待补', None),
    '待决议（用户提供设想，未经确认）': ('文档状态', '待补', '用户提供设想，未经确认'),
    '待决议（聊天讨论结论，未经确认）': ('文档状态', '待补', '聊天讨论结论，未经确认'),
    '待决议（AI 猜想补完，未经用户确认）': ('文档状态', '待补', '智能体猜想补完，未经确认'),
    '待作者确认；定名——核心／Core 已选，额度与核心并存已选': ('文档状态', '待补', '待作者确认'),
    '幻觉已定；本体未写': ('文档状态', '待补', '本体未写'),
    '结果已定，过程未写': ('文档状态', '待补', '过程未写'),
    '存在已定，专名未写': ('文档状态', '待补', '专名未写'),

    '存续（保有生产能力，无力远征）；已定名——云邦／Orbis；云城邦联／CCC；基本单位称成员；州是成员的一种；尚未成州称领地': ('状态', '存续', '保有生产能力，无力远征'),
    '存续（环带大战后保有生产能力，无力远征）；已定名——简称云邦／Orbis；全称云城邦联／CCC；基本单位称成员；州／state 是成员的一种；尚未成州称领地／territory': ('状态', '存续', '环带大战后保有生产能力，无力远征'),
    '存续（节点可独立或重组）；已定名——云城／Cloud City（邦联全称中的 Cloud City）': ('状态', '存续', '节点可独立或重组'),
    '持续存在；旧文明对世界底层的构想，只在设定真相层使用': ('状态', '存续', '旧文明对世界底层的构想，只在设定真相层使用'),
    '待作者确认；定名——核心／Core 已选，额度与核心并存已选；口径——额度＝配给／虚拟寿命（耗尽即静滞），核心＝物质界／实质，算力＝能力基准（非上限、无明确值或边界）；分界——核心与额度为云上人（人）特有，AI 不受此限制；玩家可见文案仅一句「AI 不受此限制。」': ('文档状态', '待补', '待作者确认'),

    # ---- 状态：这个世界里该实体还在不在 ----
    '活跃': ('状态', '存续', None),
    '存续': ('状态', '存续', None),
    '使用中': ('状态', '存续', None),
    '运行中': ('状态', '存续', None),
    '生效中': ('状态', '存续', None),
    '存活（A 站驾驶员）': ('状态', '存续', 'A 站驾驶员'),
    '存在（准入依赖信物）': ('状态', '存续', '准入依赖信物'),
    '存在（仅可通过痕迹感知）': ('状态', '存续', '仅可通过痕迹感知'),
    '持续存在；仅能被间接感知与有限干预': ('状态', '存续', '仅能被间接感知与有限干预'),
    '持续存在；性质随环境与灾变可变': ('状态', '存续', '性质随环境与灾变可变'),
    '存续（与自由政府互相钳制）': ('状态', '存续', '与自由政府互相钳制'),
    '存续（A 站技术官僚）；英文定名 Cloudtype 已确认': ('状态', '存续', 'A 站技术官僚'),
    '存续（实施独裁统治）': ('状态', '存续', '实施独裁统治'),
    '存续（战场遗存）；英文定名 Dispersed AI 已确认': ('状态', '存续', '战场遗存'),
    '存续（保有生产能力，无力远征）；已定名——云邦／Orbis': ('状态', '存续', '保有生产能力，无力远征'),
    '存续（人格堆叠事业进行中）；已定名共信会（The Fiducia）': ('状态', '存续', '人格堆叠事业进行中'),
    '存续（环带大战参战方，战后注资自由空间站）': ('状态', '存续', '环带大战参战方，战后注资自由空间站'),
    '存续（环带内战参战方，亚冷战期间控制环带大片区域）': ('状态', '存续', '环带内战参战方，僵持期间控制环带大片区域'),
    '存续（掩护关系生效中）': ('状态', '存续', '掩护关系生效中'),
    '存续（非法 AI 掌权）': ('状态', '存续', '非法 AI 掌权'),
    '存续（作为「非人类」存在形式）': ('状态', '存续', '作为「非人类」存在形式'),
    '生效中（核心规则）': ('状态', '存续', '核心规则'),
    '生效中（硬约束）': ('状态', '存续', '硬约束'),
    '生效中（云邦明文禁令；A 站私下违反）': ('状态', '存续', '云邦明文禁令，A 站私下违反'),
    '生效中（检查点回滚机制运行中）': ('状态', '存续', '检查点回滚机制运行中'),
    '生效中（不知情）': ('状态', '存续', '不知情'),
    '虚构叙事生效中': ('状态', '存续', '虚构叙事生效中'),
    '运行中（承载 A 站虚拟社会）': ('状态', '存续', '承载 A 站虚拟社会'),
    '自由空间站（表层呈有人居住的 A 站社会）': ('状态', '存续', '自由空间站，表层呈 A 站社会'),
    '无人站点，表层呈 A 站虚拟社会': ('状态', '存续', '表层呈 A 站虚拟社会'),
    '实体无人站点；表层呈 A 站虚拟社会': ('状态', '存续', '无人站点，表层呈 A 站虚拟社会'),
    '活跃；已定名——云上人／Cloudtype': ('状态', '存续', None),
    '活跃（祖树异变后）': ('状态', '存续', '祖树异变后'),
    '活跃（碎片化后仍存续）': ('状态', '存续', '碎片化后仍存续'),
    '活跃 / 部分设施孤立': ('状态', '存续', '部分设施孤立'),
    '战后长期运行中': ('状态', '存续', None),
    '名号沿用中（与昏昼面相绑定为现行口径）': ('状态', '存续', '与昏昼面相绑定'),
    '总控已封存修剪；局部通用模型仍可用': ('状态', '存续', '总控已封存修剪，局部通用模型仍可用'),
    '失控／扩散中；名字仍叫穿越机，新名字未定': ('状态', '存续', '扩散中，新名未定'),
    '信仰存续；伊勒与巴力并不同源': ('状态', '存续', '伊勒与巴力并不同源'),
    '多地并存，影响区域性': ('状态', '存续', '影响区域性'),
    '开发中／污染存续／与主世界失联后独立运行': ('状态', '存续', '污染存续，与主世界失联后独立运行'),
    '崩溃后仍以多个小世界形式存续；只在设定真相层使用': ('状态', '存续', '以多个小世界形式存续，只在设定真相层使用'),
    '与世隔绝': ('状态', '存续', '与世隔绝'),
    '被困 / 孤立研究': ('状态', '存续', '被困，孤立研究'),
    '高危 / 勘探受限': ('状态', '存续', '高危，勘探受限'),
    '历史占领 / 离散以太区存续': ('状态', '存续', '历史占领，离散以太区存续'),
    '高危': ('状态', '存续', '高危'),
    '禁区级': ('状态', '存续', '禁区级'),
    '已发生（自由政府建立）': ('状态', '已发生', '自由政府建立'),
    '已发生（环带失联、混乱开始）': ('状态', '已发生', '环带失联，混乱开始'),
    '已发生（统治者已迁至数字空间）': ('状态', '已发生', '统治者已迁至数字空间'),
    '已结束（环带遍地废墟）': ('状态', '已发生', '环带遍地废墟'),
    '与 A 站依附合作关系已终结': ('状态', '已中断', '与 A 站依附合作关系'),
    '遗址': ('状态', '已消亡', None),
    '遗址 / 边境节点城': ('状态', '已消亡', '边境节点城'),
    '神圣遗址（教会叙事）': ('状态', '已消亡', '教会叙事'),
    '废墟 / 方位参照': ('状态', '已消亡', '方位参照'),
    '掩埋 / 勘探受限': ('状态', '已消亡', '掩埋，勘探受限'),
    '大战后遍地废墟': ('状态', '已消亡', '战后废墟'),
    '逐渐陷落 / 革命后瓦解': ('状态', '已消亡', '逐渐陷落，革命后瓦解'),
    '历史上活跃；执火者革命后被放逐至自缚之城，退出世界舞台': ('状态', '已消亡', '被放逐至自缚之城'),
    '节点城时期为教会正统；执火者革命后随城市人被放逐而衰落': ('状态', '已消亡', '执火者革命后衰落'),
}

# 原 `时代` 取值 -> 受控取值。None 表示模板占位，原样保留。
ERA = {
    '大灾变前': '大灾变前',
    '灾后': '灾后',
    '战前': '灾后',
    '战前（环带大战之前）': '灾后',
    '战前至战后': '贯穿',
    '战时': '环带内战',
    '战时早期': '环带内战',
    '战时（战争中后期投放）': '环带内战',
    '战后': '僵持',
    '战后（遗存）': '僵持',
    '战后（A 站脱离巨企N 之后）': '僵持',
    '战后（历史横跨战前': '贯穿',
    '战后（历史横跨战前战时）': '贯穿',
    '大天灾': '大天灾',
    '大天灾（陷落）': '大天灾',
    '大天灾（及更早萌芽）': '大天灾',
    '大天灾之后': '灾后',
    '大天灾（陷落）起': '灾后',
    '前文明末期': '前文明末期',
    '前文明末期（国教化）': '前文明末期',
    '旧文明': '前文明末期',
    '环带内战': '环带内战',
    '亚冷战': '僵持',
    '抗击异魔': '抗击异魔',
    '抗击异魔期间': '抗击异魔',
    '抗击异魔（环带所见起于亚冷战之后的外溢）': '抗击异魔',
    '灾变时代': '灾变时代',
    '节点城时代': '节点城时代',
    '贯穿': '贯穿',
    '贯穿（大灾变后收紧）': '贯穿',
    '贯穿（战后被打破）': '贯穿',
    '超越时代（创世层级）': '贯穿',
    '超越时代（创世层）': '贯穿',
    '路西法叛变以降（叙事上贯穿洪泛期与此后的地面冲突）': '灾变时代',
    '待定': '未定',
    '{时代一}': None,
    '{时代二}': None,
}

HEAD = ['类型', '文档状态', '状态', '时代', 'tags', '状态说明']


def split_front(text):
    m = re.match(r'^---\r?\n([\s\S]*?)\r?\n---\r?\n?', text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def read_fields(front):
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


def render(fields, order):
    out = []
    for key in HEAD:
        values = fields.get(key)
        if not values:
            continue
        if len(values) == 1 and key != 'tags':
            out.append('%s: %s' % (key, values[0]))
        else:
            out.append('%s:' % key)
            out.extend('  - ' + v for v in values)
    for key in order:
        if key in HEAD or key in ('分类',):
            continue
        values = fields.get(key, [])
        if len(values) == 1:
            out.append('%s: %s' % (key, values[0]))
        elif values:
            out.append('%s:' % key)
            out.extend('  - ' + v for v in values)
    return '\n'.join(out)


def fill_doc_state(apply):
    """给可被引用的文档补 `文档状态`。草稿、原文、绘图不参与这一轴。"""
    CITABLE = ('词条', '分支正文', '规范', '索引')
    added = collections.Counter()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if not name.endswith('.md'):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace('\\', '/')
            raw = open(path, encoding='utf-8', errors='ignore').read()
            front, body = split_front(raw)
            if front is None:
                continue
            fields, order = read_fields(front)
            if fields.get('文档状态'):
                continue
            kind = (fields.get('类型') or [''])[0]
            archived = '/归档/' in rel
            if kind not in CITABLE and not archived:
                continue
            value = '存档' if archived else '现行'
            fields['文档状态'] = [value]
            added[value] += 1
            open(path, 'w', encoding='utf-8', newline='\n').write(
                '---\n' + render(fields, order) + '\n---\n' + body.lstrip('\r'))
    print('补 `文档状态`: 现行 %d 篇，存档 %d 篇' % (added['现行'], added['存档']))


def main():
    if '--fill-doc-state' in sys.argv:
        fill_doc_state('--apply' in sys.argv)
        return
    apply = '--apply' in sys.argv
    stats = collections.Counter()
    unmapped = collections.Counter()
    conflicts, era_left, no_state, changed = [], [], [], 0

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if not name.endswith('.md'):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace('\\', '/')
            raw = open(path, encoding='utf-8', errors='ignore').read()
            front, body = split_front(raw)
            if front is None:
                continue
            fields, order = read_fields(front)
            if '状态' not in fields and '时代' not in fields and '文档状态' not in fields:
                continue

            old_state = [unquote(v) for v in fields.get('状态', [])]
            target, note, keep = None, None, None
            if old_state:
                if len(old_state) > 1:
                    conflicts.append((rel, old_state))
                for value in old_state:
                    if value in SPLIT:
                        field, token, extra = SPLIT[value]
                        stats[(field, token)] += 1
                        if field == '文档状态':
                            fields['文档状态'] = [token]
                        else:
                            target = token
                            note = extra
                    elif re.fullmatch(r'\{.*\}', value):
                        keep = value  # 模板占位符，原样保留
                    else:
                        unmapped[value] += 1
            if target:
                fields['状态'] = [target]
            elif keep:
                fields['状态'] = [keep]
            else:
                fields.pop('状态', None)
            if note:
                fields['状态说明'] = [note]
            else:
                fields.pop('状态说明', None)

            eras = []
            raw_eras = [unquote(v) for v in fields.get('时代', [])]
            # 括号没闭合的列表值会被拆成两行，先并回去
            merged, buf = [], ''
            for value in raw_eras:
                buf = (buf + value) if buf else value
                if buf.count('（') > buf.count('）'):
                    continue
                merged.append(buf)
                buf = ''
            if buf:
                merged.append(buf)

            for value in merged:
                if value in ERA:
                    mapped = ERA[value]
                    if mapped is None:
                        eras.append(value)
                    elif mapped not in eras:
                        eras.append(mapped)
                else:
                    era_left.append((rel, value))
                    eras.append(value)
            if eras:
                fields['时代'] = eras
            else:
                fields.pop('时代', None)

            if '状态' not in fields and '文档状态' not in fields and '时代' not in fields:
                no_state.append(rel)

            new_text = '---\n' + render(fields, order) + '\n---\n' + body.lstrip('\r')
            if new_text != raw:
                changed += 1
                if apply:
                    open(path, 'w', encoding='utf-8', newline='\n').write(new_text)

    print(('已写入' if apply else '试运行：将改写') + ' %d 篇' % changed)

    print('\n=== 拆分结果 ===')
    for field in ('文档状态', '状态'):
        print('\n[%s]' % field)
        for (f, token), count in sorted(stats.items()):
            if f == field:
                print('   %3d  %s' % (count, token))

    print('\n=== 无法归位、需要人工判断的 `状态` 取值 ===')
    for value, count in unmapped.most_common():
        print('   %3d  %s' % (count, value))

    print('\n=== 未映射的 `时代` 取值 ===')
    for rel, value in era_left:
        print('   %-50s  %s' % (rel, value))

    print('\n=== 一个文档写了多个 `状态` 的 ===')
    for rel, values in conflicts:
        print('   %-50s  %s' % (rel, values))

    if not apply:
        print('\n以上为试运行结果，未改动任何文件。确认后加 --apply 写入。')


if __name__ == '__main__':
    main()
