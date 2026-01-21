from threading import Lock


class SingletonMeta(type):
    """
    这是一个线程安全的单例实现元类。
    """

    _instances = {}       # 小本本，记录已经创建过的对象
    _lock: Lock = Lock()  # 锁，防止多线程同时挤进来

    def __call__(cls, *args, **kwargs):
        # 当调用 AgentManager() 时，实际上是触发了这里的 __call__
        with cls._lock:
            # 1. 查小本本：这个类之前创建过实例吗？
            if cls not in cls._instances:
                # 2. 没创建过 -> 创建一个新的，并记在小本本上
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        # 3. 如果创建过 -> 直接把小本本上记录的那个旧实例给你
        return cls._instances[cls]