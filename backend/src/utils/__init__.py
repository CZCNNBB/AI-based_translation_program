import hashlib
import time


def hashstr(input_string, length=None, with_salt=False):
    """生成字符串的哈希值
    Args:
        input_string: 输入字符串
        length: 截取长度，默认为None，表示不截取
        with_salt: 是否加盐，默认为False
    """
    try:
        # 尝试直接编码
        encoded_string = str(input_string).encode("utf-8")
    except UnicodeEncodeError:
        # 如果编码失败，替换无效字符
        encoded_string = str(input_string).encode("utf-8", errors="replace")

    if with_salt:
        salt = str(time.time())
        encoded_string = (encoded_string.decode("utf-8") + salt).encode("utf-8")

    hash = hashlib.md5(encoded_string).hexdigest()
    if length:
        return hash[:length]
    return hash