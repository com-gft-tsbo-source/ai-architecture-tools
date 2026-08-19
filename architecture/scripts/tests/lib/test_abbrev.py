import unittest

from lib.abbrev import (
    AbbrevCollisionError,
    derive_object_type,
    natural_object_type,
    pad,
    strip_sort_prefix,
    widths_for_level_count,
)


class TestWidthsAndPrefix(unittest.TestCase):
    def test_widths_for_level_count(self):
        self.assertEqual(widths_for_level_count(1), (6,))
        self.assertEqual(widths_for_level_count(2), (3, 3))
        self.assertEqual(widths_for_level_count(3), (2, 2, 2))

    def test_widths_for_unsupported_level_count(self):
        with self.assertRaises(ValueError):
            widths_for_level_count(4)

    def test_strip_sort_prefix(self):
        self.assertEqual(strip_sort_prefix("002-Implementation"), "Implementation")
        self.assertEqual(strip_sort_prefix("NoPrefix"), "NoPrefix")


class TestPad(unittest.TestCase):
    def test_pads_short_letters(self):
        self.assertEqual(pad("Go"), "Go____")

    def test_leaves_target_length_untouched(self):
        self.assertEqual(pad("Python"), "Python")

    def test_leaves_longer_than_target_untouched(self):
        self.assertEqual(pad("Abcdefgh"), "Abcdefgh")


class TestNaturalObjectType(unittest.TestCase):
    def test_single_level(self):
        self.assertEqual(natural_object_type(["Python"]), "Python")

    def test_single_level_short_name_padded(self):
        self.assertEqual(natural_object_type(["Go"]), "Go____")

    def test_two_levels(self):
        self.assertEqual(natural_object_type(["backend", "login"]), "baclog")

    def test_three_levels(self):
        self.assertEqual(natural_object_type(["Python", "backend", "validation"]), "Pybava")

    def test_strips_sort_prefix_before_deriving(self):
        self.assertEqual(natural_object_type(["001-Setup"]), "Setup_")


class TestDeriveObjectType(unittest.TestCase):
    def test_no_collision_returns_natural(self):
        result = derive_object_type(["Python"], known={})
        self.assertEqual(result, "Python")

    def test_design_doc_collision_example(self):
        # backend/login -> baclog (already assigned); adding backend/logik
        # must resolve to baclog -> baclok per design-decisions.md.
        known = {"baclog": ("backend", "login")}
        result = derive_object_type(["backend", "logik"], known=known)
        self.assertEqual(result, "baclok")

    def test_non_colliding_level_left_unchanged(self):
        known = {"baclog": ("backend", "login")}
        result = derive_object_type(["backend", "logik"], known=known)
        self.assertTrue(result.startswith("bac"))

    def test_explicit_abbrev_used_verbatim_and_padded(self):
        result = derive_object_type(["backend", "login"], known={}, abbrev="x")
        self.assertEqual(result, "x_____")

    def test_explicit_abbrev_colliding_raises(self):
        known = {"custom": ("whatever",)}
        with self.assertRaises(AbbrevCollisionError):
            derive_object_type(["backend", "login"], known=known, abbrev="custom")

    def test_width_extension_when_substitution_still_collides(self):
        # Natural + single-substitution both pre-occupied by other entries ->
        # must escalate to a wider (unpadded) window.
        known = {
            "Abcdef": ("AbcdefZZ",),
            "Abcdem": ("AbcdemZZ",),
        }
        result = derive_object_type(["Abcdefmnopqrst"], known=known)
        self.assertNotIn(result, known)
        self.assertTrue(result.startswith("Abcdef"))
        self.assertGreater(len(result), 6)

    def test_numeric_suffix_when_width_extension_exhausted(self):
        known = {
            "Abcdef": ("AbcdefZZ",),
            "Abcdem": ("AbcdemZZ",),
            "Abcdefm": ("dummy",),
            "Abcdefmn": ("dummy",),
            "Abcdefmno": ("dummy",),
        }
        result = derive_object_type(["Abcdefmnopqrst"], known=known)
        self.assertEqual(result, "Abcdem-2")

    def test_identical_source_names_cannot_substitute_forces_suffix(self):
        known = {"Python": ("Python",)}
        result = derive_object_type(["Python"], known=known)
        self.assertEqual(result, "Python-2")

    def test_full_exhaustion_raises_collision_error(self):
        known = {"Abcdef": ("AbcdefZZ",), "Abcdem": ("AbcdemZZ",)}
        for extra_width in range(7, 10):
            known[f"Abcdefmnopqrst"[:extra_width]] = ("dummy",)
        for suffix in range(2, 100):
            known[f"Abcdem-{suffix}"] = ("dummy",)
        with self.assertRaises(AbbrevCollisionError):
            derive_object_type(["Abcdefmnopqrst"], known=known)


if __name__ == "__main__":
    unittest.main()
