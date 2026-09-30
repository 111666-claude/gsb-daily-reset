"""每日重置：服务器时区日界、跨多天追赶、按玩家幂等。"""

DAY_MS = 86400000
MINUTE_MS = 60000


class Resets:
    """按玩家记录的每日重置台账。"""

    def __init__(self, tz_offset_min=480):
        self.tz_offset_min = tz_offset_min
        self.state = {}
        self.steps = 0

    def service_day(self, now_ms):
        """服务日序数 = floor((now_ms + tz_offset_min * 60000) / 86400000)。"""
        return (now_ms + self.tz_offset_min * MINUTE_MS) // DAY_MS

    def due(self, player, now_ms):
        """把玩家的每日状态结算到 now_ms，返回 {"granted", "missed"}。

        幂等：同一服务日重复结算 granted=0；跨天后第一次结算 granted=1。
        追赶为算术跳跃：跨 N 天 granted=1、missed=N-1，迭代恒为 1 次。
        """
        day = self.service_day(now_ms)
        record = self.state.get(player)
        if record is None:
            self.state[player] = {"day": day, "granted": 1}
            return {"granted": 1, "missed": 0}
        if day <= record["day"]:
            return {"granted": 0, "missed": 0}
        missed = day - record["day"] - 1
        record["day"] = day
        record["granted"] += 1
        self.steps += 1
        return {"granted": 1, "missed": missed}

    def granted_total(self, player):
        return self.state.get(player, {}).get("granted", 0)

    def steps_count(self):
        return self.steps
