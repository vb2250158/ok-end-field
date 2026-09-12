from src.data.FeatureList import FeatureList as fL
from src.data.world_map import areas_list


class DailyLogisticsMixin:
    def blind_spot_speed_up(self, feature, box=None, time_out=12, click_interval=0.05):
        """装货过场动画期间快速连点屏幕中心，直到目标按钮出现。

        Args:
            feature: 目标按钮特征名。
            box: 特征识别区域。
            time_out: 总超时时间。
            click_interval: 每次连点后的等待间隔。

        Returns:
            bool: 找到目标按钮返回 True，超时返回 False。
        """
        start_time = self.active_time()
        while True:
            if self.active_time() - start_time > time_out:
                self.log_info(self.tr("盲点加速超时，未找到 {feature}").format(feature=feature))
                return False
            if self.find_feature(feature=feature, box=box):
                return True
            self.click(x=0.5, y=0.5, down_time=0.01)
            self.sleep(click_interval)

    def claim_mail(self):
        self.info_set("current_task", "claim_delivery_rewards")
        self.log_info("开始收邮件")
        self.press_key("k")
        if not self.wait_click_ocr(
            x=0,
            y=0.88,
            to_x=0.25,
            to_y=0.95,
            match=self.lang.daily_routine_mixin.k_ffb5655a,
            time_out=5,
        ):
            self.log_info("未识别到领取按钮，直接退出收邮件")
            self.press_key("esc")
            return True
        self.wait_pop_up()
        stage_area = (
            self.wait_ocr(
                match=self.lang.daily_routine_mixin.k_4a2ece6a,
                box=self.box.top_left,
                time_out=4,
                raise_if_not_found=False,
            )
            or []
        )
        if len(stage_area) > 0:
            self.click(x=stage_area[0].x, y=stage_area[0].y + int(self.height * 0.25))
            self.wait_click_ocr(match=self.lang.daily_routine_mixin.k_3fef35d6, box=self.box.center, time_out=5)
            self.wait_pop_up()
        self.press_key("esc")
        return True

    def _claim_delivery_rewards_in_current_node(self):
        """在已进入的仓储节点中领取一次转交委托奖励。

        仓储节点内的「我转交的委托」「一键领取」「本地仓储节点」等
        均为同一级页面（上有分类、下有页面的界面），无需返回总览。

        Returns:
            bool: 领取流程到达完成状态返回 True（已领取或确认无奖励）；
                  未找到节点或确认失败返回 False，
                  便于调用方在后续地区重试。
        """
        self.log_info("开始领取转交委托奖励")
        if not self.wait_click_ocr(match=self.lang.daily_routine_mixin.k_41a9fd98, box=self.box.top_left, time_out=5):
            self.log_info("未找到「我转交的委托」节点，跳过领取")
            return False

        results = self.wait_ocr(
            match=self.lang.daily_routine_mixin.k_bf856c96,
            box=self.box.bottom_right,
            time_out=5,
        )

        if not results:
            # 已进入节点且确认无奖励，视为该节点的领取流程完成。
            self.log_info("当前没有可领取的转交委托奖励")
            return True

        self.click(results)
        if not self.wait_pop_up():
            self.log_info("未找到 '确认' 按钮，可能未成功领取奖励")
            return False

        # 返回仓储节点总览，让后续转交委托复用已经完成的地区导航。
        self.log_info("转交委托奖励领取完成")
        return True

    def _select_delivery_activity(self, results):
        """从「货物装箱 / 查看报价」候选中选出本次要点击的目标与起始步骤。

        节点会同时给出两类入口：
        - 「货物装箱」是完整装箱流程的入口，后续从 steps[0] 开始；
        - 「查看报价」表示货物已装箱、只剩交付，后续从 steps[2] 开始。

        原实现固定取 results[0]，但 OCR 的返回顺序并不保证把「货物装箱」排在
        前面。一旦 results[0] 命中「查看报价」，就会进入 start_index=2 的交付
        分支，而报价界面上并不存在 steps[2] 要点的 give_gift 按钮，于是
        「步骤 give_gift 未找到」→ 放弃本次活动 → send_count 恒为 0 →
        整个转交运送委托被记为失败。这里改为优先选非「查看报价」的装箱入口。

        Args:
            results: wait_ocr 返回的候选列表，调用方已保证至少一项。

        Returns:
            tuple: (候选对象, 起始步骤下标)。
        """
        for item in results:
            if self.lang.daily_routine_mixin.k_view_quote not in item.name:
                return item, 0
        return results[0], 2

    def delivery_send_others(self):
        self.info_set("current_task", "delivery_send_others")

        send_count = 0
        claim_rewards_done = False
        # 本地区是否出现过可转交活动；用于区分「今天没事可做」与「有事但都失败」。
        activity_seen = False

        for area in areas_list:
            activity_num = 0
            count = 0
            self.log_info(self.tr("开始处理区域: {area}").format(area=self.tr(area)))

            while True:
                if 0 < activity_num <= count:
                    self.log_info(
                        self.tr("{area}仓储节点已完成{count}次，停止继续").format(
                            area=self.tr(area), count=activity_num
                        )
                    )
                    break

                self.to_model_area(area, "仓储节点")

                if not claim_rewards_done:
                    # 仅在领取流程真正完成时才置位，失败留到后续地区重试。
                    if self._claim_delivery_rewards_in_current_node():
                        claim_rewards_done = True

                if not self.wait_click_ocr(
                    match=self.lang.daily_routine_mixin.k_298d3284, box=self.box.top_left, time_out=5
                ):
                    self.log_info(self.tr("{area}未找到本地仓储节点，返回主界面").format(area=self.tr(area)))
                    self.ensure_main()
                    break

                results = self.wait_ocr(
                    match=[self.lang.daily_routine_mixin.k_573c7c18, self.lang.daily_routine_mixin.k_8f2058a8],
                    box=self.box.bottom,
                    time_out=5,
                )

                if not results:
                    self.log_info(self.tr("{area} 当前没有货物装箱可操作，返回主界面").format(area=self.tr(area)))
                    self.ensure_main()
                    break

                activity_seen = True

                if activity_num == 0:
                    activity_num = len(results)
                    self.log_info(
                        self.tr("{area}共有{activity_num}次可进行转交运送委托的活动").format(
                            area=self.tr(area), activity_num=activity_num
                        ),
                        notify=True,
                    )

                activity, start_index = self._select_delivery_activity(results)
                self.log_info(
                    f"转交诊断: 候选={[item.name for item in results]} 选中={activity.name} 起始步骤={start_index}"
                )
                self.click(activity)
                steps = [
                    (fL.give_gift, self.box_of_screen(0.945, 0.904, 0.965, 0.937), 0),
                    (fL.fill_max, None, 0),
                    (fL.give_gift, self.box_of_screen(0.945, 0.904, 0.965, 0.937), 1),
                    (fL.give_gift, self.box_of_screen(0.945, 0.904, 0.965, 0.937), 0),
                    (fL.esc, None, 0),
                ]
                optional_steps = {3}
                blind_spot_steps = {3, 4}

                for i in range(start_index, len(steps)):
                    step = steps[i]
                    feature = step[0]
                    box = step[1]
                    after_sleep = step[2]
                    time_out = 12 if i > 2 else 5
                    if i in blind_spot_steps:
                        self.log_info("盲点加速：装货过场动画期间快速连点屏幕中心")
                        if not self.blind_spot_speed_up(feature=feature, box=box, time_out=time_out):
                            if i in optional_steps:
                                continue
                            self.log_info(f"步骤 {feature} 未找到，跳过本次活动")
                            self.log_info(
                                f"转交诊断: 第 {i} 步 {feature} 未找到（起始步骤={start_index}，选中={activity.name}）"
                            )
                            break
                        if i == len(steps) - 1:
                            continue
                    res = self.wait_click_feature(
                        feature=feature,
                        click_after_delay=0.5,
                        box=box,
                        time_out=time_out,
                        raise_if_not_found=False,
                        after_sleep=after_sleep,
                    )

                    if not res:
                        if i in optional_steps:
                            continue

                        self.log_info(self.tr("步骤 {feature} 未找到，跳过本次活动").format(feature=feature))
                        self.log_info(
                            f"转交诊断: 第 {i} 步 {feature} 未找到（起始步骤={start_index}，选中={activity.name}）"
                        )
                        break
                self.ensure_main()
                self.press_key("j", after_sleep=1)

                if not self.wait_click_ocr(
                    match=self.lang.daily_routine_mixin.k_1dd73947, box=self.box.bottom_left, time_out=5
                ):
                    self.log_info("未找到 '转交运送委托' 按钮，跳过本次活动")
                    self.ensure_main()
                    break
                if not self.click_confirm():
                    self.log_info("未找到 '确认' 按钮，跳过本次活动")
                    self.ensure_main()
                    break
                count += 1
                send_count += 1
                self.log_info(f"{area} 已完成 {count}/{activity_num} 次转交")
        if send_count == 0:
            if not activity_seen:
                # 今天没有任何可转交的运送委托（当天已完成、或地区尚未接入送货网络）。
                # 这属于「无事可做」，不应记为任务失败拖垮整轮。
                self.log_info("今天没有可转交的运送委托，视为已完成")
                return True
            self.mark_task_failure("未完成任何转交运送委托操作")
            return False
        return True
