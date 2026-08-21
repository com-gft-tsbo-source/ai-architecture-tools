import unittest

from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec


class TestStatusSpec(unittest.TestCase):
    def test_rejects_initial_status_not_in_codes(self):
        with self.assertRaises(ValueError):
            StatusSpec(codes=("draft", "active"), initial="obsolete")

    def test_accepts_valid_initial_status(self):
        spec = StatusSpec(codes=("draft", "active"), initial="active")
        self.assertEqual(spec.initial, "active")
        self.assertIsNone(spec.transition_validator)


class TestToolSpec(unittest.TestCase):
    def _make(self):
        return ToolSpec(
            name="rulectl",
            metagroup_levels=(
                MetagroupLevelSpec(type="Language"),
                MetagroupLevelSpec(type="Context"),
                MetagroupLevelSpec(type="Category"),
            ),
            metainfo=(
                MetainfoSpec(type="weight"),
                MetainfoSpec(type="checkable", choices=("llm",)),
            ),
            status=StatusSpec(codes=("draft", "active", "obsolete"), initial="active"),
            user_content_blocks=("Description", "Procedure"),
            root_name="rules",
            default_mode="directory",
        )

    def test_metainfo_names(self):
        spec = self._make()
        self.assertEqual(spec.metainfo_names(), ("weight", "checkable"))

    def test_metagroup_level_types(self):
        spec = self._make()
        self.assertEqual(spec.metagroup_level_types(), ("Language", "Context", "Category"))

    def test_defaults(self):
        spec = self._make()
        self.assertIsNone(spec.object_type_fn)

    def test_rejects_invalid_default_mode(self):
        with self.assertRaises(ValueError):
            ToolSpec(
                name="rulectl",
                metagroup_levels=(MetagroupLevelSpec(type="Language"),),
                metainfo=(),
                status=StatusSpec(codes=("active",), initial="active"),
                user_content_blocks=("Description",),
                root_name="rules",
                default_mode="both",
            )


if __name__ == "__main__":
    unittest.main()
