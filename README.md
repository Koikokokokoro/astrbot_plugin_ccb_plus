# C C B PLUS!!!

基于 [灵煞 / ccb](https://github.com/tenno1174/astrbot_plugin_ccb) 的 和QQ群群友发生赛博sex的插件 的改进版。

# 新增的内容
## 更新前建议备份数据文件（如有需要）可能出现意料外错误

## 17/9/2026
### 合并 PR [#11](https://github.com/Koikokokokoro/astrbot_plugin_ccb_plus/pull/11)（nicocatxzc）
可通过插件配置自定义ccb的代号 <br>
可关闭消息附带的头像，防止刷屏 <br>
新增自动撤回，需在插件配置中开启（仅aiocqhttp生效）<br>
新增防牛头人联动，需安装 [astrbot-plugin-wifepicker](https://github.com/Heximiao/astrbot-plugin-wifepicker)（默认关闭）<br>

## 25/8/2026
### 合并 PR [#9](https://github.com/Koikokokokoro/astrbot_plugin_ccb_plus/pull/9)（nicocatxzc）
旧数据自动复制至插件专属目录 <br>
昵称优先显示（群名片 > QQ昵称 > QQ号）<br>
管理员可绕过ccbnodo <br>
添加命令别名：踩踩背 / 捶捶背 <br>

### 统一文本、规范了几个格式
规范导入路径<br>
数据迁移改用move方法<br>
修改一处文案及一处缩进<br>
昵称获取加no_cache强制刷新，但是仍有缓存延迟，变更后第二次起或者重载插件才能够更新（疑似无法完全对齐）<br>

## 19/5/2026
添加命令：ccbclear 清除记录；ccbnodo 防CCB开关。 逻辑来自 [ERX399 / ccb_plus_beta](https://github.com/ERX399/ccb_plus_beta) <br>
清除了一些无效的注释，引用和变量 <br>
整合了一些出现频繁的代码段 <br>

## 24/8/2025
由群友使用量决定，注释了海王榜命令 <br>
添加逻辑：记录单次最大注入量max及其产生者（不存在该项的旧数据使用平均值）<br>
添加逻辑：可以通过插件配置选择是否保留每一次ccb的记录（默认为false）<br>
将max、cb次数添加至ccbinfo <br>
添加max排行榜 <br>

## previous
☑ 荆州容量检查 不会再出现0.00000001ml了！<br>
☑ 群组分离 每个群都可以破一次出了（雾）<br>
☑ 添加北朝记录，保留ccb的人及次数 <br>
☑ 添加养胃，过于频繁的ccb会养胃）））<br>
☑ 添加暴击，有一定概率翻倍

☑ ccbtop 艾草排行榜<br>
☑ ccbvol 失荆州排行榜<br>
☑ ccbinfo 查询ccb信息<br>
☑ haiwang 海王榜<br>
☑ xnn xnn榜<br>

☑ 添加Astrbot配置文件，可以在插件管理中修改部分参数<br>
☑ 添加白名单，白名单内id脱离七情六欲，不能被ccb<br>
☑ ccb.json长期化，现在位置为astrbot/data

todo：<br>

## ...<br>
NULL <br>

群友反应排行榜太多会乱，<br>
考虑删改使用频率低的命令或以图片格式发送

# 绝赞更新中⭐
如有额外需要的功能可以发issue，随缘更新