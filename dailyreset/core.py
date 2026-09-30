"""每日重置：服务器时区日界、跨多天追赶、按玩家幂等。

缺陷：日界没加服务器时区偏移、追赶靠逐天循环、同一天重复调用还会再发一次奖励。
"""

DAY_MS = 86400000


class Resets:
    """按玩家记录的每日重置台账。"""

    def __init__(self, tz_offset_min=480):
        self.tz_offset_min = tz_offset_min
        self.state = {}
        self.steps = 0

    def service_day(self, now_ms):
        """服务日序数。缺陷：直接用 UTC，没有加服务器时区偏移。"""
        return now_ms // DAY_MS

    def due(self, player, now_ms):
        """把玩家的每日状态结算到 now_ms。

        缺陷：追赶靠逐天循环；同一天重复调用也会再发一次奖励。
        """
        day = self.service_day(now_ms)
        record = self.state.get(player)
        if record is None:
            record = {"day": day, "granted": 0}
            self.state[player] = record
        missed = 0
        current = record["day"]
        while current < day:
            current += 1
            missed += 1
            self.steps += 1
        granted = 1
        record["day"] = day
        record["granted"] += granted
        return {"granted": granted, "missed": missed}

    def granted_total(self, player):
        return self.state.get(player, {}).get("granted", 0)

    def steps_count(self):
        return self.steps
