# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from collections import deque
# from astrbot.api import AstrBotConfig

import time
import json
import random
import os

DATA_FILE = os.path.join(
    os.getcwd(),
    "data", "plugins", "astrbot_plugin_ccb_plus", "ccb.json"
)

a1 = "id"       # qq号
a2 = "num"      # 北朝次数
a3 = "vol"      # 被注入量
a4 = "ccb_by"   # 被谁朝了

def get_avatar(user_id: str) -> bytes:
    return f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"

def makeit(group_data, target_user_id):
    return 1 if any(item.get(a1) == target_user_id for item in group_data) else 2

@register("ccb", "Koikokokokoro", "和群友赛博sex的插件PLUS", "1.1.4")
class ccb(Star):
    def __init__(self, context: Context):
        super().__init__(context)
<<<<<<< Updated upstream
        # self.config = config
        self.WINDOW = 60                 # 滑动窗口长度（秒）
        self.THRESHOLD = 5               # 窗口内最大允许动作次数
        self.BAN_DURATION = 900      # 禁用时长（秒）
=======
        self.config = config
        self.WINDOW = config.get("yw_window")                 # 滑动窗口长度（秒）
        self.THRESHOLD = config.get("yw_threshold")               # 窗口内最大允许动作次数
        self.BAN_DURATION = config.get("yw_ban_duration")      # 禁用时长（秒）
>>>>>>> Stashed changes
        self.action_times = {}
        self.ban_list = {}
        self.YW_PROB = config.get("yw_probability")               # 触发概率
        self.white_list  = config.get("white_list")
        self.selfdo = self.config.get("self_ccb", False)         # 0721 默认为否

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

    @filter.command("ccb")
    async def ccb(self, event: AstrMessageEvent):
        """
        ccb，顾名思义，用来ccb
        用法： ccb [@]
        """
        import time, random

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
        while times and now - times[0] > self.WINDOW:
            times.popleft()
        times.append(now)

        # 超阈值禁用
        if len(times) > self.THRESHOLD:
            self.ban_list[actor_id] = now + self.BAN_DURATION
            times.clear()
            yield event.plain_result("冲得出来吗你就冲，再冲就给你折了")
            return

        # 找到 @ 的目标，否则默认自己
        target_user_id = next(
            (str(seg.qq) for seg in event.get_messages()
             if isinstance(seg, Comp.At) and str(seg.qq) != self_id),
            send_id
        )

        if target_user_id in self.white_list:
            stranger_info = await event.bot.api.call_action(
                'get_stranger_info', user_id=target_user_id
            )
            nickname = stranger_info.get("nick", target_user_id)
            yield event.plain_result(f"{nickname} 的后门被后户之神霸占了，不能ccb（悲")
            return

        if target_user_id == actor_id and not self.selfdo:
            yield event.plain_result("兄啊金箔怎么还能捅到自己的啊（恼）")
            return

        # CCB 逻辑
        duration = round(random.uniform(1, 60), 2)
        V = round(random.uniform(1, 100), 2)
        pic = get_avatar(target_user_id)

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
                        ccb_by = item.get(a4, {})
                        if send_id in ccb_by:
                            ccb_by[send_id]["count"] += 1
                        else:
                            ccb_by[send_id] = {"count": 1, "first": False}
                        item[a4] = ccb_by

                        # 发送结果
                        chain = [
                            Comp.Plain(f"你和{nickname}发生了{duration}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                            Comp.Image.fromURL(pic),
                            Comp.Plain(f"这是ta的第{item[a2]}次。")
                        ]
                        yield event.chain_result(chain)

                        # 写回数据
                        all_data[group_id] = group_data
                        self.write_data(all_data)

                        # 随机养胃
                        if random.random() < self.YW_PROB:
                            self.ban_list[actor_id] = now + self.BAN_DURATION
                            yield event.plain_result("💥你的牛牛炸膛了！满身疮痍，再起不能（悲）")

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
                    Comp.Image.fromURL(pic),
                    Comp.Plain("这是ta的初体验。")
                ]
                yield event.chain_result(chain)

                # 构造并保存新记录
                new_record = {
                    a1: target_user_id,
                    a2: 1,
                    a3: round(V, 2),
                    a4: {send_id: {"count": 1, "first": True}}
                }
                group_data.append(new_record)
                all_data[group_id] = group_data
                self.write_data(all_data)

                # 随机养胃
                if random.random() < self.YW_PROB:
                    self.ban_list[actor_id] = now + self.BAN_DURATION
                    yield event.plain_result("💥你的牛牛炸膛了！满身疮痍，再起不能（悲）")

                return
            except Exception as e:
                logger.error(f"报错: {e}")
                yield event.plain_result("对方拒绝了和你ccb")
                return

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
        msg = "ccb 次数排行榜 TOP5：\n"
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
        msg = "ccb 注入量排行榜 TOP5：\n"
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
            f"• 诗经：{total_vol:.2f}ml"
        )
        yield event.plain_result(msg)

    @filter.command("haiwang")
    async def haiwang(self, event: AstrMessageEvent):
        """
        海王榜
        计算群中最后宫特质的群友
        """
        group_id = str(event.get_group_id())
        all_data = self.read_data()
        group_data = all_data.get(group_id, [])
        if not group_data:
            yield event.plain_result("当前群暂无ccb记录。")
            return

        # 聚合
        stats = {}  # actor_id -> {"first": x, "actions": y}
        for record in group_data:
            ccb_by = record.get(a4, {})
            for actor_id, info in ccb_by.items():
                st = stats.setdefault(actor_id, {"first": 0, "actions": 0})
                st["actions"] += info.get("count", 0)
                if info.get("first"):
                    st["first"] += 1

        # 计算权重并排序
        ranking = []
        for actor_id, st in stats.items():
            weight = st["first"] * 2 + st["actions"]
            ranking.append((actor_id, st["first"], st["actions"], weight))
        ranking.sort(key=lambda x: x[3], reverse=True)
        top5 = ranking[:5]

        # 构造输出
        msg = "🏆 海王榜 TOP5 🏆\n"
        for idx, (actor_id, first_cnt, actions_cnt, weight) in enumerate(top5, 1):
            nick = actor_id
            if event.get_platform_name() == "aiocqhttp":
                try:
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    info = await event.bot.api.call_action("get_stranger_info", user_id=actor_id)
                    nick = info.get("nick", nick)
                except:
                    pass
            msg += (
                f"{idx}. {nick} - 海王值：{weight}\n"
                # f"(首位：{first_cnt}次，ccb：{actions_cnt}次)\n"
            )
        yield event.plain_result(msg)

    @filter.command("xnn")
    async def xnn(self, event: AstrMessageEvent):
        """
        XNN榜
        计算群中最xnn特质的群友
        """
        # 配置权重
        w_num = 1.0
        w_vol = 0.1
        w_action = 0.5

        group_id = str(event.get_group_id())
        all_data = self.read_data()
        group_data = all_data.get(group_id, [])
        if not group_data:
            yield event.plain_result("当前群暂无ccb记录。")
            return

        # 统计每个人对别人的操作次数
        actor_actions = {}
        for record in group_data:
            ccb_by = record.get(a4, {})
            for actor_id, info in ccb_by.items():
                actor_actions[actor_id] = actor_actions.get(actor_id, 0) + info.get("count", 0)

        # 计算xnn值
        ranking = []
        for record in group_data:
            uid = record.get(a1)
            num = int(record.get(a2, 0))
            vol = float(record.get(a3, 0))
            actions = actor_actions.get(uid, 0)
            xnn_value = num * w_num + vol * w_vol - actions * w_action
            ranking.append((uid, xnn_value))

        # 排序
        ranking.sort(key=lambda x: x[1], reverse=True)
        top5 = ranking[:5]

        # 构造输出
        msg = "💎 XNN 榜 TOP5 💎\n"
        for idx, (uid, xnn_val) in enumerate(ranking[:5], 1):
            nick = uid
            if event.get_platform_name() == "aiocqhttp":
                try:
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    info = await event.bot.api.call_action("get_stranger_info", user_id=uid)
                    nick = info.get("nick", nick)
                except:
                    pass
            msg += (
                f"{idx}. {nick} - XNN值：{xnn_val:.2f} \n"
                # f"(被ccb次数：{num}，容量：{vol:.2f}ml，对他人ccb：{actions})\n"
            )

        yield event.plain_result(msg)
