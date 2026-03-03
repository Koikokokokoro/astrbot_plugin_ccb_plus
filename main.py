# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from collections import deque
from astrbot.api import AstrBotConfig

import json, os, time, random, math

# DATA_FILE = os.path.join(
#     os.getcwd(),
#     "data", "plugins", "astrbot_plugin_ccb_plus", "ccb.json"
# )

DATA_FILE = "data/ccb.json"

LOG_FILE = "data/ccb_log.json"

a1 = "id"       # qq号
a2 = "num"      # 北朝次数
a3 = "vol"      # 被注入量
a4 = "ccb_by"   # 被谁朝了
a5 = "max"      # 最大值

# 评价label
LABEL_RULES = [
    {"lt": 0.05, "label": "果蝇抖擞精神开始了交配"},
    {"min": 0.05, "label": "巴特曼"},
    {"min": 1,    "label": "兔子"},
    {"min": 3,    "label": "你正常地简直像个人"},
    {"min": 8,    "label": "大狗大狗交教胶"},
    {"min": 30,   "label": "海豚"},
    {"min": 50,   "label": "阿凡提的驴"},
    {"min": 80,   "label": "马吊"},
    {"min": 150,  "label": "猪降临"},
    {"min": 300,  "label": "恐怖！巨大种猪降临"},
    {"min": 600,  "label": "虎鲸"},
    {"min": 1000,  "label": "大象"},
    {"min": 2000, "label": "长毛猛犸象"},
    {"min": 7000, "label": "bro是真正的精鱼"},
]

# 获取label
def get_label_for_vol(vol):
    try:
        v = float(vol)
    except Exception:
        return "二进制生物"
    for r in LABEL_RULES:
        if "lt" in r:
            try:
                if v < float(r["lt"]):
                    return r["label"]
            except Exception:
                continue
    min_rules = [r for r in LABEL_RULES if "min" in r]
    try:
        min_rules = sorted(min_rules, key=lambda x: float(x["min"]))
    except Exception:
        pass
    chosen = None
    for r in min_rules:
        try:
            if v >= float(r["min"]):
                chosen = r["label"]
        except Exception:
            continue
    if chosen:
        return chosen
    if min_rules:
        try:
            return min_rules[0]["label"]
        except Exception:
            return min_rules[0].get("label", "二进制生物")
    return "你什么东西，古神吗"

def get_avatar(user_id: str) -> bytes:
    return f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"

def makeit(group_data, target_user_id):
    return 1 if any(item.get(a1) == target_user_id for item in group_data) else 2

@register("ccb", "Koikokokokoro", "和群友赛博sex的插件PLUS", "1.1.4")
class ccb(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.window = config.get("yw_window")                 # 滑动窗口长度（秒）
        self.threshold = config.get("yw_threshold")               # 窗口内最大允许动作次数
        self.ban_duration = config.get("yw_ban_duration")      # 禁用时长（秒）
        self.action_times = {}
        self.ban_list = {}
        self.yw_prob = config.get("yw_probability")               # 触发概率
        self.white_list  = config.get("white_list")
        self.selfdo = self.config.get("self_ccb", False)         # 0721 默认为否
        self.crit_prob  =   self.config.get("crit_prob")
        self.is_log =   self.config.get("is_log")           # 完整日志，默认为false

        # 新增概率
        self.crit_prob_dx = self.config.get("crit_prob_dx")
        self.tiny_prob = self.config.get("crit_prob_dx")
        self.tail_prob = self.config.get("tail_prob")
        self.skew = self.config.get("skew")

    def read_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"读取数据错误: {e}")
        return {}

    def write_data(self, data):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"写入数据错误: {e}")

    # 记录日志
    def append_log(self, group_id: str, executor_id: str, target_id: str, time: float, vol: float):
        """
        记录日志，格式为：
        {"executor": "...", ````````}
        """
        try:
            # 读取日志，可能用于数据处理
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r', encoding='utf-8') as lf:
                    try:
                        logs = json.load(lf)
                        if not isinstance(logs, list):
                            logs = []
                    except Exception:
                        logs = []
            else:
                logs = []

            # 追加日志内容
            entry = {
                "group": group_id,
                "executor": executor_id,
                "target": target_id,
                "time": time,
                "vol": str(round(float(vol), 2))
            }
            logs.append(entry)

            # 写回
            with open(LOG_FILE, 'w', encoding='utf-8') as lf:
                json.dump(logs, lf, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"append_log 失败: {e}")

    @filter.command("ccb")
    async def ccb(self, event: AstrMessageEvent):
        """
        ccb，顾名思义，用来ccb
        用法： ccb [@]
        """

        group_id = str(event.get_group_id())
        send_id = str(event.get_sender_id())
        self_id = str(event.get_self_id())
        actor_id = send_id
        now = time.time()

        # 检查是否在禁用期内
        ban_end = self.ban_list.get(actor_id, 0)
        if now < ban_end:
            remain = int(ban_end - now)
            m, s = divmod(remain, 60)
            yield event.plain_result(f"嘻嘻，你已经一滴不剩了，养胃还剩 {m}分{s}秒")
            return

        # 窗口时间统计
        times = self.action_times.setdefault(actor_id, deque())
        while times and now - times[0] > self.window:
            times.popleft()
        times.append(now)

        # 超阈值禁用
        if len(times) > self.threshold:
            self.ban_list[actor_id] = now + self.ban_duration
            times.clear()
            yield event.plain_result("冲得出来吗你就冲，再冲就给你折了")
            return

        # 找到 @ 的目标，否则默认自己
        msgs = event.get_messages()
        send_id = str(event.get_sender_id())
        self_id = str(event.get_self_id())

        # 收集 At 段与 Plain 段
        at_segs = [seg for seg in msgs if isinstance(seg, Comp.At)]
        plain_segments = []
        for seg in msgs:
            if isinstance(seg, Comp.Plain):
                # 兼容不同实现，优先取 text 属性，否则 str()
                txt = getattr(seg, "text", None)
                if txt is None:
                    try:
                        txt = str(seg)
                    except Exception:
                        txt = ""
                if txt and txt.strip():
                    plain_segments.append(txt.strip())
        # 拒绝atbot
        if any(str(seg.qq) == self_id for seg in at_segs):
            yield event.plain_result("😅")
            return
        # 拒绝at全体
        at_all_indicators = ("all", "全体", "全体成员", "所有人", "0")
        if any(str(seg.qq).lower() in at_all_indicators for seg in at_segs):
            yield event.plain_result("你要寄吧干什么。")
            return
        # 不能自交的时候且存在非空参数时
        if not self.selfdo:
            if not at_segs and plain_segments:
                yield event.plain_result("你没 @ 人，那就是要捅自己？")
                return

        target_at = next((seg for seg in at_segs if str(seg.qq) != self_id), None)
        if target_at:
            target_user_id = str(target_at.qq)
        else:
            target_user_id = send_id

        if target_user_id in self.white_list:
            stranger_info = await event.bot.api.call_action(
                'get_stranger_info', user_id=target_user_id
            )
            nickname = stranger_info.get("nick", target_user_id)
            yield event.plain_result(f"{nickname} 的后门被后户之神霸占了（悲")
            return

        if target_user_id == actor_id and not self.selfdo:
            yield event.plain_result("兄啊金箔怎么还能捅到自己的啊（恼）")
            return

        # CCB 逻辑
        duration = round(random.uniform(1, 60), 2)

        skew = self.skew  # 幂次偏斜，>1 时更偏向小值，越大小值概率越高
        tiny_prob = self.crit_prob_dx  # 极值概率
        tail_prob = self.tail_prob  # 进入长尾分布（>200）的概率

        # 确定label表中最大项
        try:
            min_vals = [float(r["min"]) for r in LABEL_RULES if "min" in r]
            max_label_min = max(min_vals) if min_vals else 7000.0
        except Exception:
            max_label_min = 7000.0
        tail_upper = max_label_min + 1000

        # 混合采样：
        if random.random() < tail_prob:
            v = math.exp(random.uniform(math.log(1.0), math.log(tail_upper)))
            V = round(v, 2)
            crit = True
        else:
            u = random.random()
            V_raw = 100.0 * (u ** skew)
            if random.random() < tiny_prob:
                V = round(random.uniform(0.001, 0.0499), 4)
            else:
                V = max(0.01, round(V_raw, 2))

            # 暴击判定
            prob = self.crit_prob
            crit = False
            if random.random() < prob:
                V = round(V * 2, 2)
                crit = True

        is_log = self.is_log

        pic = get_avatar(target_user_id)

        label = get_label_for_vol(V)

        all_data = self.read_data()
        group_data = all_data.get(group_id, [])

        mode = makeit(group_data, target_user_id)
        if mode == 1:
            # 已有记录，更新
            try:
                for item in group_data:
                    if item.get(a1) == target_user_id:
                        # 获取昵称
                        nickname = target_user_id
                        if event.get_platform_name() == "aiocqhttp":
                            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import \
                                AiocqhttpMessageEvent
                            assert isinstance(event, AiocqhttpMessageEvent)
                            stranger_info = await event.bot.api.call_action(
                                'get_stranger_info', user_id=target_user_id
                            )
                            nickname = stranger_info.get("nick", nickname)

                        # 更新 num / vol / ccb_by
                        item[a2] = int(item.get(a2, 0)) + 1
                        item[a3] = round(float(item.get(a3, 0)) + V, 2)

                        # 添加逻辑：记录max值的产生者
                        ccb_by = item.get(a4, {}) or {}
                        if send_id in ccb_by:
                            ccb_by[send_id]["count"] = ccb_by[send_id].get("count", 0) + 1
                            ccb_by[send_id]["first"] = ccb_by[send_id].get("first", False)
                        else:
                            ccb_by[send_id] = {"count": 1, "first": False, "max": False}

                        # 添加逻辑：记录max值

                        # 计算max
                        raw_prev = item.get(a5, None)
                        prev_max = 0.0
                        if raw_prev is not None:
                            try:
                                prev_max = float(raw_prev)
                            except (TypeError, ValueError):
                                prev_max = 0.0
                        # 如果不存在合法的 max，使用平均值
                        if prev_max == 0.0:
                            try:
                                total_vol = float(item.get(a3, 0))
                                total_num = int(item.get(a2, 0))
                                if total_num > 0:
                                    prev_max = round(total_vol / total_num, 2)
                                else:
                                    prev_max = 0.0
                            except Exception:
                                prev_max = 0.0

                        if float(V) > prev_max:
                            item[a5] = round(float(V), 2)
                            for k in ccb_by:
                                ccb_by[k]["max"] = False
                            ccb_by[send_id]["max"] = True
                        else:
                            for k in ccb_by:
                                if "max" not in ccb_by[k]:
                                    ccb_by[k]["max"] = False

                        item[a4] = ccb_by

                        if crit:
                            chain = [
                                Comp.Plain(f"你和{nickname}发生了{duration}min长的ccb行为，向ta注入了 💥 暴击！{V:.2f}ml的生命因子"),
                                Comp.Plain(f"评级：{label}"),
                                Comp.Image.fromURL(pic),
                                Comp.Plain(f"这是ta的第{item[a2]}次。")
                            ]
                        else:
                            # 发送结果
                            chain = [
                                Comp.Plain(f"你和{nickname}发生了{duration}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                                Comp.Plain(f"评级：{label}"),
                                Comp.Image.fromURL(pic),
                                Comp.Plain(f"这是ta的第{item[a2]}次。")
                            ]
                        yield event.chain_result(chain)

                        # 是否保留完整日志
                        if is_log:
                            try:
                                self.append_log(group_id, send_id, target_user_id, duration, V)
                            except Exception as e:
                                logger.warning(f"记录日志失败: {e}")

                        # 写回数据
                        all_data[group_id] = group_data
                        self.write_data(all_data)

                        # 随机养胃
                        if random.random() < self.yw_prob:
                            self.ban_list[actor_id] = now + self.ban_duration
                            yield event.plain_result("💥你的牛牛炸膛了！满身疮痍，再起不能（乐）")

                        return
            except Exception as e:
                logger.error(f"报错: {e}")
                yield event.plain_result("对方拒绝了和你ccb")
                return

        else:
            # 新记录
            try:
                nickname = target_user_id
                if event.get_platform_name() == "aiocqhttp":
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    stranger_info = await event.bot.api.call_action(
                        'get_stranger_info', user_id=target_user_id
                    )
                    nickname = stranger_info.get("nick", nickname)

                chain = [
                    Comp.Plain(f"你和{nickname}发生了{duration}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                    Comp.Plain(f"评级：{label}"),
                    Comp.Image.fromURL(pic),
                    Comp.Plain("这是ta的初体验。")
                ]
                yield event.chain_result(chain)

                # 构造并保存新记录
                new_record = {
                    a1: target_user_id,
                    a2: 1,
                    a3: round(V, 2),
                    a4: {send_id: {"count": 1, "first": True, "max": True}},
                    a5: round(V, 2)
                }
                group_data.append(new_record)
                all_data[group_id] = group_data
                self.write_data(all_data)

                # 是否保留完整日志
                if is_log:
                    try:
                        self.append_log(group_id, send_id, target_user_id, duration, V)
                    except Exception as e:
                        logger.warning(f"记录日志失败: {e}")

                # 随机养胃
                if random.random() < self.yw_prob:
                    self.ban_list[actor_id] = now + self.ban_duration
                    yield event.plain_result("💥你的牛牛炸膛了！满身疮痍，再起不能（悲）")

                return
            except Exception as e:
                logger.error(f"报错: {e}")
                yield event.plain_result("对方拒绝了和你ccb")
                return

    # debug用 模拟ccb
    @filter.command("mnccb")
    async def mnccb(self, event: AstrMessageEvent):
        import re, math, random

        msgs = event.get_messages()
        text = ""
        for seg in msgs:
            if isinstance(seg, Comp.Plain):
                txt = getattr(seg, "text", None)
                if txt is None:
                    try:
                        txt = str(seg)
                    except Exception:
                        txt = ""
                text += txt + " "
        m = re.search(r"(\d+)", text)
        if not m:
            yield event.plain_result("用法: /mnccb <正整数>，例如 /mnccb 10")
            return
        n = int(m.group(1))
        if n <= 0:
            yield event.plain_result("参数必须为正整数。")
            return

        MAX_SIM = 50
        if n > MAX_SIM:
            yield event.plain_result(f"次数过大，最多允许模拟 {MAX_SIM} 次。")
            return

        tail_prob = self.tail_prob
        skew = self.skew
        tiny_prob = self.crit_prob_dx

        try:
            min_vals = [float(r["min"]) for r in LABEL_RULES if "min" in r]
            max_label_min = max(min_vals) if min_vals else 7000.0
        except Exception:
            max_label_min = 7000.0
        tail_upper = max_label_min + 1000.0

        lines = [f"模拟 ccb {n} 次："]
        for i in range(1, n + 1):
            if random.random() < tail_prob:
                v = math.exp(random.uniform(math.log(1.0), math.log(tail_upper)))
                V = round(v, 2)
                crit = True
            else:
                u = random.random()
                V_raw = 100.0 * (u ** skew)
                if random.random() < tiny_prob:
                    V = round(random.uniform(0.001, 0.0499), 4)
                else:
                    V = max(0.01, round(V_raw, 2))
                crit = False
                try:
                    prob = self.crit_prob
                except Exception:
                    prob = 0.0
                if random.random() < prob:
                    V = round(V * 2, 2)
                    crit = True

            if float(V) < 0.1:
                V_str = f"{V:.4f}"
            else:
                V_str = f"{V:.2f}"
            status = "💥" if crit else ""
            lines.append(f"{i}. {V_str}ml {status}")
        yield event.plain_result("\n".join(lines))

    @filter.command("ccbtop")
    async def ccbtop(self, event: AstrMessageEvent):
        """
        按次数排行
        """
        group_id = str(event.get_group_id())
        group_data = self.read_data().get(group_id, [])
        if not group_data:
            yield event.plain_result("当前群暂无ccb记录。")
            return

        top5 = sorted(group_data, key=lambda x: int(x.get(a2, 0)), reverse=True)[:5]
        msg = "被ccb排行榜 TOP5：\n"
        for i, r in enumerate(top5, 1):
            uid = r[a1]
            nick = uid
            if event.get_platform_name() == "aiocqhttp":
                try:
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    stranger_info = await event.bot.api.call_action('get_stranger_info', user_id=uid)
                    nick = stranger_info.get("nick", nick)
                except:
                    pass
            msg += f"{i}. {nick} - 次数：{r[a2]}\n"
        yield event.plain_result(msg)

    @filter.command("ccbvol")
    async def ccbvol(self, event: AstrMessageEvent):
        """
        按注入量排行
        """
        group_id = str(event.get_group_id())
        group_data = self.read_data().get(group_id, [])
        if not group_data:
            yield event.plain_result("当前群暂无ccb记录。")
            return

        top5 = sorted(group_data, key=lambda x: float(x.get(a3, 0)), reverse=True)[:5]
        msg = "被注入量排行榜 TOP5：\n"
        for i, r in enumerate(top5, 1):
            uid = r[a1]
            nick = uid
            if event.get_platform_name() == "aiocqhttp":
                try:
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    stranger_info = await event.bot.api.call_action('get_stranger_info', user_id=uid)
                    nick = stranger_info.get("nick", nick)
                except:
                    pass
            msg += f"{i}. {nick} - 累计注入：{float(r[a3]):.2f}ml\n"
        yield event.plain_result(msg)

    @filter.command("ccbinfo")
    async def ccbinfo(self, event: AstrMessageEvent):
        """
        查询某人ccb信息：第一次对他ccb的人，被ccb的总次数，注入总量
        用法：ccbinfo [@目标]
        """
        group_id = str(event.get_group_id())
        # 解析 @ 目标，否则默认查询自己
        self_id = str(event.get_self_id())
        target_user_id = next(
            (str(seg.qq) for seg in event.get_messages()
             if isinstance(seg, Comp.At) and str(seg.qq) != self_id),
            str(event.get_sender_id())
        )

        # 读取群数据
        all_data = self.read_data()
        group_data = all_data.get(group_id, [])

        # 查找目标记录
        record = next((r for r in group_data if r.get(a1) == target_user_id), None)
        if not record:
            yield event.plain_result("该用户暂无ccb记录。")
            return

        # 总次数 & 总注入量
        total_num = int(record.get(a2, 0))
        total_vol = float(record.get(a3, 0))

        raw_max = record.get(a5, None)
        max_val = 0.0
        try:
            if raw_max is not None:
                max_val = float(raw_max)
            else:
                if total_num > 0:
                    max_val = round(total_vol / total_num, 2)
        except Exception:
            max_val = 0.0

        # 计算ccb次数
        cb_total = 0
        try:
            for rec in group_data:
                by = rec.get(a4, {}) or {}
                info = by.get(target_user_id)
                if info:
                    cb_total += int(info.get("count", 0))
        except Exception:
            cb_total = 0

        # 找出第一次的操作者
        ccb_by = record.get(a4, {})
        first_actor = None
        for actor_id, info in ccb_by.items():
            if info.get("first"):
                first_actor = actor_id
                break

        # 如果没标记 first，就选 count 最大的作为“首位”
        if not first_actor and ccb_by:
            first_actor = max(ccb_by.items(), key=lambda x: x[1].get("count", 0))[0]

        # 获取昵称
        first_nick = first_actor or "未知"
        if first_actor and event.get_platform_name() == "aiocqhttp":
            try:
                from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                assert isinstance(event, AiocqhttpMessageEvent)
                stranger_info = await event.bot.api.call_action(
                    'get_stranger_info', user_id=first_actor
                )
                first_nick = stranger_info.get("nick", first_actor)
            except:
                pass

        # 输出结果
        msg = (
            f"【{record.get(a1)} 】\n"
            f"• 破壁人：{first_nick}\n"
            f"• 北朝：{total_num}\n"
            f"• 朝壁：{cb_total}\n"
            f"• 诗经：{total_vol:.2f}ml\n"
            f"• 马克思：{max_val:.2f}ml"
        )
        yield event.plain_result(msg)

    # 单次注入排行榜
    @filter.command("ccbmax")
    async def ccbmax(self, event: AstrMessageEvent):
        """
        按max值排行并输出产生者
        """
        group_id = str(event.get_group_id())
        group_data = self.read_data().get(group_id, [])
        if not group_data:
            yield event.plain_result("当前群暂无ccb记录。")
            return

        # 计算max
        entries = []
        for r in group_data:
            raw_max = r.get(a5, None)
            max_val = 0.0
            try:
                if raw_max is not None:
                    max_val = float(raw_max)
                else:
                    total_vol = float(r.get(a3, 0))
                    total_num = int(r.get(a2, 0))
                    if total_num > 0:
                        max_val = round(total_vol / total_num, 2)
            except Exception:
                max_val = 0.0
            entries.append((r, float(max_val)))

        # 排序
        entries.sort(key=lambda x: x[1], reverse=True)
        top5 = entries[:5]

        msg = "单次最大注入排行榜 TOP5：\n"
        for i, (r, max_val) in enumerate(top5, 1):
            uid = r.get(a1)
            # 解析产生者
            producer_id = None
            ccb_by = r.get(a4, {}) or {}
            for actor_id, info in ccb_by.items():
                if info.get("max"):
                    producer_id = actor_id
                    break
            # 若没有显式标记，则回退选取count最大者
            if not producer_id and ccb_by:
                try:
                    producer_id = max(ccb_by.items(), key=lambda x: x[1].get("count", 0))[0]
                except Exception:
                    producer_id = None

            # 获取昵称
            nick = uid
            producer_nick = producer_id or "未知"
            if event.get_platform_name() == "aiocqhttp":
                try:
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    # 获取被ccb者昵称
                    try:
                        stranger_info = await event.bot.api.call_action('get_stranger_info', user_id=uid)
                        nick = stranger_info.get("nick", nick)
                    except Exception:
                        pass
                    # 获取产生者昵称
                    if producer_id:
                        try:
                            p_info = await event.bot.api.call_action('get_stranger_info', user_id=producer_id)
                            producer_nick = p_info.get("nick", producer_nick)
                        except Exception:
                            pass
                except Exception:
                    pass

            msg += f"{i}. {nick} - 单次最大：{max_val:.2f}ml（{producer_nick}）\n"

        yield event.plain_result(msg)

    @filter.command("ccbhelp", alias={"ccb帮助"})
    async def ccb_help(self, event: AstrMessageEvent):
        """帮助信息"""
        import inspect, re, ast, textwrap

        # 从源码解析各命令及其描述
        try:
            src = inspect.getsource(self.__class__)
            # 匹配形式: @filter.command("命令名", alias={...})
            pattern = re.compile(
                r'@filter\.command\(\s*["\']([^"\']+)["\'](?:\s*,\s*alias\s*=\s*([^)]*))?\)\s*\n\s*async\s+def\s+(\w+)\s*\(',
                re.M | re.S
            )
            matches = pattern.findall(src)

            commands = []
            for cmd, alias_str, func_name in matches:
                # 别名（虽然之前的全部没写）
                aliases = []
                if alias_str and alias_str.strip():
                    try:
                        parsed = ast.literal_eval(alias_str)
                        if isinstance(parsed, dict):
                            aliases = list(parsed.keys())
                        elif isinstance(parsed, (list, tuple, set)):
                            aliases = list(parsed)
                        else:
                            aliases = [str(parsed)]
                    except Exception:
                        try:
                            cleaned = alias_str.strip()
                            cleaned = cleaned.strip("{}[]() ")
                            aliases = [a.strip(" '\"") for a in cleaned.split(",") if a.strip()]
                        except Exception:
                            aliases = []

                # 取函数 docstring 的第一行作为描述
                short = ""
                try:
                    fn = getattr(self, func_name, None)
                    if fn:
                        doc = inspect.getdoc(fn) or ""
                        if doc:
                            short = doc.splitlines()[0].strip()
                except Exception:
                    short = ""

                # 如果没有说明则标记为“无描述”
                if not short:
                    short = "无描述"

                commands.append((cmd, aliases, short))

            if not commands:
                raise RuntimeError("未找到注册命令")

            lines = ["ccb帮助"]
            for cmd, aliases, short in commands:
                alias_part = f"（别名: {', '.join(map(str, aliases))}）" if aliases else ""
                desc = f" - {short}" if short else ""
                lines.append(f"{cmd}{alias_part}{desc}")

            yield event.plain_result("\n".join(lines))
            return

        except Exception as e:
            # 回退：静态帮助（与之前提供的帮助内容类似）
            fallback = (
                "ccb帮助\n\n"
                "ccb [@目标]\n"
                "   对@的目标进行ccb（默认不能自交）。\n"
                "ccbtop\n"
                "  按被ccb次数排序，显示群内TOP5。\n\n"
                "ccbvol\n"
                "  按累计注入量排序，显示群内TOP5。\n\n"
                "ccbinfo [@目标]\n"
                "  查询某人的ccb信息：破壁人、被 ccb 次数、被朝次数、累计被注入量、单次最大值。\n"
                "ccbmax\n"
                "  单次最大注入排行榜，显示群内TOP5，括号内为该次的操作者。\n\n"
                "ccbhelp / ccb帮助\n"
                "  显示本帮助信息。\n\n"
                "注：看到这一行说明help命令未能正常工作\n"
            )
            yield event.plain_result(fallback)
            return