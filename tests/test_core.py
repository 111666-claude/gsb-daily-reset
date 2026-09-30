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
