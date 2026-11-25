"""wheel_yoke is built, checked and exported together with the wheel (the checks need both parts):
runs ../wheel/build_wheel.py, which writes wheel_yoke.step/.stl/_print.stl into this folder."""
import runpy, pathlib
runpy.run_path(str(pathlib.Path(__file__).resolve().parents[1] / "wheel" / "build_wheel.py"), run_name="__main__")
