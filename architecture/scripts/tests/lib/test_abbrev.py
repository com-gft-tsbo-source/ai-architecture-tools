import unittest

from lib.abbrev import (
    AbbrevCollisionError,
    derive_object_type,
    natural_object_type,
    pad,
    strip_sort_prefix,
    widths_for_level_count,
    widths_target_length,
)


class TestWidthsAndPrefix(unittest.TestCase):
    def test_widths_for_level_count(self):
        self.assertEqual(widths_for_level_count(1), (6,))
        self.assertEqual(widths_for_level_count(2), (3, 3))
        self.assertEqual(widths_for_level_count(3), (2, 2, 2))

    def test_widths_for_level_count_specctl_exception(self):
        # design-specctl.md, "Object Type": width grows with depth for
        # specctl's 4/5-level metagroups instead of staying fixed at 6.
        self.assertEqual(widths_for_level_count(4), (2, 2, 2, 2))
        self.assertEqual(widths_for_level_count(5), (2, 2, 2, 2, 2))

    def test_widths_for_unsupported_level_count(self):
        with self.assertRaises(ValueError):
            widths_for_level_count(6)

    def test_widths_target_length(self):
        self.assertEqual(widths_target_length(3), 6)
        self.assertEqual(widths_target_length(4), 8)
        self.assertEqual(widths_target_length(5), 10)

    def test_widths_for_level_count_zero(self):
        # design-taskctl.md/design-questctl.md, both "Object Type": a
        # depth-0 store (no metagroup in use at all) has no letters to take
        # from anywhere, but the table entry still exists so the generic
        # derivation machinery doesn't need a special case for it.
        self.assertEqual(widths_for_level_count(0), ())

    def test_widths_target_length_zero_still_pads_to_six(self):
        self.assertEqual(widths_target_length(0), 6)

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


class TestFourAndFiveLevels(unittest.TestCase):
    """specctl's exception: width grows with depth (design-specctl.md,
    "Object Type") instead of staying fixed at 6."""

    def test_natural_four_levels(self):
        result = natural_object_type(["Part", "Chapter", "Section", "Subsection"])
        self.assertEqual(result, "PaChSeSu")
        self.assertEqual(len(result), 8)

    def test_natural_five_levels(self):
        result = natural_object_type(["Part", "Chapter", "Section", "Subsection", "Point"])
        self.assertEqual(result, "PaChSeSuPo")
        self.assertEqual(len(result), 10)

    def test_short_name_at_one_level_only_pads_the_overall_result(self):
        # Only the final joined string is padded to the target length -- a
        # short individual level's shortfall is not padded per-level, same
        # as the existing 1-3 level behavior (natural_object_type(["Go"])).
        result = natural_object_type(["P", "Chapter", "Section", "Subsection", "Point"])
        self.assertEqual(result, "PChSeSuPo_")
        self.assertEqual(len(result), 10)

    def test_five_level_collision_with_identical_names_forces_suffix(self):
        # All 5 level names identical between the two paths -> no level can
        # be resolved by the anchor+divergent-character rule (divergent_index
        # is None for a name that's a prefix of/identical to the colliding
        # one), so this escalates to width-extension, same as the existing
        # 1-3 level "identical source names" case.
        known = {"PaChSeSuPo": ("Part", "Chapter", "Section", "Subsection", "Point")}
        result = derive_object_type(
            ["Part", "Chapter", "Section", "Subsection", "Points"], known=known
        )
        self.assertNotIn(result, known)
        self.assertGreater(len(result), 10)
        self.assertTrue(result.startswith("Pa") or result.startswith("Par"))

    def test_explicit_abbrev_five_levels_padded_to_ten(self):
        result = derive_object_type(
            ["Part", "Chapter", "Section", "Subsection", "Point"], known={}, abbrev="pt"
        )
        self.assertEqual(result, "pt" + "_" * 8)
        self.assertEqual(len(result), 10)


class TestZeroLevels(unittest.TestCase):
    """design-taskctl.md/design-questctl.md, both "Object Type": a
    variable-depth store fixed at depth 0 has every object derive to the
    same, all-underscore code -- the existing padding rule applied to the
    empty case, not a new sentinel constant."""

    def test_natural_object_type_empty(self):
        self.assertEqual(natural_object_type([]), "______")

    def test_derive_object_type_empty(self):
        self.assertEqual(derive_object_type([], known={}), "______")

    def test_cannot_collide_with_a_real_group_name(self):
        # A real Group/Subgroup Name is never empty, so no derived code can
        # ever equal the depth-0 sentinel -- no collision handling needed.
        known = {"______": ("SomeName",)}  # contrived: pretend it did collide
        with self.assertRaises(AbbrevCollisionError):
            # abbrev override colliding with a *pre-existing* "______" still
            # goes through the normal collision path, confirming the code
            # participates in collision detection like any other -- it just
            # never naturally arises from a real (non-empty) level name.
            derive_object_type([], known=known, abbrev="______")


if __name__ == "__main__":
    unittest.main()
