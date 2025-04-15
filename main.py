# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import json
import random
import os

DATA_FILE = os.path.join(os.getcwd(), "data", "plugins", "astrbot_plugin_ccb_plus", "jilu.json")

a1 = "id"
a2 = "num"
a3 = "vol"


def get_avatar(user_id: str) -> bytes:
    avatar_url = f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"
    return avatar_url


def makeit(data, target_user_id):
    for item in data:
        if a1 in item and item[a1] == target_user_id:
            return 1
    return 2


@register("ccb", "Koikokokokoro", "和群友赛博sex的插件PLUS", "1.1.4")
class ccb(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("ccb")
    async def ccb(self, event: AstrMessageEvent):
        messages = event.get_messages()
        send_id = event.get_sender_id()
        self_id = event.get_self_id()
        target_user_id = next(
            (str(seg.qq) for seg in messages if (isinstance(seg, Comp.At)) and str(seg.qq) != self_id), send_id)
        # 随机生成ccb时长和注入量，并确保注入量只有两位小数
        time = round(random.uniform(1, 60), 2)
        V = round(random.uniform(1, 100), 2)
        pic = get_avatar(target_user_id)
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        a = makeit(data, target_user_id)
        if a == 1:
            try:
                for item in data:
                    if a1 in item and item[a1] == target_user_id:
                        if event.get_platform_name() == "aiocqhttp":
                            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                            assert isinstance(event, AiocqhttpMessageEvent)
                            client = event.bot
                            stranger_payloads = {"user_id": target_user_id}
                            stranger_info: dict = await client.api.call_action('get_stranger_info', **stranger_payloads)
                            nickname = stranger_info['nick']
                            # 确保累加后的次数为整数，注入量两位小数
                            item[a2] = int(item.get(a2, 0)) + 1
                            item[a3] = round(float(item.get(a3, 0)) + V, 2)
                            chain = [
                                Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                                Comp.Image.fromURL(pic),
                                Comp.Plain(f"这是ta的第{item[a2]}次。ta被累积注入了{item[a3]:.2f}ml的生命因子")
                            ]
                            yield event.chain_result(chain)
                            with open(DATA_FILE, 'w') as f:
                                json.dump(data, f)
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
                    # 确保新记录中注入量为两位小数
                    new_record = {"id": target_user_id, "num": 1, "vol": round(V, 2)}
                    data.append(new_record)
                    with open(DATA_FILE, 'w') as f:
                        json.dump(data, f)
            except Exception as e:
                logger.error(f"报错: {e}")
                yield event.plain_result("对方拒绝了和你ccb")

    @filter.command("ccbtop")
    async def ccbtop(self, event: AstrMessageEvent):
        """
        排行榜功能：按ccb次数(num)从高到低排序，只展示前五名
        """
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"读取数据错误: {e}")
            yield event.plain_result("无法读取排行榜数据，请稍后重试。")
            return

        # 按 num 从高到低排序，将 num 强制转换为整数
        sorted_data = sorted(data, key=lambda x: int(x.get(a2, 0)), reverse=True)
        top5 = sorted_data[:5]

        ranking_message = "ccb排行榜TOP5：\n"
        # 遍历排行榜记录
        for idx, record in enumerate(top5, start=1):
            user_id = record.get(a1)
            # 默认昵称为用户id，如果平台为 aiocqhttp 则尝试获取昵称
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
            # 使用格式化字符串确保累计注入量只有两位小数显示
            ranking_message += f"{idx}. {nickname} - ccb次数：{record.get(a2, 0)}，累计注入：{float(record.get(a3, 0)):.2f}ml\n"
        yield event.plain_result(ranking_message)
