import random
import unittest

from dailyreset.core import DAY_MS, Resets


class ServiceDayTest(unittest.TestCase):
    def test_first_day_is_zero(self):
        self.assertEqual(Resets(480).service_day(0), 0)

    def test_day_advances_after_a_full_day(self):
        self.assertEqual(Resets(480).service_day(DAY_MS), 1)


class DueTest(unittest.TestCase):
    def test_first_call_grants(self):
        resets = Resets(480)
        self.assertEqual(resets.due("p", 0)["granted"], 1)

    def test_player_is_registered(self):
        resets = Resets(480)
        resets.due("p", 0)
        self.assertIn("p", resets.state)

    def test_steps_start_at_zero(self):
        self.assertEqual(Resets(480).steps_count(), 0)


class TimezoneBoundaryTest(unittest.TestCase):
    def test_positive_offset_flips_day_before_utc_midnight(self):
        resets = Resets(480)
        resets.due("p", 0)
        # UTC 仍是第 0 天，+8 时区已翻到第 1 天（57600000 = 16h）。
        result = resets.due("p", 57600000)
        self.assertEqual(resets.state["p"]["day"], 1)
        self.assertEqual(result["granted"], 1)
        self.assertEqual(result["missed"], 0)

    def test_negative_offset_delays_day_flip(self):
        resets = Resets(-480)
        # UTC 已翻日，但 -8 时区仍在第 0 天。
        self.assertEqual(resets.service_day(57600000), 0)
        self.assertEqual(resets.service_day(DAY_MS + 28800000 - 1), 0)
        self.assertEqual(resets.service_day(DAY_MS + 28800000), 1)

    def test_day_depends_only_on_server_timezone(self):
        now_ms = DAY_MS - 3600000
        self.assertEqual(Resets(480).service_day(now_ms), 1)
        self.assertEqual(Resets(0).service_day(now_ms), 0)
        self.assertEqual(Resets(-480).service_day(now_ms), 0)


class IdempotentTest(unittest.TestCase):
    def test_repeat_same_timestamp_grants_zero(self):
        resets = Resets(480)
        self.assertEqual(resets.due("p", 1000)["granted"], 1)
        self.assertEqual(resets.due("p", 1000)["granted"], 0)
        self.assertEqual(resets.due("p", 1000)["granted"], 0)
        self.assertEqual(resets.granted_total("p"), 1)

    def test_repeat_within_same_service_day_grants_zero(self):
        resets = Resets(480)
        resets.due("p", 1000)
        result = resets.due("p", 2000)
        self.assertEqual((result["granted"], result["missed"]), (0, 0))
        self.assertEqual(resets.granted_total("p"), 1)

    def test_first_settlement_after_rollover_grants(self):
        resets = Resets(480)
        resets.due("p", 0)
        self.assertEqual(resets.due("p", 57600000)["granted"], 1)
        self.assertEqual(resets.due("p", 57600000)["granted"], 0)


class CatchupTest(unittest.TestCase):
    def test_multi_day_jump_is_arithmetic(self):
        resets = Resets(480)
        resets.due("p", 0)
        result = resets.due("p", 1000 * DAY_MS)
        self.assertEqual(result["granted"], 1)
        self.assertEqual(result["missed"], 999)
        self.assertEqual(resets.steps_count(), 1)

    def test_step_count_independent_of_days_spanned(self):
        costs = []
        for span in (1, 2, 10, 1000, 3652):
            resets = Resets(480)
            resets.due("p", 0)
            resets.due("p", span * DAY_MS)
            costs.append(resets.steps_count())
        self.assertEqual(costs, [1] * len(costs))

    def test_same_day_repeat_adds_no_steps(self):
        resets = Resets(480)
        resets.due("p", 0)
        for _ in range(100):
            resets.due("p", 1000)
        self.assertEqual(resets.steps_count(), 0)

    def test_missed_equals_service_day_difference_minus_one(self):
        resets = Resets(480)
        resets.due("p", 0)
        for n in (1, 2, 30, 366):
            before = resets.state["p"]["day"]
            result = resets.due("p", before * DAY_MS + n * DAY_MS + 1)
            after = resets.state["p"]["day"]
            self.assertEqual(result["missed"], after - before - 1)


class ScaleTest(unittest.TestCase):
    def test_100k_players_ten_year_span_is_linear(self):
        resets = Resets(480)
        players = 100000
        span_days = 3652
        for index in range(players):
            player = "p-%d" % index
            resets.due(player, 0)
            resets.due(player, span_days * DAY_MS)
        self.assertEqual(resets.steps_count(), players)
        self.assertEqual(len(resets.state), players)


class ReferenceImplTest(unittest.TestCase):
    """200 组随机「玩家 + 结算时刻序列」差分对照独立参考实现。"""

    @staticmethod
    def _reference(tz_offset_min, timestamps):
        offset_ms = tz_offset_min * 60000
        last_day = None
        granted_total = 0
        rows = []
        for now_ms in timestamps:
            day = (now_ms + offset_ms) // DAY_MS
            if last_day is None:
                granted, missed = 1, 0
                last_day = day
            elif day > last_day:
                granted, missed = 1, day - last_day - 1
                last_day = day
            else:
                granted, missed = 0, 0
            granted_total += granted
            rows.append((granted, missed, last_day))
        return rows, granted_total

    def test_random_sequences_match_reference(self):
        rng = random.Random(20260930)
        for _ in range(200):
            tz_offset_min = rng.choice([-720, -600, -480, -60, 0, 60, 480, 600, 720])
            resets = Resets(tz_offset_min)
            base = rng.randrange(-30, 4000) * DAY_MS + rng.randrange(0, DAY_MS)
            timestamps = []
            for _ in range(rng.randrange(1, 12)):
                kind = rng.random()
                if kind < 0.3 and timestamps:
                    timestamps.append(rng.choice(timestamps))
                elif kind < 0.5:
                    timestamps.append(base + rng.randrange(0, 40) * DAY_MS +
                                      rng.randrange(-DAY_MS, DAY_MS))
                else:
                    timestamps.append(base + rng.randrange(0, 3652) * DAY_MS +
                                      rng.randrange(0, DAY_MS))
            expected_rows, expected_total = self._reference(tz_offset_min, timestamps)
            player = "p"
            for now_ms, (granted, missed, day) in zip(timestamps, expected_rows):
                result = resets.due(player, now_ms)
                self.assertEqual(result["granted"], granted, (tz_offset_min, timestamps, now_ms))
                self.assertEqual(result["missed"], missed, (tz_offset_min, timestamps, now_ms))
                self.assertEqual(resets.state[player]["day"], day,
                                 (tz_offset_min, timestamps, now_ms))
            self.assertEqual(resets.granted_total(player), expected_total)

    def test_same_sequence_replays_identically(self):
        rng = random.Random(42)
        tz_offset_min = 480
        timestamps = [rng.randrange(0, 3652) * DAY_MS for _ in range(20)]

        def replay():
            resets = Resets(tz_offset_min)
            return [resets.due("p", now_ms) for now_ms in timestamps]

        self.assertEqual(replay(), replay())


if __name__ == "__main__":
    unittest.main()
