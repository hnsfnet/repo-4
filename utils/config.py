import yaml
import os

_CONFIG = None

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')


def load_config(path=None):
    global _CONFIG
    if _CONFIG is not None and path is None:
        return _CONFIG
    cfg_path = path or CONFIG_PATH
    with open(cfg_path, 'r', encoding='utf-8') as f:
        _CONFIG = yaml.safe_load(f)
    return _CONFIG


def get_config(path=None):
    if _CONFIG is None:
        return load_config(path)
    return _CONFIG


def get(key, default=None):
    cfg = get_config()
    keys = key.split('.')
    val = cfg
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val
