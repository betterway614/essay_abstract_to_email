import os
import runpy
import sys


def _main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(root_dir, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    runpy.run_path(os.path.join(root_dir, "src", "main.py"), run_name="__main__")


if __name__ == "__main__":
    _main()

