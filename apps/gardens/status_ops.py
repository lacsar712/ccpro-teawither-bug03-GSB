"""萎凋槽状态的唯一口径：字面量、统计、筛选都从这里取。

状态字面量直接引用 Trough 模型上的常量，首页状态卡、整页筛选、
HTMX 局部表必须共用本模块，禁止再各自维护映射表。
"""
from django.db.models import Count

from .models import Trough

STATUS_LOADING = Trough.STATUS_LOADING
STATUS_WITHERING = Trough.STATUS_WITHERING
STATUS_READY = Trough.STATUS_READY

# 按 STATUS_CHOICES 的顺序排列，供模板/视图统一取用
VALID_STATUSES = [value for value, _label in Trough.STATUS_CHOICES]


def normalize_status(value):
    """把请求里的 status 参数归一化为合法字面量，非法值返回 None。"""
    if value in VALID_STATUSES:
        return value
    return None


def trough_status_counts(queryset=None):
    """返回 {状态字面量: 数量}，三个状态键一定齐全（默认补 0）。"""
    qs = queryset if queryset is not None else Trough.objects.all()
    counts = {status: 0 for status in VALID_STATUSES}
    rows = qs.values("status").annotate(total=Count("pk"))
    for row in rows:
        if row["status"] in counts:
            counts[row["status"]] = row["total"]
    return counts


def filter_troughs_by_status(queryset, status):
    """按状态字面量筛选槽位；status 为空或非法时不做筛选。"""
    normalized = normalize_status(status)
    if normalized is None:
        return queryset
    return queryset.filter(status=normalized)
