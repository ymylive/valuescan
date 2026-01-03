#!/usr/bin/env python3
"""
AI 信号简评队列管理器
确保每条信号都被简评，一个个顺序处理，不会跳过任何信号
"""

import os
import queue
import threading
import time
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field

try:
    from logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _read_int_env_or_config(env_key: str, config_key: str, default: int) -> int:
    raw = os.getenv(env_key)
    if raw is not None and str(raw).strip() != "":
        try:
            return int(float(raw))
        except Exception:
            return default
    try:
        import config as signal_config
        value = getattr(signal_config, config_key, None)
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


_BULLISH_SIGNAL_TYPES = {100, 101, 108, 110, 111}
_BEARISH_SIGNAL_TYPES = {102, 103, 109, 112}
_BULL_BEAR_SIGNAL_TTL_SECONDS = _read_int_env_or_config(
    "VALUESCAN_BULL_BEAR_SIGNAL_TTL_SECONDS",
    "BULL_BEAR_SIGNAL_TTL_SECONDS",
    86400,
)


def _extract_signal_timestamp_ms(signal_payload: Optional[Dict[str, Any]]) -> int:
    if not isinstance(signal_payload, dict):
        return 0
    for key in ("createTime", "createdTime", "create_time", "timestamp", "time", "ts", "msgTime"):
        value = signal_payload.get(key)
        if value is None:
            continue
        try:
            ts = int(float(value))
        except Exception:
            continue
        if ts <= 0:
            continue
        return ts if ts > 10**12 else ts * 1000
    return 0


def _extract_signal_type(signal_payload: Optional[Dict[str, Any]]) -> int:
    if not isinstance(signal_payload, dict):
        return 0
    for key in ("type", "msgType", "messageType", "signalType", "warnType"):
        value = signal_payload.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except Exception:
            continue
    return 0


def _is_bull_bear_signal_expired(signal_payload: Optional[Dict[str, Any]]) -> bool:
    if _BULL_BEAR_SIGNAL_TTL_SECONDS <= 0:
        return False
    msg_type = _extract_signal_type(signal_payload)
    if msg_type not in _BULLISH_SIGNAL_TYPES and msg_type not in _BEARISH_SIGNAL_TYPES:
        return False
    msg_time_ms = _extract_signal_timestamp_ms(signal_payload)
    if not msg_time_ms:
        return False
    age_seconds = (time.time() * 1000 - msg_time_ms) / 1000.0
    return age_seconds > _BULL_BEAR_SIGNAL_TTL_SECONDS


@dataclass
class AISignalTask:
    """AI简评任务"""
    symbol: str
    signal_payload: Optional[Dict[str, Any]] = None
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
    created_at: float = field(default_factory=time.time)
    task_id: str = field(default_factory=lambda: f"{time.time():.6f}")


class AISignalQueue:
    """
    AI信号简评队列管理器
    - 所有信号进入队列排队
    - 单线程顺序处理，确保不跳过任何信号
    - 支持回调通知处理结果
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._queue: queue.Queue[AISignalTask] = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._processing_lock = threading.Lock()
        self._current_task: Optional[AISignalTask] = None
        self._stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_skipped": 0,
        }
        self._initialized = True
        self._start_worker()
        logger.info("[AI队列] 信号队列管理器已初始化")
    
    def _start_worker(self):
        """启动工作线程"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="AISignalQueueWorker",
                daemon=True
            )
            self._worker_thread.start()
            logger.info("[AI队列] 工作线程已启动")
    
    def _worker_loop(self):
        """工作线程主循环"""
        while not self._stop_event.is_set():
            try:
                # 等待任务，超时1秒检查停止信号
                try:
                    task = self._queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                with self._processing_lock:
                    self._current_task = task
                
                try:
                    self._process_task(task)
                    self._stats["total_success"] += 1
                except Exception as e:
                    logger.error(f"[AI队列] 处理任务失败: {task.symbol} - {e}")
                    self._stats["total_failed"] += 1
                finally:
                    self._stats["total_processed"] += 1
                    with self._processing_lock:
                        self._current_task = None
                    self._queue.task_done()
                    
            except Exception as e:
                logger.error(f"[AI队列] 工作线程异常: {e}")
                time.sleep(1)
        
        logger.info("[AI队列] 工作线程已停止")
    
    def _process_task(self, task: AISignalTask):
        """处理单个AI简评任务"""
        symbol = task.symbol
        wait_time = time.time() - task.created_at
        logger.info(f"[AI队列] 开始处理: {symbol} (等待 {wait_time:.1f}s, 队列剩余 {self._queue.qsize()})")
        
        try:
            from ai_signal_analysis import analyze_signal
            result = analyze_signal(symbol, signal_payload=task.signal_payload)
            
            if result and isinstance(result, dict):
                analysis = result.get("analysis", "")
                if analysis:
                    logger.info(f"[AI队列] ✅ 完成: {symbol} - {analysis[:50]}...")
                else:
                    logger.info(f"[AI队列] ⚠️ 完成但无分析: {symbol}")
            else:
                logger.warning(f"[AI队列] ⚠️ 无结果: {symbol}")
                result = {}
            
            # 执行回调
            if task.callback:
                try:
                    task.callback(result or {})
                except Exception as e:
                    logger.warning(f"[AI队列] 回调执行失败: {symbol} - {e}")
                    
        except Exception as e:
            logger.error(f"[AI队列] ❌ 分析失败: {symbol} - {e}")
            if task.callback:
                try:
                    task.callback({})
                except:
                    pass
            raise
    
    def enqueue(
        self,
        symbol: str,
        signal_payload: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> str:
        """
        将信号加入队列
        
        Args:
            symbol: 币种符号
            signal_payload: 信号数据
            callback: 处理完成后的回调函数，接收分析结果
            
        Returns:
            任务ID
        """
        if _is_bull_bear_signal_expired(signal_payload):
            self._stats["total_skipped"] += 1
            logger.info("[AIQueue] Skip expired bull/bear signal: %s", symbol)
            if callback:
                try:
                    callback({})
                except Exception as exc:
                    logger.warning("[AIQueue] Skip callback failed: %s", exc)
            return f"skipped-{time.time():.6f}"

        task = AISignalTask(
            symbol=symbol,
            signal_payload=signal_payload,
            callback=callback,
        )
        
        self._queue.put(task)
        self._stats["total_queued"] += 1
        
        queue_size = self._queue.qsize()
        logger.info(f"[AI队列] 入队: {symbol} (队列长度: {queue_size}, 任务ID: {task.task_id})")
        
        # 确保工作线程在运行
        self._start_worker()
        
        return task.task_id
    
    def get_queue_size(self) -> int:
        """获取当前队列长度"""
        return self._queue.qsize()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._processing_lock:
            current = self._current_task.symbol if self._current_task else None
        
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "current_processing": current,
        }
    
    def is_processing(self) -> bool:
        """是否正在处理任务"""
        with self._processing_lock:
            return self._current_task is not None
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒），None表示无限等待
            
        Returns:
            是否在超时前完成
        """
        try:
            self._queue.join()
            return True
        except:
            return False
    
    def stop(self):
        """停止队列处理"""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        logger.info("[AI队列] 队列管理器已停止")


# 全局单例
_queue_instance: Optional[AISignalQueue] = None
_queue_lock = threading.Lock()


def get_ai_signal_queue() -> AISignalQueue:
    """获取全局AI信号队列实例"""
    global _queue_instance
    if _queue_instance is None:
        with _queue_lock:
            if _queue_instance is None:
                _queue_instance = AISignalQueue()
    return _queue_instance


def enqueue_ai_signal(
    symbol: str,
    signal_payload: Optional[Dict[str, Any]] = None,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> str:
    """
    快捷函数：将信号加入AI简评队列
    
    Args:
        symbol: 币种符号
        signal_payload: 信号数据
        callback: 处理完成后的回调函数
        
    Returns:
        任务ID
    """
    return get_ai_signal_queue().enqueue(symbol, signal_payload, callback)


def get_queue_stats() -> Dict[str, Any]:
    """获取队列统计信息"""
    return get_ai_signal_queue().get_stats()
