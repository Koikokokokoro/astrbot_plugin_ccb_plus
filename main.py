# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from collections import deque
from astrbot.api import AstrBotConfig
from astrbot.api.star import StarTools

import time
import json
import random
import asyncio
from datetime import datetime
import os
import shutil

data_dir = StarTools.get_data_dir("astrbot_plugin_ccb_plus")

DATA_FILE = os.path.join(data_dir, "ccb.json")

LOG_FILE = os.path.join(data_dir, "ccb_log.json")

#migration
old_data_file = "data/ccb.json"
old_log_file = "data/ccb_log.json"

try:
    os.makedirs(data_dir, exist_ok=True)
    # 复制数据文件
    if os.path.exists(old_data_file) and not os.path.exists(DATA_FILE):
        shutil.move(old_data_file, DATA_FILE)
    if os.path.exists(old_log_file) and not os.path.exists(LOG_FILE):
        shutil.move(old_log_file, LOG_FILE)
except Exception:
    pass

a1 = "id"       # qq号
a2 = "num"      # 北朝次数
a3 = "vol"      # 被注入量
a4 = "ccb_by"   # 被谁朝了
a5 = "max"      # 最大值

def get_avatar(user_id: str) -> bytes:
    return f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"

def makeit(group_data, target_user_id):
    return 1 if any(item.get(a1) == target_user_id for item in group_data) else 2

@register("ccb", "Koikokokokoro", "和群友赛博sex的插件PLUS", "1.1.4")
class ccb(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.ccb_name = config.get("ccb_name") # 踩踩背所用代号
        self.window = config.get("yw_window")                 # 滑动窗口长度（秒）
        self.threshold = config.get("yw_threshold")               # 窗口内最大允许动作次数
        self.ban_duration = config.get("yw_ban_duration")      # 禁用时长（秒）
        self.action_times = {}
        self.ban_list = {}
        self.yw_prob = config.get("yw_probability")               # 触发概率
        self.white_list  = config.get("white_list")
        self.selfdo = self.config.get("self_ccb", False)         # 0721 默认为否
        self.dis_ntr = self.config.get("dis_ntr", False)        # 禁止ntr
        self.crit_prob  =   self.config.get("crit_prob")
        self.attach_avatar = self.config.get("attach_avatar", True)     #附带头像
        self.auto_delete  =   self.config.get("auto_delete",False)    # 自动撤回
        self.auto_delete_delay  =   self.config.get("auto_delete_delay",60)
        self._withdraw_tasks: set = set()                   # 定时撤回任务集合
        self.is_log =   self.config.get("is_log")           # 完整日志，默认为false

    #  from issue 6
    async def _is_admin(self, event: AstrMessageEvent) -> bool:
        try:
            return bool(event.is_admin())
        except Exception:
            return False

    def _save_white_list(self):
        try:
            self.config["white_list"] = self.white_list
            save_fn = getattr(self.config, "save", None)
            if callable(save_fn):
                save_fn()
        except Exception as e:
            logger.warning(f"保存白名单失败: {e}")

    # Copyright (C) 2026 astrbot-plugin-wifepicker
    # Source: https://github.com/Heximiao/astrbot-plugin-wifepicker
    # SPDX-License-Identifier: AGPL-3.0-or-later
    # Modified by nicocatxzc on 2026-08-28

    def _can_auto_delete(self, event: AstrMessageEvent) -> bool:
        """是否启用自动撤回：auto_delete 开启且目标消息平台为 aiocqhttp。"""
        return bool(self.auto_delete) and event.get_platform_name() == "aiocqhttp"

    def _get_auto_delete_delay(self) -> int:
        try:
            delay = int(self.auto_delete_delay or 60)
        except Exception:
            delay = 60
        return max(1, delay)

    def _schedule_delete_msg(self, client, message_id) -> None:
        """延迟 auto_delete_delay 秒后撤回指定 message_id 的消息。"""
        delay = self._get_auto_delete_delay()

        async def _runner():
            await asyncio.sleep(delay)
            try:
                await client.api.call_action("delete_msg", message_id=message_id)
            except Exception as e:
                logger.warning(f"自动撤回失败: {e}")

        task = asyncio.create_task(_runner())
        self._withdraw_tasks.add(task)
        task.add_done_callback(self._withdraw_tasks.discard)

    async def _send_with_auto_delete(self, event: AstrMessageEvent, chain=None, text=None) -> bool:
        """
        当 auto_delete 开启且当前平台为 aiocqhttp 时，直接调用 OneBot API 发送消息，
        拿到 message_id 后安排延迟 auto_delete_delay 秒自动撤回。

        返回 True 表示消息已通过 OneBot 直接发送（调用方无需再 yield 结果）；
        返回 False 表示未启用自动撤回或直发失败，应回退到 AstrBot 标准发送路径。
        """
        if not self._can_auto_delete(event):
            return False
        try:
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            if not isinstance(event, AiocqhttpMessageEvent):
                return False
            if text is not None:
                segs = [{"type": "text", "data": {"text": text}}]
            else:
                segs = []
                for seg in chain or []:
                    if isinstance(seg, Comp.Plain):
                        segs.append({"type": "text", "data": {"text": seg.text}})
                    elif isinstance(seg, Comp.At):
                        segs.append({"type": "at", "data": {"qq": seg.qq}})
                    elif isinstance(seg, Comp.Image):
                        image_url = (
                            getattr(seg, "url", None)
                            or getattr(seg, "file", None)
                            or getattr(seg, "path", None)
                        )
                        if image_url:
                            segs.append({"type": "image", "data": {"file": image_url}})
                        else:
                            segs.append({"type": "text", "data": {"text": str(seg)}})
                    else:
                        segs.append({"type": "text", "data": {"text": str(seg)}})

            group_id = event.get_group_id()
            if group_id:
                resp = await event.bot.api.call_action(
                    "send_group_msg", group_id=int(group_id), message=segs
                )
            else:
                resp = await event.bot.api.call_action(
                    "send_private_msg",
                    user_id=int(event.get_sender_id()),
                    message=segs,
                )

            message_id = None
            if isinstance(resp, dict):
                if "message_id" in resp:
                    message_id = resp.get("message_id")
                elif isinstance(resp.get("data"), dict):
                    message_id = resp["data"].get("message_id")

            if message_id is not None:
                self._schedule_delete_msg(event.bot, message_id)
            else:
                logger.warning(f"无法解析 send_*_msg 返回的 message_id: {resp!r}")
            return True
        except Exception as e:
            logger.warning(f"OneBot 直发失败，回退到标准发送路径: {e}")
            return False
    # end autodelete

    # start wifepicker

    def _find_wifepicker_plugin(self):
        """
        从 sys.modules 中查找已加载的 astrbot-plugin-wifepicker 插件模块，
        并返回其插件实例（Star 实例）。
        优先按精确模块路径获取，其次遍历 sys.modules 模糊匹配 wifepicker。
        """
        import sys

        candidate_keys = [
            "data.plugins.astrbot-plugin-wifepicker",
            "data.plugins.astrbot_plugin_wifepicker",
            "astrbot-plugin-wifepicker",
            "astrbot_plugin_wifepicker",
        ]
        for key in candidate_keys:
            mod = sys.modules.get(key)
            if mod is not None:
                plugin = self._get_plugin_instance_from_module(key, mod)
                if plugin is not None:
                    return plugin

        # 兜底：遍历 sys.modules 模糊匹配
        for key, mod in list(sys.modules.items()):
            if mod is None or "wifepicker" not in key.lower():
                continue
            plugin = self._get_plugin_instance_from_module(key, mod)
            if plugin is not None:
                return plugin
        return None

    def _get_plugin_instance_from_module(self, module_path, mod):
        """根据模块路径/模块对象，从 AstrBot star_map 注册表中获取插件实例。"""
        try:
            from astrbot.core.star.star import star_map
            metadata = star_map.get(module_path)
            if metadata is not None and metadata.star_cls is not None:
                return metadata.star_cls
            # 模块内定义的插件类，通过类的 __module__ 反查 star_map
            import inspect
            for attr in vars(mod).values():
                if inspect.isclass(attr):
                    metadata = star_map.get(attr.__module__)
                    if metadata is not None and metadata.star_cls is not None:
                        return metadata.star_cls
        except Exception:
            pass
        return None

    def _target_has_wife_today(self, group_id: str, target_user_id: str, sender_id: str) -> bool:
        """
        参考 astrbot-plugin-wifepicker 的 _cmd_draw_wife ：
        当某用户今日抽取老婆次数 >= daily_limit（原逻辑将返回"你今天已经有老婆了"）
        时，判定对方已经有老婆了。
        最后额外比对操作者：若sender_id为wife_id则放行
        """
        try:
            plugin = self._find_wifepicker_plugin()
            if plugin is None:
                return False

            daily_limit = int(plugin.config.get("daily_limit", 1) or 1)
            if daily_limit <= 0:
                return False

            records = getattr(plugin, "records", None)
            if not isinstance(records, dict):
                return False
            # wifepicker 的 records 每日首次访问会被 ensure_today_records 重置为当日数据，
            # 这里校验日期，避免把昨天的记录算作"今天已有老婆"。
            if records.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return False

            group_data = records.get("groups", {}).get(str(group_id), {})
            group_records = (
                group_data.get("records", []) if isinstance(group_data, dict) else []
            )
            # 收集目标用户今日的记录（user_recs）
            target_records = [
                r
                for r in group_records
                if isinstance(r, dict) and str(r.get("user_id")) == str(target_user_id)
            ]
            if len(target_records) < daily_limit:
                return False
            # 判断请求者是否是目标的老公
            if any(str(r.get("wife_id")) == str(sender_id) for r in target_records):
                return False
            return True
        except Exception as e:
            logger.warning(f"查询 wifepicker 老婆记录失败: {e}")
            return False

        # end wifepicker

    async def _get_nickname(self, event: AstrMessageEvent, user_id: str, strict_event: bool = False) -> str:
        nickname = user_id
        if event.get_platform_name() == "aiocqhttp":
            try:
                from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                if strict_event:
                    assert isinstance(event, AiocqhttpMessageEvent)
                # 优先使用群成员信息：群名片(card) > QQ昵称(nickname) > QQ号
                group_id = event.get_group_id()
                if group_id:
                    try:
                        member_info = await event.bot.api.call_action(
                            'get_group_member_info', group_id=group_id, user_id=user_id, no_cache=True
                        )
                        nick = member_info.get("card") or member_info.get("nickname")
                        if nick:
                            return nick
                    except Exception:
                        pass
                # 回退：使用陌生人信息
                stranger_info = await event.bot.api.call_action(
                    'get_stranger_info', user_id=user_id
                )
                nickname = stranger_info.get("nick", nickname)
            except Exception:
                pass
        return nickname

    # 获取目标用户ID
    def _get_target_user_id(self, event: AstrMessageEvent) -> str:
        self_id = str(event.get_self_id())
        return next(
            (str(seg.qq) for seg in event.get_messages()
             if isinstance(seg, Comp.At) and str(seg.qq) != self_id),
            str(event.get_sender_id())
        )

    # 重新计算由于clear导致的缺口
    def _recalc_max(self, record: dict):
        if not isinstance(record, dict):
            return
        ccb_by = record.get(a4, {}) or {}
        total_num = 0
        try:
            total_num = int(record.get(a2, 0))
        except Exception:
            total_num = 0
        try:
            total_vol = float(record.get(a3, 0))
        except Exception:
            total_vol = 0.0
        if total_num <= 0 or not ccb_by:
            record[a5] = 0.0
            for k, v in ccb_by.items():
                if isinstance(v, dict):
                    v["max"] = False
            record[a4] = ccb_by
            return
        record[a5] = round(total_vol / total_num, 2)
        try:
            best_id = max(
                ccb_by.items(),
                key=lambda x: int(x[1].get("count", 0)) if isinstance(x[1], dict) else 0
            )[0]
        except Exception:
            best_id = None
        if best_id:
            for k, v in ccb_by.items():
                if isinstance(v, dict):
                    v["max"] = (k == best_id)
        record[a4] = ccb_by

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

    @filter.command("ccb", alias={'踩踩背', '捶捶背'})
    async def ccb(self, event: AstrMessageEvent):
        """
        ccb，顾名思义，用来ccb
        用法： ccb [@]
        """

        group_id = str(event.get_group_id())
        send_id = str(event.get_sender_id())
        actor_id = send_id
        now = time.time()

        # 检查是否在禁用期内
        ban_end = self.ban_list.get(actor_id, 0)
        if now < ban_end:
            remain = int(ban_end - now)
            m, s = divmod(remain, 60)
            if not await self._send_with_auto_delete(event, text=f"嘻嘻，你已经一滴不剩了，养胃还剩 {m}分{s}秒"):
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
            if not await self._send_with_auto_delete(event, text="冲得出来吗你就冲，再冲就给你折了"):
                yield event.plain_result("冲得出来吗你就冲，再冲就给你折了")
            return

        target_user_id = self._get_target_user_id(event)

        # dis_ntr
        if self.dis_ntr and self._target_has_wife_today(group_id, target_user_id, send_id):
            if not await self._send_with_auto_delete(event, text="对方已经有老公了，不要动歪心思哦~"):
                yield event.plain_result("对方已经有老公了，不要动歪心思哦~")
            return

        if self.dis_ntr and self._target_has_wife_today(group_id, send_id, target_user_id):
            if not await self._send_with_auto_delete(event, text="你已经有老婆了，要对ta负责哦~"):
                yield event.plain_result("你已经有老婆了，要对ta负责哦~")
            return

        if target_user_id in self.white_list and not await self._is_admin(event):
            nickname = await self._get_nickname(event, target_user_id)
            if not await self._send_with_auto_delete(event, text=f"{nickname} 的后门被后户之神霸占了，不能{self.ccb_name}（悲"):
                yield event.plain_result(f"{nickname} 的后门被后户之神霸占了，不能{self.ccb_name}（悲")
            return

        if target_user_id == actor_id and not self.selfdo:
            if not await self._send_with_auto_delete(event, text="兄啊金箔怎么还能捅到自己的啊（恼）"):
                yield event.plain_result("兄啊金箔怎么还能捅到自己的啊（恼）")
            return

        # CCB 逻辑
        duration = round(random.uniform(1, 60), 2)
        V = round(random.uniform(1, 100), 2)
        prob = self.crit_prob
        crit = False
        is_log = self.is_log
        if random.random() < prob:
            V = round(V * 2, 2)
            crit = True
        pic = get_avatar(target_user_id)
        target_avatar_comp = [Comp.Image.fromURL(pic)] if self.attach_avatar else []

        all_data = self.read_data()
        group_data = all_data.get(group_id, [])

        mode = makeit(group_data, target_user_id)
        if mode == 1:
            # 已有记录，更新
            try:
                for item in group_data:
                    if item.get(a1) == target_user_id:
                        # 获取昵称
                        nickname = await self._get_nickname(event, target_user_id, strict_event=True)

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
                                Comp.Plain(f"你和{nickname}发生了{duration}min长的{self.ccb_name}行为，向ta注入了 💥 暴击！{V:.2f}ml的生命因子\n"),
                                *(target_avatar_comp),
                                Comp.Plain(f"这是ta的第{item[a2]}次。")
                            ]
                        else:
                            # 发送结果
                            chain = [
                                Comp.Plain(f"你和{nickname}发生了{duration}min长的{self.ccb_name}行为，向ta注入了{V:.2f}ml的生命因子\n"),
                                *(target_avatar_comp),
                                Comp.Plain(f"这是ta的第{item[a2]}次。")
                            ]
                        if not await self._send_with_auto_delete(event, chain=chain):
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
                            if not await self._send_with_auto_delete(event, text="💥你的牛牛炸膛了！满身疮痍，再起不能（悲）"):
                                yield event.plain_result("💥你的牛牛炸膛了！满身疮痍，再起不能（悲）")

                        return
            except Exception as e:
                logger.error(f"报错: {e}")
                if not await self._send_with_auto_delete(event, text=f"对方拒绝了和你{self.ccb_name}"):
                    yield event.plain_result(f"对方拒绝了和你{self.ccb_name}")
                return

        else:
            # 新记录
            try:
                nickname = await self._get_nickname(event, target_user_id, strict_event=True)

                chain = [
                    Comp.Plain(f"你和{nickname}发生了{duration}min长的{self.ccb_name}行为，向ta注入了{V:.2f}ml的生命因子\n"),
                    *(target_avatar_comp),
                    Comp.Plain("这是ta的初体验。")
                ]
                if not await self._send_with_auto_delete(event, chain=chain):
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
                    if not await self._send_with_auto_delete(event, text="💥你的牛牛炸膛了！满身疮痍，再起不能（悲）"):
                        yield event.plain_result("💥你的牛牛炸膛了！满身疮痍，再起不能（悲）")

                return
            except Exception as e:
                logger.error(f"报错: {e}")
                if not await self._send_with_auto_delete(event, text=f"对方拒绝了和你{self.ccb_name}"):
                    yield event.plain_result(f"对方拒绝了和你{self.ccb_name}")
                return

    @filter.command("ccbtop")
    async def ccbtop(self, event: AstrMessageEvent):
        """
        按次数排行
        """
        group_id = str(event.get_group_id())
        group_data = self.read_data().get(group_id, [])
        if not group_data:
            if not await self._send_with_auto_delete(event, text=f"当前群暂无{self.ccb_name}记录。"):
                yield event.plain_result(f"当前群暂无{self.ccb_name}记录。")
            return

        top5 = sorted(group_data, key=lambda x: int(x.get(a2, 0)), reverse=True)[:5]
        msg = "被ccb排行榜 TOP5：\n"
        for i, r in enumerate(top5, 1):
            uid = r[a1]
            nick = await self._get_nickname(event, uid)
            msg += f"{i}. {nick} - 次数：{r[a2]}\n"
        if not await self._send_with_auto_delete(event, text=msg):
            yield event.plain_result(msg)

    @filter.command("ccbvol")
    async def ccbvol(self, event: AstrMessageEvent):
        """
        按注入量排行
        """
        group_id = str(event.get_group_id())
        group_data = self.read_data().get(group_id, [])
        if not group_data:
            if not await self._send_with_auto_delete(event, text=f"当前群暂无{self.ccb_name}记录。"):
                yield event.plain_result(f"当前群暂无{self.ccb_name}记录。")
            return

        top5 = sorted(group_data, key=lambda x: float(x.get(a3, 0)), reverse=True)[:5]
        msg = "被注入量排行榜 TOP5：\n"
        for i, r in enumerate(top5, 1):
            uid = r[a1]
            nick = await self._get_nickname(event, uid)
            msg += f"{i}. {nick} - 累计注入：{float(r[a3]):.2f}ml\n"
        if not await self._send_with_auto_delete(event, text=msg):
            yield event.plain_result(msg)

    @filter.command("ccbinfo")
    async def ccbinfo(self, event: AstrMessageEvent):
        """
        查询某人ccb信息：第一次对他ccb的人，被ccb的总次数，注入总量
        用法：ccbinfo [@目标]
        """
        group_id = str(event.get_group_id())
        target_user_id = self._get_target_user_id(event)

        # 读取群数据
        all_data = self.read_data()
        group_data = all_data.get(group_id, [])

        # 查找目标记录
        record = next((r for r in group_data if r.get(a1) == target_user_id), None)
        if not record:
            if not await self._send_with_auto_delete(event, text=f"该用户暂无{self.ccb_name}记录。"):
                yield event.plain_result(f"该用户暂无{self.ccb_name}记录。")
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
        if first_actor:
            first_nick = await self._get_nickname(event, first_actor, strict_event=True)

        # 输出结果
        msg = (
            f"【{record.get(a1)} 】\n"
            f"• 破壁人：{first_nick}\n"
            f"• 北朝：{total_num}\n"
            f"• 朝壁：{cb_total}\n"
            f"• 诗经：{total_vol:.2f}ml\n"
            f"• 马克思：{max_val:.2f}ml"
        )
        if not await self._send_with_auto_delete(event, text=msg):
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
            if not await self._send_with_auto_delete(event, text=f"当前群暂无{self.ccb_name}记录。"):
                yield event.plain_result(f"当前群暂无{self.ccb_name}记录。")
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
            nick = await self._get_nickname(event, uid, strict_event=True)
            producer_nick = producer_id or "未知"
            if producer_id:
                producer_nick = await self._get_nickname(event, producer_id, strict_event=True)

            msg += f"{i}. {nick} - 单次最大：{max_val:.2f}ml（{producer_nick}）\n"

        if not await self._send_with_auto_delete(event, text=msg):
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
            if not await self._send_with_auto_delete(event, text=f"当前群暂无{self.ccb_name}记录。"):
                yield event.plain_result(f"当前群暂无{self.ccb_name}记录。")
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
        msg = "💎 小南梁 TOP5 💎\n"
        for idx, (uid, xnn_val) in enumerate(ranking[:5], 1):
            nick = await self._get_nickname(event, uid, strict_event=True)
            msg += (
                f"{idx}. {nick} - XNN值：{xnn_val:.2f} \n"
                # f"(被ccb次数：{num}，容量：{vol:.2f}ml，对他人ccb：{actions})\n"
            )

        if not await self._send_with_auto_delete(event, text=msg):
            yield event.plain_result(msg)

    # issue 6
    @filter.command("ccbclear")
    async def ccbclear(self, event: AstrMessageEvent):
        """
        管理员指令：清除某人的所有ccb记录
        用法：ccbclear [@目标]
        """
        group_id = str(event.get_group_id())
        if not await self._is_admin(event):
            yield event.plain_result("无权限使用此命令")
            return

        target_user_id = self._get_target_user_id(event)

        all_data = self.read_data()
        group_data = all_data.get(group_id, [])
        if not isinstance(group_data, list):
            group_data = []

        before_len = len(group_data)
        group_data = [r for r in group_data if isinstance(r, dict) and r.get(a1) != target_user_id]
        removed_self = before_len - len(group_data)

        removed_from_others = 0
        modified_records = []
        for record in group_data:
            if not isinstance(record, dict):
                continue
            ccb_by = record.get(a4, {}) or {}
            if target_user_id in ccb_by:
                try:
                    removed_from_others += int(ccb_by[target_user_id].get("count", 0))
                except Exception:
                    removed_from_others += 0
                del ccb_by[target_user_id]
                record[a4] = ccb_by
                record[a2] = sum(
                    int(info.get("count", 0)) for info in ccb_by.values() if isinstance(info, dict)
                )
                modified_records.append(record)

        for record in modified_records:
            self._recalc_max(record)

        all_data[group_id] = group_data
        self.write_data(all_data)

        msg = (
            f"已清除 {target_user_id} 的 {self.ccb_name} 记录：\n"
            f"删除自身被{self.ccb_name}记录：{removed_self} 条\n"
            f"移除朝壁他人记录：{removed_from_others} 次\n"
            f"相关记录已重新校准"
        )
        if not await self._send_with_auto_delete(event, text=msg):
            yield event.plain_result(msg)

    @filter.command("ccbnodo")
    async def ccbnodo(self, event: AstrMessageEvent):
        """
        管理员指令：切换目标防被ccb状态
        用法：ccbnodo [@目标]
        """
        if not await self._is_admin(event):
            yield event.plain_result("无权限使用此命令")
            return

        target_user_id = self._get_target_user_id(event)
        if target_user_id in self.white_list:
            self.white_list = [uid for uid in self.white_list if uid != target_user_id]
            self._save_white_list()
            yield event.plain_result(f"已解除 {target_user_id} 的防{self.ccb_name}保护")
        else:
            self.white_list.append(target_user_id)
            self._save_white_list()
            yield event.plain_result(f"已将 {target_user_id} 加入防{self.ccb_name}保护名单")
