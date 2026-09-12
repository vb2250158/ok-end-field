import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.tasks.daily.misc.daily_logistics_mixin import DailyLogisticsMixin


class TestSelectDeliveryActivity(unittest.TestCase):
    """_select_delivery_activity 优先选「货物装箱」，只在没有装箱入口时才退回「查看报价」。

    节点同时给出两类入口时固定取 results[0]，一旦命中「查看报价」就会进入
    start_index=2 的交付分支，而报价界面上没有 steps[2] 要点的 give_gift 按钮，
    于是每次转交都失败、send_count 恒为 0。
    """

    def make_feature(self):
        feature = object.__new__(DailyLogisticsMixin)
        feature.log_info = Mock()
        feature.lang = SimpleNamespace(
            daily_routine_mixin=SimpleNamespace(k_view_quote="查看报价")
        )
        return feature

    def test_prefers_pack_entry_when_quote_comes_first(self):
        feature = self.make_feature()
        quote = SimpleNamespace(name="查看报价")
        pack = SimpleNamespace(name="货物装箱")

        activity, start_index = feature._select_delivery_activity([quote, pack])

        self.assertIs(activity, pack)
        self.assertEqual(start_index, 0)

    def test_prefers_pack_entry_when_pack_comes_first(self):
        feature = self.make_feature()
        pack = SimpleNamespace(name="货物装箱")
        quote = SimpleNamespace(name="查看报价")

        activity, start_index = feature._select_delivery_activity([pack, quote])

        self.assertIs(activity, pack)
        self.assertEqual(start_index, 0)

    def test_falls_back_to_quote_when_only_quote_offered(self):
        feature = self.make_feature()
        quote = SimpleNamespace(name="查看报价")

        activity, start_index = feature._select_delivery_activity([quote])

        self.assertIs(activity, quote)
        self.assertEqual(start_index, 2)


class TestDeliverySendOthersNoActivity(unittest.TestCase):
    """转交运送委托区分「今天没事可做」与「有事但都失败」。"""

    def make_send_feature(self, ocr_results, step_found=True, panel_found=False):
        feature = object.__new__(DailyLogisticsMixin)
        feature.info_set = Mock()
        feature.log_info = Mock()
        feature.tr = lambda message, **kwargs: message
        feature.mark_task_failure = Mock()
        feature.to_model_area = Mock(return_value=True)
        feature.ensure_main = Mock()
        feature.press_key = Mock()
        feature.click = Mock()
        feature.click_confirm = Mock(return_value=True)
        feature.blind_spot_speed_up = Mock(return_value=True)
        feature.wait_click_feature = Mock(return_value=step_found)
        feature.box_of_screen = Mock(return_value=object())
        feature.box = SimpleNamespace(top_left=object(), bottom=object(), bottom_left=object())
        feature.lang = SimpleNamespace(
            daily_routine_mixin=SimpleNamespace(
                k_view_quote="查看报价",
                k_298d3284="本地仓储节点",
                k_573c7c18="货物装箱",
                k_8f2058a8="查看报价",
                k_1dd73947="转交运送委托",
            )
        )
        feature._claim_delivery_rewards_in_current_node = Mock(return_value=True)
        # 「本地仓储节点」总能找到；任务面板里的「转交运送委托」按钮是否可点由 panel_found 决定。
        tracked = ("本地仓储节点", "转交运送委托") if panel_found else ("本地仓储节点",)
        feature.wait_click_ocr = Mock(side_effect=lambda match=None, **kwargs: match in tracked)
        feature.wait_ocr = Mock(return_value=ocr_results)
        return feature

    def run_send_others(self, feature):
        with patch(
            "src.tasks.daily.misc.daily_logistics_mixin.areas_list",
            ["武陵", "试验园区"],
        ):
            return feature.delivery_send_others()

    def test_no_activity_anywhere_is_a_noop_success(self):
        feature = self.make_send_feature([])
        result = self.run_send_others(feature)

        self.assertTrue(result)
        feature.mark_task_failure.assert_not_called()

    def test_activity_present_but_not_handed_over_still_fails(self):
        feature = self.make_send_feature([SimpleNamespace(name="货物装箱")], step_found=False)
        result = self.run_send_others(feature)

        self.assertFalse(result)
        feature.mark_task_failure.assert_called_once()

    def test_activity_handed_over_succeeds(self):
        feature = self.make_send_feature(
            [SimpleNamespace(name="查看报价"), SimpleNamespace(name="货物装箱")], panel_found=True
        )
        result = self.run_send_others(feature)

        self.assertTrue(result)
        feature.mark_task_failure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
