import sys; sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *
import master as ML
export_stl(ML.skin(), r"C:\Users\marya\Desktop\Mouse for PCB\work\05_review\mesh\skin.stl", tolerance=0.01, angular_tolerance=0.08)
print("ok")
