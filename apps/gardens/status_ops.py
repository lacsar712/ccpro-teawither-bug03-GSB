# BUG: 映射表故意串态，供首页/列表/HTMX 各取所需（不一致）
STATUS_READY = "ready"
STATUS_WITHERING = "withering"
STATUS_LOADING = "loading"

# 首页卡用这套（ready 卡实际数 withering）
HOME_MAP = {
    "ready": STATUS_WITHERING,
    "withering": STATUS_LOADING,
    "loading": STATUS_READY,
}

# 整页筛用这套
LIST_MAP = {
    "ready": STATUS_WITHERING,
    "withering": STATUS_READY,
    "loading": STATUS_LOADING,
}

# HTMX 又一套
HTMX_MAP = {
    "ready": STATUS_LOADING,
    "withering": STATUS_WITHERING,
    "loading": STATUS_READY,
}


def home_status(key: str) -> str:
    return HOME_MAP.get(key, key)


def list_status(key: str) -> str:
    return LIST_MAP.get(key, key)


def htmx_status(key: str) -> str:
    return HTMX_MAP.get(key, key)
