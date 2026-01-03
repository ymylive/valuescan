# Token刷新机制优化方案

## 当前问题

用户反馈: 日志中经常显示"Token已过期",但数据仍能正常获取。

## 问题分析

### 当前逻辑
```python
# 1. API返回 code 4000/4002
if code in (4000, 4002):
    logger.error(f"Token 已过期或失效 (code {code})")
    return None, "expired"

# 2. 主循环检测到expired后触发刷新
elif status == "expired":
    if _trigger_chrome_refresh("token_expired"):
        consecutive_failures = 0
        time.sleep(1)
        continue
```

### 可能的原因

1. **Token真的频繁过期**
   - Token有效期很短
   - 每次请求都可能遇到过期

2. **刷新太频繁**
   - 没有记录上次刷新时间
   - 可能在短时间内多次刷新

3. **API误报**
   - API可能在某些情况下错误返回4000

---

## 优化方案

### 方案1: 添加刷新冷却时间 ✅ 推荐

**思路**: 记录上次刷新时间,避免频繁刷新

```python
# 全局变量
_last_token_refresh_time = 0
TOKEN_REFRESH_COOLDOWN = 300  # 5分钟冷却

def should_refresh_token():
    """检查是否应该刷新token"""
    global _last_token_refresh_time
    current_time = time.time()

    # 如果距离上次刷新不到5分钟,不刷新
    if current_time - _last_token_refresh_time < TOKEN_REFRESH_COOLDOWN:
        logger.info(f"Token刷新冷却中,距离上次刷新 {int(current_time - _last_token_refresh_time)} 秒")
        return False

    return True

# 主循环中
elif status == "expired":
    if should_refresh_token():
        if _trigger_chrome_refresh("token_expired"):
            _last_token_refresh_time = time.time()
            consecutive_failures = 0
            time.sleep(1)
            continue
    else:
        # 冷却期内,等待token自动恢复
        logger.info("Token刷新冷却中,等待...")
        time.sleep(10)
```

### 方案2: 重试机制

**思路**: 遇到4000错误时先重试,确认真的过期才刷新

```python
def fetch_with_retry(session, account_token, proxies, max_retries=2):
    """带重试的fetch"""
    for attempt in range(max_retries):
        payload, status = fetch_signals(session, account_token, proxies)

        if status == "expired" and attempt < max_retries - 1:
            logger.warning(f"Token可能过期,重试 {attempt + 1}/{max_retries}")
            time.sleep(2)
            continue

        return payload, status

    return None, "expired"
```

### 方案3: Token有效期检查

**思路**: 在token中解析过期时间,提前刷新

```python
import jwt
from datetime import datetime

def check_token_expiry(token):
    """检查token是否即将过期"""
    try:
        # 解析JWT token
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp')

        if exp:
            exp_time = datetime.fromtimestamp(exp)
            now = datetime.now()
            remaining = (exp_time - now).total_seconds()

            # 如果剩余时间少于5分钟,需要刷新
            if remaining < 300:
                logger.info(f"Token将在 {remaining} 秒后过期,需要刷新")
                return True

        return False
    except:
        return False
```

---

## 推荐实施步骤

### 第一步: 添加刷新冷却 (立即实施)

修改 `polling_monitor.py`:

1. 添加全局变量记录刷新时间
2. 添加 `should_refresh_token()` 函数
3. 修改主循环的expired处理逻辑

### 第二步: 优化日志输出

将频繁的ERROR日志改为INFO:

```python
# 修改前
logger.error(f"Token 已过期或失效 (code {code})")

# 修改后
logger.info(f"检测到Token过期信号 (code {code}),准备刷新")
```

### 第三步: 添加统计信息

记录token刷新次数和成功率:

```python
_token_refresh_count = 0
_token_refresh_success = 0

# 刷新成功后
_token_refresh_count += 1
_token_refresh_success += 1
logger.info(f"Token刷新成功 (总计: {_token_refresh_count}, 成功率: {_token_refresh_success/_token_refresh_count*100:.1f}%)")
```

---

## 预期效果

1. ✅ 减少频繁的"Token过期"日志
2. ✅ 避免不必要的token刷新
3. ✅ 提高系统稳定性
4. ✅ 更清晰的日志输出

---

## 需要修改的文件

- `signal_monitor/polling_monitor.py` - 主要修改
