"""Wrapper: side_btn_back uses the shared parametric lever builder in ../side_btn_fwd/build_side_btn.py."""
import runpy, sys
from pathlib import Path
sys.argv = [sys.argv[0], "back"]
runpy.run_path(str(Path(__file__).resolve().parents[1] / "side_btn_fwd" / "build_side_btn.py"), run_name="__main__")
