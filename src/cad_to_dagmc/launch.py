import runpy
import sys
import cad_to_dagmc
from pathlib import Path


def main():

    path_to_app = str(Path(cad_to_dagmc.__path__[0]) / "app.py")

    sys.argv = ["streamlit", "run", path_to_app]
    runpy.run_module("streamlit", run_name="__main__")


if __name__ == "__main__":
    main()
