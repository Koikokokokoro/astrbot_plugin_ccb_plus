# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import json
import random
import os

DATA_FILE = os.path.join(os.getcwd(), "data", "plugins", "astrbot_plugin_ccb_plus", "ccb.json")

a1 = "id"
a2 = "num"
a3 = "vol"


def get_avatar(user_id: str) -> bytes:
    avatar_url = f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"
    return avatar_url


def makeit(group_data, target_user_id):
    for item in group_data:
        if a1 in item and item[a1] == target_user_id:
            return 1
    return 2


@register("ccb", "Koikokokokoro", "和群友赛博sex的插件PLUS", "1.1.4")
class ccb(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    def read_data(self):
        # 尝试读取数据文件，如不存在则返回空字典
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
        except Exception as e:
            logger.error(f"读取数据错误: {e}")
            data = {}
        return data

    def write_data(self, data):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"写入数据错误: {e}")

    @filter.command("ccb")
    async def ccb(self, event: AstrMessageEvent):
        group_id = event.get_group_id()
        messages = event.get_messages()
        send_id = event.get_sender_id()
        self_id = event.get_self_id()
        target_user_id = next(
            (str(seg.qq) for seg in messages if (isinstance(seg, Comp.At)) and str(seg.qq) != self_id),
            send_id
        )
        # 生成ccb时长和注入量，注入量保留两位小数
        time = round(random.uniform(1, 60), 2)
        V = round(random.uniform(1, 100), 2)
        pic = get_avatar(target_user_id)

        # 读取所有群的数据，并获取当前群的数据列表
        all_data = self.read_data()
        group_data = all_data.get(group_id, [])

        a = makeit(group_data, target_user_id)
        if a == 1:
            try:
                for item in group_data:
                    if a1 in item and item[a1] == target_user_id:
                        if event.get_platform_name() == "aiocqhttp":
                            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import \
                                AiocqhttpMessageEvent
                            assert isinstance(event, AiocqhttpMessageEvent)
                            client = event.bot
                            stranger_payloads = {"user_id": target_user_id}
                            stranger_info: dict = await client.api.call_action('get_stranger_info', **stranger_payloads)
                            nickname = stranger_info['nick']
                            # 累计次数和注入量处理，次数为整数，注入量保留两位小数
                            item[a2] = int(item.get(a2, 0)) + 1
                            item[a3] = round(float(item.get(a3, 0)) + V, 2)
                            chain = [
                                Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                                Comp.Image.fromURL(pic),
                                Comp.Plain(f"这是ta的第{item[a2]}次。")
                            ]
                            yield event.chain_result(chain)
                            # 更新当前群数据并写入
                            all_data[group_id] = group_data
                            self.write_data(all_data)
                            break
            except Exception as e:
                logger.error(f"报错: {e}")
                yield event.plain_result("对方拒绝了和你ccb")
        if a == 2:
            try:
                if event.get_platform_name() == "aiocqhttp":
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    client = event.bot
                    stranger_payloads = {"user_id": target_user_id}
                    stranger_info: dict = await client.api.call_action('get_stranger_info', **stranger_payloads)
                    nickname = stranger_info['nick']
                    chain = [
                        Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                        Comp.Image.fromURL(pic),
                        Comp.Plain("这是ta的初体验。")
                    ]
                    yield event.chain_result(chain)
                    # 添加新记录到当前群数据中
                    new_record = {"id": target_user_id, "num": 1, "vol": round(V, 2)}
                    group_data.append(new_record)
                    all_data[group_id] = group_data
                    self.write_data(all_data)
            except Exception as e:
                logger.error(f"报错: {e}")
                yield event.plain_result("对方拒绝了和你ccb")

    #艾草排行榜（？
    @filter.command("ccbtop")
    async def ccbtop(self, event: AstrMessageEvent):
        """
        排行榜功能：按ccb次数(num)从高到低排序，只展示前五名（不显示累计注入量）
        """
        group_id = event.get_group_id()
        all_data = self.read_data()
        group_data = all_data.get(group_id, [])

        # 若当前群无数据，则返回提示
        if not group_data:
            yield event.plain_result("当前群暂无ccb记录。")
            return

        sorted_data = sorted(group_data, key=lambda x: int(x.get(a2, 0)), reverse=True)
        top5 = sorted_data[:5]

        ranking_message = "艾草排行榜TOP5：\n"
        for idx, record in enumerate(top5, start=1):
            user_id = record.get(a1)
            nickname = user_id
            if event.get_platform_name() == "aiocqhttp":
                try:
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    client = event.bot
                    stranger_payloads = {"user_id": user_id}
                    stranger_info: dict = await client.api.call_action('get_stranger_info', **stranger_payloads)
                    nickname = stranger_info.get('nick', user_id)
                except Exception as e:
                    logger.error(f"获取用户昵称失败: {e}")
            ranking_message += f"{idx}. {nickname} - 艾草次数：{record.get(a2, 0)}\n"
        yield event.plain_result(ranking_message)

    #好喝爱喝
    @filter.command("ccbvol")
    async def ccbvol(self, event: AstrMessageEvent):
        """
        排行榜功能：按累计注入量(vol)从高到低排序，只展示前五名（不显示ccb次数）
        """
        group_id = event.get_group_id()
        all_data = self.read_data()
        group_data = all_data.get(group_id, [])

        if not group_data:
            yield event.plain_result("当前群暂无ccb记录。")
            return

        sorted_data = sorted(group_data, key=lambda x: float(x.get(a3, 0)), reverse=True)
        top5 = sorted_data[:5]

        ranking_message = "累计失荆州排行榜TOP5：\n"
        for idx, record in enumerate(top5, start=1):
            user_id = record.get(a1)
            nickname = user_id
            if event.get_platform_name() == "aiocqhttp":
                try:
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                    assert isinstance(event, AiocqhttpMessageEvent)
                    client = event.bot
                    stranger_payloads = {"user_id": user_id}
                    stranger_info: dict = await client.api.call_action('get_stranger_info', **stranger_payloads)
                    nickname = stranger_info.get('nick', user_id)
                except Exception as e:
                    logger.error(f"获取用户昵称失败: {e}")
            ranking_message += f"{idx}. {nickname} - 累计荆州：{float(record.get(a3, 0)):.2f}ml\n"
        yield event.plain_result(ranking_message)
