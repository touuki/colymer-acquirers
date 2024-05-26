# colymer-acquirers
## 这是什么？
[colymer](https://github.com/touuki/colymer)项目的目标是将各个不同平台的信息内容抽象成统一的数据结构后汇集到一起，实现信息的聚集。而此项目colymer-acquirers则是其采集器程序，负责从各个网站爬取内容后抽象成统一格式后保存在colymer中。目前已支持的网站及功能有：  
1. Instagram（由于仅有的账号状态异常，目前有效性未知）: 通过sessionid登录、扫描用户时间线、获取用户快拍
2. Weibo（登录似乎已失效）: 通过SMS验证登录、扫描用户时间线、扫描用户含关键词微博、微博视频
3. Twitter（已失效）: 扫描用户时间线

## 关于用法
目前而言我并没有精力将这个项目短时间内完善成一个通用爬虫项目，因此目前优先满足自用需求，之后有时间再进行通用化完善。有需要及能力的同学可以先通过源码进行学习。

## TODO
+ 将`InstagramStory`采集器并入`Instagram`采集器
+ weibo.com某些账号时间线无法获取2018/3之前的微博（2021/5/24测试，虽然可以通过m.weibo.cn获取，但是简直逼死强迫症），期望官方能修复。。
+ 添加微博文章支持，考虑纳入Twitter Card以及微博外部视频，考虑加入Twitter Fleets支持
+ 添加微信公众号支持
+ 添加Bilibili支持
+ 完善执行脚本，将参数设置改入命令行或使用单独的配置文件，使其更加通用
+ 抽象后端存储，目前是数据直接存储到[colymer](https://github.com/touuki/colymer)，考虑支持本地存储