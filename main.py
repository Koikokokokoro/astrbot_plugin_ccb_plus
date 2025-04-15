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


# def parse_at_target(self,event):
#  for comp in event.message_obj.message:
#    if isinstance(comp,At):
#      return str(comp.qq)
#    return None

def get_avatar(user_id: str) -> bytes:
    avatar_url = f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"
    return avatar_url


def makeit(data, target_user_id):
    for item in data:
        if a1 in item and item[a1] == target_user_id:
            a = 1
            return a
    a = 2
    return a


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
        # name = parse_at_target()
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
                            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import \
                                AiocqhttpMessageEvent
                            assert isinstance(event, AiocqhttpMessageEvent)
                            client = event.bot
                            stranger_payloads = {"user_id": target_user_id}
                            stranger_info: dict = await client.api.call_action('get_stranger_info', **stranger_payloads)
                            nickname = stranger_info['nick']
                            item[a2] = item[a2] + 1
                            item[a3] = item[a3] + V
                            chain = [
                                Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V}ml的生命因子"),
                                Comp.Image.fromURL(pic),  # 从 URL 发送图片
                                Comp.Plain(f"这是ta的第{item[a2]}次。ta被累积注入了{item[a3]}ml的生命因子")
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
                        Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V}ml的生命因子"),
                        Comp.Image.fromURL(pic),  # 从 URL 发送图片
                        Comp.Plain("这是ta的初体验。")
                    ]
                    yield event.chain_result(chain)
                    dir = {"id": target_user_id, "num": 1, "vol": V}
                    data.append(dir)
                    with open(DATA_FILE, 'w') as f:
                        json.dump(data, f)
            except Exception as e:
                logger.error(f"报错: {e}")
                yield event.plain_result("对方拒绝了和你ccb")

    # 排行榜（为什么需要这个？）
    @filter.command("ccbtop")
    async def ccbtop(self, event: AstrMessageEvent):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)

            if not data:
                yield event.chain_result([Comp.Plain("排行榜是空的，大家都还没开始ccb呢~")])
                return

            # 按照 num（次数）从高到低排序，取前5
            top_data = sorted(data, key=lambda x: x.get("num", 0), reverse=True)[:5]

            if event.get_platform_name() == "aiocqhttp":
                from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot

                msg_chain = [Comp.Plain("📈 CCB排行榜前五名：\n")]
                for idx, item in enumerate(top_data, 1):
                    user_id = item.get("id", "未知")
                    num = item.get("num", 0)
                    vol = item.get("vol", 0)

                    try:
                        stranger_payloads = {"user_id": user_id}
                        stranger_info: dict = await client.api.call_action('get_stranger_info', **stranger_payloads)
                        nickname = stranger_info.get("nick", "未知昵称")
                    except Exception as e:
                        logger.warning(f"获取昵称失败：{e}")
                        nickname = "未知昵称"

                    msg_chain.append(Comp.Plain(f"{idx}. {nickname}（{user_id}）：{num}次，累计 {vol:.2f}ml\n"))

                yield event.chain_result(msg_chain)

        except Exception as e:
            logger.error(f"ccbtop 出错: {e}")
            yield event.chain_result([Comp.Plain("排行榜加载失败了，请稍后再试~")])