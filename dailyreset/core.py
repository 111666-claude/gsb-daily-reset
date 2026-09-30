"""每日重置：服务器时区日界、跨多天算术追赶、按玩家幂等。"""

DAY_MS = 86400000


class Resets:
    """按玩家记录的每日重置台账。

    状态只保存每个玩家最近一次结算到的服务日，任何跨天结算都是一次
    算术跳跃（``steps`` 只加 1），与跨越的天数无关。
    """

    def __init__(self, tz_offset_min=480):
        self.tz_offset_min = tz_offset_min
        self.state = {}
        self.steps = 0

    def service_day(self, now_ms):
        """服务日序数：以服务器时区为日界。"""
        return (now_ms + self.tz_offset_min * 60000) // DAY_MS

    def due(self, player, now_ms):
        """把玩家的每日状态结算到 ``now_ms``，返回 ``{granted, missed}``。

        首次结算发 1、``missed=0``；同一服务日重复结算发 0；跨 N 天
        （N >= 1）时发 1、``missed=N-1``，且只产生一次迭代。时间回退
        （早于已结算服务日）视为同一服务日的重复调用。
        """
        day = self.service_day(now_ms)
        record = self.state.get(player)
        if record is None:
            record = {"day": day, "granted": 0}
            self.state[player] = record
            granted = 1
            missed = 0
        else:
            delta = day - record["day"]
            if delta <= 0:
                granted = 0
                missed = 0
            else:
                granted = 1
                missed = delta - 1
                self.steps += 1
                record["day"] = day
        record["granted"] += granted
        return {"granted": granted, "missed": missed}

    def granted_total(self, player):
        return self.state.get(player, {}).get("granted", 0)

    def steps_count(self):
        return self.steps
