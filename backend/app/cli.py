import sys

from .config import CONFIG_SRC


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    root = sys.argv[2] if len(sys.argv) > 2 else CONFIG_SRC
    if cmd in ("load", "all"):
        from . import loader
        loader.run(root)
    if cmd in ("index", "all"):
        from . import indexer
        indexer.run()
    if cmd in ("docs", "all"):
        from . import docs
        docs.generate_missing()


if __name__ == "__main__":
    main()
