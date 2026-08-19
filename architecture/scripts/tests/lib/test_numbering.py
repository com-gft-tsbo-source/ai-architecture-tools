import unittest

from lib.numbering import next_number, plan_reorder


class TestNextNumber(unittest.TestCase):
    def test_empty_starts_at_one(self):
        self.assertEqual(next_number([]), 1)

    def test_max_plus_one(self):
        self.assertEqual(next_number([1, 2, 5]), 6)

    def test_ignores_gaps(self):
        self.assertEqual(next_number([1, 5]), 6)


class TestPlanReorder(unittest.TestCase):
    def test_move_to_end(self):
        plan = plan_reorder(sibling_numbers=[1, 2, 3], moving_number=1, insert_after=3)
        self.assertEqual(plan.moving_number_after, 4)
        self.assertEqual(plan.shifts, ())

    def test_move_to_beginning_no_siblings(self):
        plan = plan_reorder(sibling_numbers=[5], moving_number=5, insert_after=0)
        self.assertEqual(plan.moving_number_after, 1)
        self.assertEqual(plan.shifts, ())

    def test_reuses_existing_gap(self):
        # siblings 1,2,3,5 (gap at 4); moving object currently 6, inserted after 3.
        plan = plan_reorder(sibling_numbers=[1, 2, 3, 5, 6], moving_number=6, insert_after=3)
        self.assertEqual(plan.moving_number_after, 4)
        self.assertEqual(plan.shifts, ())

    def test_cascade_stops_at_first_gap(self):
        # siblings 1,2,3,5,6 (gap at 4); moving object 7, insert at very start.
        plan = plan_reorder(sibling_numbers=[1, 2, 3, 5, 6, 7], moving_number=7, insert_after=0)
        self.assertEqual(plan.moving_number_after, 1)
        # 1->2, 2->3, 3->4 (stops before the pre-existing gap at 4); 5,6 untouched.
        self.assertEqual(plan.shifts, ((3, 4), (2, 3), (1, 2)))

    def test_full_cascade_when_no_gap_exists(self):
        plan = plan_reorder(sibling_numbers=[1, 2, 3, 4], moving_number=4, insert_after=0)
        self.assertEqual(plan.moving_number_after, 1)
        self.assertEqual(plan.shifts, ((3, 4), (2, 3), (1, 2)))

    def test_move_by_exactly_one_position(self):
        plan = plan_reorder(sibling_numbers=[1, 2, 3], moving_number=1, insert_after=2)
        self.assertEqual(plan.moving_number_after, 3)
        self.assertEqual(plan.shifts, ((3, 4),))

    def test_invalid_insert_after_raises(self):
        with self.assertRaises(ValueError):
            plan_reorder(sibling_numbers=[1, 2, 3], moving_number=1, insert_after=99)

    def test_noop_property(self):
        plan = plan_reorder(sibling_numbers=[1, 2, 3], moving_number=1, insert_after=3)
        self.assertFalse(plan.is_noop)


if __name__ == "__main__":
    unittest.main()
