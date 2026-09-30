# daily-reset

每日重置：服务器时区日界、跨多天追赶、按玩家幂等，只用 Python 标准库。

```
python3 -m dailyreset.cli --sample rollover
python3 -m dailyreset.cli --sample catchup
python3 -m dailyreset.cli --sample idempotent
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **服务日按服务器时区**：服务日 = `floor((now_ms + tz_offset_min * 60000) / 86400000)`，
  日界以服务器时区为准，客户端本地时间不参与。
- **幂等**：同一个服务日里重复结算不再发奖励（`granted=0`）；跨天之后的第一次结算才发。
- **追赶要是算术跳跃**：跨 N 天时 `granted=1`、`missed=N-1`，结算代价 O(1)，
  不许逐天循环（`steps_count()` 反映迭代次数，必须与天数无关）。
- **规模**：10 万玩家、每个玩家一次跨 10 年的结算，总迭代次数 O(玩家数)，
  内存 O(玩家数)。
- **不变量**：同一时刻重复调用第二次的 `granted` 必为 0；`missed` 等于两次服务日之差减一；
  同一串结算序列重复执行结果相同。

## 输出契约（不改格式）

```
day=1 granted=1
granted=1 missed=999 steps=1
granted_total=1
steps=2000
```

## 目录

```
dailyreset/core.py   服务日、追赶与幂等
dailyreset/cli.py    命令行入口
tests/               unittest 用例
```
