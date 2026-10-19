import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest


def load_method(name="perform_operator_liaison"):
    path = Path(__file__).parents[1] / "src/tasks/mixin/liaison_mixin.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_names = {alias.asname or alias.name for node in tree.body
                      if isinstance(node, ast.Import) for alias in node.names}
    if "re" not in imported_names:
        raise AssertionError("recipient guard requires module-level re import")
    method = next(node for owner in tree.body if isinstance(owner, ast.ClassDef)
                  for node in owner.body if isinstance(node, ast.FunctionDef)
                  and node.name == name)
    namespace = {"get_localized_name_by_canonical": lambda language, name: name,
                 "re": re, "fL": SimpleNamespace(map_filter_icon="filter", give_gift="give")}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[method.name]


class TargetSelected(Exception):
    pass


class Harness:
    def __init__(self, resolved=True, visible=False):
        self.config = {"优先送礼对象": "祀", "仅向优先对象送礼": True}
        self.lang = SimpleNamespace()
        self.can_contact_dict = {"祀": "contact_si", "其他对象": "contact_other"}
        self.contact_name_patterns = {"祀": []}
        self.resolved = resolved
        self.visible = visible
        self.clicked = []

    def _resolve_contact_feature_name(self, name):
        return "contact_si" if self.resolved else None

    def log_info(self, *arguments):
        pass

    def box_of_screen(self, *arguments):
        return object()

    def press_key(self, *arguments):
        pass

    def wait_ui_stable(self, **keywords):
        pass

    def next_frame(self):
        pass

    def find_one(self, **keywords):
        return "selected-si" if self.visible else None

    def scroll_relative(self, *arguments):
        pass

    def ensure_main(self):
        raise AssertionError("fallback was reached")

    def click(self, selected, **keywords):
        self.clicked.append(selected)
        raise TargetSelected()


class TestStrictGiftTarget(unittest.TestCase):
    def test_unknown_target_stops_without_fallback(self):
        self.assertFalse(load_method()(Harness(resolved=False)))

    def test_missing_target_stops_without_other_selection(self):
        self.assertFalse(load_method()(Harness(visible=False)))

    def test_exact_target_remains_selectable(self):
        harness = Harness(visible=True)
        method = load_method()
        method.__globals__["build_name_patterns"] = lambda name: []
        with self.assertRaises(TargetSelected):
            method(harness)
        self.assertEqual(harness.clicked, ["selected-si"])

    def test_wrong_recipient_stops_before_selecting_any_gift(self):
        harness = GiftHarness(recipient="大潘")
        self.assertFalse(load_method("_finish_give_gift_after_clicked")(harness))
        self.assertEqual(harness.selected_count, 0)

    def test_confirmed_recipient_can_reach_gift_confirmation(self):
        harness = GiftHarness(recipient="祀")
        with self.assertRaises(TargetSelected):
            load_method("_finish_give_gift_after_clicked")(harness)
        self.assertEqual(harness.selected_count, 2)


class GiftHarness(Harness):
    def __init__(self, recipient):
        super().__init__()
        self.recipient = recipient
        self.selected_count = 0

    def wait_feature(self, **keywords):
        pass

    def wait_ocr(self, **keywords):
        return [self.recipient] if keywords["match"].fullmatch(self.recipient) else []

    def click(self, *arguments, **keywords):
        self.selected_count += 1

    def wait_click_feature(self, **keywords):
        raise TargetSelected()


if __name__ == "__main__":
    unittest.main()
