"""把 samples/plugin_exports/ 下的插件导出 JSON 全部灌入索引（演示用）。"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from container import init_from_plugin_exports

if __name__ == "__main__":
    paths = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "plugin_exports", "*.json")))
    print(f"导入 {len(paths)} 个文件 → {init_from_plugin_exports(paths)} 条消息")