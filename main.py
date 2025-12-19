import os
import runpy


def _main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    runpy.run_path(os.path.join(root_dir, "src", "main.py"), run_name="__main__")


if __name__ == "__main__":
    _main()

