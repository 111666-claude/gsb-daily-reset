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


if __name__ == "__main__":
    unittest.main()


import calendar
import random
from datetime import date

from dailyreset.core import MINUTE_MS


class ServiceDayTimezoneTest(unittest.TestCase):
    def test_positive_offset_rolls_over_before_utc_midnight(self):
        resets = Resets(480)
        self.assertEqual(resets.service_day(57600000 - 1), 0)
        self.assertEqual(resets.service_day(57600000), 1)

    def test_negative_offset_rolls_over_after_utc_midnight(self):
        resets = Resets(-480)
        self.assertEqual(resets.service_day(8 * 3600000 - 1), -1)
        self.assertEqual(resets.service_day(8 * 3600000), 0)

    def test_non_hour_offset_uses_floor(self):
        resets = Resets(330)
        boundary = DAY_MS - 330 * MINUTE_MS
        self.assertEqual(resets.service_day(boundary - 1), 0)
        self.assertEqual(resets.service_day(boundary), 1)

    def test_boundary_is_independent_of_utc_day(self):
        resets = Resets(480)
        self.assertEqual(resets.service_day(DAY_MS - 1), 1)
        self.assertEqual(resets.service_day(DAY_MS), 1)


class IdempotentDueTest(unittest.TestCase):
    def test_same_day_second_call_grants_nothing(self):
        resets = Resets(480)
        self.assertEqual(resets.due("p", 1000), {"granted": 1, "missed": 0})
        self.assertEqual(resets.due("p", 2000), {"granted": 0, "missed": 0})
        self.assertEqual(resets.granted_total("p"), 1)
        self.assertEqual(resets.steps_count(), 0)

    def test_grant_only_on_first_settlement_of_new_day(self):
        resets = Resets(480)
        resets.due("p", 0)
        self.assertEqual(resets.due("p", 2 * DAY_MS)["granted"], 1)
        self.assertEqual(resets.due("p", 2 * DAY_MS + 1000)["granted"], 0)

    def test_backward_call_is_idempotent(self):
        resets = Resets(480)
        resets.due("p", 5 * DAY_MS)
        self.assertEqual(resets.due("p", 0), {"granted": 0, "missed": 0})
        self.assertEqual(resets.granted_total("p"), 1)

    def test_players_are_independent(self):
        resets = Resets(480)
        resets.due("a", 0)
        resets.due("b", 0)
        resets.due("a", 3 * DAY_MS)
        self.assertEqual(resets.due("b", 3 * DAY_MS), {"granted": 1, "missed": 2})
        self.assertEqual(resets.granted_total("a"), 2)
        self.assertEqual(resets.granted_total("b"), 2)


class CatchupDueTest(unittest.TestCase):
    def test_cross_n_days_grants_one_and_misses_n_minus_one(self):
        for gap in (2, 3, 10, 365, 3653):
            resets = Resets(480)
            resets.due("p", 0)
            result = resets.due("p", gap * DAY_MS)
            day0 = resets.service_day(0)
            day1 = resets.service_day(gap * DAY_MS)
            self.assertEqual(result["granted"], 1)
            self.assertEqual(result["missed"], day1 - day0 - 1)

    def test_catchup_cost_is_one_step_regardless_of_days(self):
        resets = Resets(480)
        resets.due("p", 0)
        result = resets.due("p", 10 * 365 * DAY_MS)
        self.assertGreaterEqual(result["missed"], 3000)
        self.assertEqual(resets.steps_count(), 1)

    def test_missed_equals_service_day_difference_minus_one(self):
        resets = Resets(480)
        resets.due("p", 2 * MINUTE_MS)
        result = resets.due("p", 30 * DAY_MS + 7 * MINUTE_MS)
        diff = resets.service_day(30 * DAY_MS + 7 * MINUTE_MS) - resets.service_day(2 * MINUTE_MS)
        self.assertEqual(result["missed"], diff - 1)

    def test_settlement_sequence_is_replayable(self):
        resets_a = Resets(330)
        resets_b = Resets(330)
        times = [0, 1000, DAY_MS, DAY_MS, 2 * DAY_MS, 2 * DAY_MS, 40 * DAY_MS]
        results_a = [resets_a.due("p", t) for t in times]
        results_b = [resets_b.due("p", t) for t in times]
        self.assertEqual(results_a, results_b)
        self.assertEqual(resets_a.state, resets_b.state)
        self.assertEqual(resets_a.steps_count(), resets_b.steps_count())


class ScaleTest(unittest.TestCase):
    def test_hundred_thousand_players_ten_year_catchup(self):
        resets = Resets(480)
        player_count = 100000
        now_ms = 10 * 365 * DAY_MS
        sample_result = None
        for index in range(player_count):
            player = "p-%d" % index
            resets.due(player, 0)
            sample_result = resets.due(player, now_ms)
        self.assertEqual(resets.steps_count(), player_count)
        self.assertEqual(len(resets.state), player_count)
        day0 = resets.service_day(0)
        day1 = resets.service_day(now_ms)
        self.assertEqual(sample_result, {"granted": 1, "missed": day1 - day0 - 1})
        for player in ("p-0", "p-4242", "p-99999"):
            self.assertEqual(resets.granted_total(player), 2)
            self.assertEqual(resets.state[player]["day"], day1)


EPOCH_ORD = date(1970, 1, 1).toordinal()
TZ_OFFSETS = (-720, -480, -330, -60, 0, 60, 330, 480, 540, 720)


def _reference_service_day(now_ms, tz_offset_min):
    return (now_ms + tz_offset_min * MINUTE_MS) // DAY_MS


class ReferenceResets:
    """参考实现：时区日界 + 算术跳跃 + 幂等，独立于 core 写出。"""

    def __init__(self, tz_offset_min):
        self.tz_offset_min = tz_offset_min
        self.records = {}
        self.steps = 0

    def due(self, player, now_ms):
        day = _reference_service_day(now_ms, self.tz_offset_min)
        record = self.records.get(player)
        if record is None:
            self.records[player] = [day, 1]
            return {"granted": 1, "missed": 0}
        last_day, granted_total = record
        if day <= last_day:
            return {"granted": 0, "missed": 0}
        result = {"granted": 1, "missed": day - last_day - 1}
        record[0] = day
        record[1] = granted_total + 1
        self.steps += 1
        return result


def _local_midnight_ms(year, month, day, tz_offset_min):
    day_index = date(year, month, day).toordinal() - EPOCH_ORD
    return day_index * DAY_MS - tz_offset_min * MINUTE_MS


def _make_group(rng):
    tz_offset_min = rng.choice(TZ_OFFSETS)
    players = ["p%d" % i for i in range(rng.randint(1, 4))]
    dates = [(2019, 12, 31), (2020, 1, 1), (2020, 2, 28), (2020, 2, 29),
             (2020, 3, 1), (2023, 12, 31), (2024, 1, 1), (1970, 1, 1)]
    for _ in range(rng.randint(2, 5)):
        year = rng.randint(1970, 2039)
        month = rng.randint(1, 12)
        dates.append((year, month, rng.randint(1, calendar.monthrange(year, month)[1])))
    events = []
    for year, month, day in dates:
        midnight = _local_midnight_ms(year, month, day, tz_offset_min)
        delta = rng.choice([-1, 0, 1, -MINUTE_MS, MINUTE_MS,
                            rng.randint(-DAY_MS, DAY_MS)])
        events.append((rng.choice(players), midnight + delta))
    if rng.random() < 0.5:
        events.append((rng.choice(players), 10 * 365 * DAY_MS))
    events.sort(key=lambda event: event[1])
    sequenced = []
    for event in events:
        sequenced.append(event)
        if rng.random() < 0.4:
            sequenced.append(event)
    return tz_offset_min, sequenced


class ReferenceDifferentialTest(unittest.TestCase):
    def test_200_random_groups_match_reference(self):
        rng = random.Random(20240930)
        for _ in range(200):
            tz_offset_min, events = _make_group(rng)
            actual = Resets(tz_offset_min)
            reference = ReferenceResets(tz_offset_min)
            first_results = []
            for player, now_ms in events:
                reference_result = reference.due(player, now_ms)
                first_results.append(reference_result)
                self.assertEqual(actual.due(player, now_ms), reference_result)
                self.assertEqual(actual.service_day(now_ms),
                                 _reference_service_day(now_ms, tz_offset_min))
            self.assertEqual(actual.steps_count(), reference.steps)
            # 同一串结算序列重复执行结果相同。
            replayed = Resets(tz_offset_min)
            self.assertEqual(
                [replayed.due(player, now_ms) for player, now_ms in events],
                first_results)
            self.assertEqual(replayed.steps_count(), reference.steps)
            # 同一时刻序列对已结算台账再来一遍，全部 granted=0。
            self.assertEqual(
                [actual.due(player, now_ms) for player, now_ms in events],
                [{"granted": 0, "missed": 0}] * len(events))
            self.assertEqual(
                [actual.granted_total(player) for player in reference.records],
                [total for _, total in reference.records.values()])
