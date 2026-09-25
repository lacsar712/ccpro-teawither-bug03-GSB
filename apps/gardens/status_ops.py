"""萎凋槽状态的唯一入口：字面量、归一化、统计。

首页状态卡、整页筛选、HTMX 局部刷新必须共用这里的
normalize_status() 与 status_counts()，任何一处都不允许
再维护私有的状态映射表。
"""

from django.db.models import Count

from .models import Trough

# 状态字面量唯一定义在 Trough 模型上，此处仅作再导出，
# 保证查询参数、模板 badge、数据库取值始终是同一组字符串。
STATUS_LOADING = Trough.STATUS_LOADING
STATUS_WITHERING = Trough.STATUS_WITHERING
STATUS_READY = Trough.STATUS_READY

STATUS_KEYS = (STATUS_LOADING, STATUS_WITHERING, STATUS_READY)


def normalize_status(value):
    """把请求参数归一化为规范状态字面量。

    合法（loading/withering/ready）原样返回；缺失或非法返回 None，
    调用方据此判断是否需要过滤。所有筛选路径共用本函数。
    """
    if value in STATUS_KEYS:
        return value
    return None


def filter_by_status(queryset, value):
    """按请求参数过滤槽位查询集；参数缺失或非法时不过滤。"""
    status = normalize_status(value)
    if status is None:
        return queryset
    return queryset.filter(status=status)


def status_counts():
    """三种状态各自的槽位数：{状态字面量: 数量}，键始终齐全。

    首页三张状态卡必须全部取自本函数，保证与列表筛选同源。
    """
    counts = {key: 0 for key in STATUS_KEYS}
    rows = Trough.objects.values("status").annotate(n=Count("id"))
    for row in rows:
        if row["status"] in counts:
            counts[row["status"]] = row["n"]
    return counts
