"""
图表生成专用日志模块
提供详细的步骤追踪和性能监控
"""

import time
from datetime import datetime
from logger import logger


class ChartGenerationLogger:
    """图表生成日志记录器"""

    def __init__(self, symbol):
        self.symbol = symbol
        self.start_time = time.time()
        self.steps = []
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

    def log_start(self):
        """记录开始"""
        logger.info(f"[图表生成 {self.session_id}] 开始生成 ${self.symbol} 的图表")
        self.steps.append(('start', time.time()))

    def log_step(self, step_name, success=True, details=None):
        """记录步骤"""
        elapsed = time.time() - self.start_time
        status = "✅" if success else "❌"

        msg = f"[图表生成 {self.session_id}] {status} {step_name} (耗时: {elapsed:.2f}s)"
        if details:
            msg += f" - {details}"

        if success:
            logger.info(msg)
        else:
            logger.error(msg)

        self.steps.append((step_name, time.time(), success, details))

    def log_data_fetch(self, data_source, success, data_size=None, error=None):
        """记录数据获取"""
        details = None
        if success and data_size is not None:
            details = f"获取 {data_size} 条数据"
        elif not success and error:
            details = f"错误: {error}"

        self.log_step(f"获取{data_source}数据", success, details)

    def log_render(self, component, success, error=None):
        """记录渲染步骤"""
        details = f"错误: {error}" if error else None
        self.log_step(f"渲染{component}", success, details)

    def log_complete(self, chart_size=None):
        """记录完成"""
        total_time = time.time() - self.start_time

        if chart_size:
            logger.info(
                f"[图表生成 {self.session_id}] ✅ 完成 ${self.symbol} 图表生成 "
                f"(总耗时: {total_time:.2f}s, 大小: {chart_size} bytes)"
            )
        else:
            logger.error(
                f"[图表生成 {self.session_id}] ❌ ${self.symbol} 图表生成失败 "
                f"(总耗时: {total_time:.2f}s)"
            )

    def log_error(self, error_msg, exception=None):
        """记录错误"""
        elapsed = time.time() - self.start_time
        logger.error(
            f"[图表生成 {self.session_id}] ❌ ${self.symbol} 发生错误 "
            f"(耗时: {elapsed:.2f}s): {error_msg}"
        )

        if exception:
            import traceback
            logger.error(f"[图表生成 {self.session_id}] 异常详情:\n{traceback.format_exc()}")

    def get_summary(self):
        """获取执行摘要"""
        total_time = time.time() - self.start_time
        return {
            'symbol': self.symbol,
            'session_id': self.session_id,
            'total_time': total_time,
            'steps': len(self.steps),
            'success': all(s[2] for s in self.steps if len(s) > 2)
        }
