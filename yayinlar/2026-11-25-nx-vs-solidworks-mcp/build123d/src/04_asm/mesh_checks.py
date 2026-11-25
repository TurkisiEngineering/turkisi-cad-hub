r"""WP-I step 3 (cadgenbench venv): mesh clearances, motion travel, assembly sweeps -> mesh_checks.json"""
from mesh_checks_lib import *  # noqa

# ---------------------------------------------------------------- 1. clearances at rest
SHELLS = {"bottom_shell", "top_shell"}
DESIGNED_PCB = {"button_L": ["SW_mainL_plunger"], "button_R": ["SW_mainR_plunger"], "dpi_button": ["SW_dpi_plunger"],
                "wheel_body": ["SW_middle_plunger", "EC10E"], "axle_pin": ["SW_middle_plunger"],
                "side_btn_fwd": ["SW_side_fwd_plunger"], "side_btn_back": ["SW_side_back_plunger"],
                "bottom_shell": ["board"]}
clr = {}
for n in PARTS:
    rows = []
    for k, pm in PCB.items():
        lab = k.split(":", 1)[1]
        if bbgap(M[n], pm) > 3.0: continue
        d, p = mindist(M[n], pm)
        rows.append((round(d, 3), lab, p))
    rows.sort()
    lim = 1.0 if n in SHELLS else 0.25
    nd = [r for r in rows if r[1] not in DESIGNED_PCB.get(n, []) and not r[1].endswith("_lead")]
    leads = [r for r in rows if r[1].endswith("_lead")]
    clr[n] = dict(limit=lim, min_nondesigned=nd[0] if nd else None, min_lead=leads[0] if leads else None,
                  designed=[r for r in rows if r[1] in DESIGNED_PCB.get(n, [])][:3], closest5=rows[:5])
    print("CLR", n, clr[n]["min_nondesigned"], "lead", clr[n]["min_lead"], flush=True)
OUT["pcb_clearance_rest"] = clr

pp = {}
for i, a in enumerate(PARTS):
    for b in PARTS[i + 1:]:
        if bbgap(M[a], M[b]) > 2.0: continue
        d, p = mindist(M[a], M[b]); pp[f"{a}|{b}"] = (round(d, 3), p)
        print("PP", a, b, round(d, 3), p, flush=True)
OUT["part_gaps_rest"] = pp

# ---------------------------------------------------------------- 2. motion
mo = {}
a = math.radians(POSE["btn_stop_deg"])
for side, sw, swk in (("button_L", (20.32, -23.53), "SW_mainL"), ("button_R", (58.42, -23.53), "SW_mainR")):
    V = MP[side].vertices; V0 = M[side].vertices
    nub_rest = zhit(M[side], *sw, z0=3.0); nub_pose = zhit(MP[side], *sw, z0=3.0)
    post = (V0[:, 2] < 2.4) & (V0[:, 1] > -25.1) & (V0[:, 1] < -21.9)
    r = dict(stop_deg=POSE["btn_stop_deg"], nub_rest_Z=round(float(nub_rest), 3), nub_rest_gap=round(float(nub_rest - 7.595), 3),
             nub_stop_Z=round(float(nub_pose), 3), nub_travel=round(float(nub_rest - nub_pose), 3),
             plunger_travel=round(float(7.595 - nub_pose), 3), post_min_Z_at_stop=round(float(V[post].min(0)[2] if post.any() else -1), 3),
             tip_travel=round(float(M[side].vertices[:, 2][M[side].vertices[:, 1] > -5].min() - V[:, 2][V[:, 1] > -5].min()), 3))
    rows = []
    for k, pm in PCB.items():
        lab = k.split(":", 1)[1]
        if bbgap(MP[side], pm) > 2.0 or lab in (swk + "_plunger", "board"): continue
        rows.append((round(mindist(MP[side], pm)[0], 3), lab))
    others = {o: round(mindist(MP[side], M[o])[0], 3) for o in PARTS if o != side and bbgap(MP[side], M[o]) < 2.0}
    r["min_pcb_nondesigned_at_stop"] = sorted(rows)[:3]; r["parts_at_stop"] = others
    mo[side] = r; print("MO", side, r, flush=True)

# wheel: plunger travel at the stop = drop of the pin bottom at X 50.8
z0 = zhit(M["axle_pin"], 50.8, -27.9, 3.0); z1 = zhit(MP["axle_pin"], 50.8, -27.9, 3.0)
r = dict(stop_deg=POSE["wheel_stop_deg"], axle_bottom_rest=round(float(z0), 3), rest_gap=round(float(z0 - 7.595), 3),
         axle_bottom_stop=round(float(z1), 3), plunger_travel=round(float(7.595 - z1), 3),
         wheel_top_drop=round(float(M["wheel_body"].vertices[:, 2].max() - MP["wheel_body"].vertices[:, 2].max()), 3))
rows = []
for k, pm in PCB.items():
    lab = k.split(":", 1)[1]
    if lab in ("SW_middle_plunger", "EC10E"): continue
    for w in ("wheel_body", "axle_pin"):
        if bbgap(MP[w], pm) < 2.0: rows.append((round(mindist(MP[w], pm)[0], 3), w, lab))
r["min_pcb_nondesigned_at_stop"] = sorted(rows)[:4]
r["parts_at_stop"] = {f"{w}|{o}": round(mindist(MP[w], M[o])[0], 3) for w in ("wheel_body", "axle_pin")
                      for o in ("top_shell", "bottom_shell", "wheel_yoke", "dpi_button") if bbgap(MP[w], M[o]) < 2.0}
mo["wheel"] = r; print("MO wheel", r, flush=True)

for lev, sw in (("side_btn_fwd", "SW_side_fwd"), ("side_btn_back", "SW_side_back")):
    y = -50.8 if lev.endswith("fwd") else -68.58
    V1 = MP[lev].vertices
    nub0 = zhit(M[lev], 20.99, y, 3.0); nub1 = zhit(MP[lev], 20.99, y, 3.0)
    st = V1[(V1[:, 2] > 0.0) & (V1[:, 2] < 1.51)]
    r = dict(stop_deg=POSE["side_stop_deg"], nub_rest_gap=round(float(nub0 - 7.595), 3),
             nub_travel=round(float(nub0 - nub1), 3), stop_face_maxX_on_board_band=round(float(st[:, 0].max()), 3) if len(st) else None)
    rows = []
    for k, pm in PCB.items():
        lab = k.split(":", 1)[1]
        if lab in (sw + "_plunger", "board") or bbgap(MP[lev], pm) > 2.0: continue
        rows.append((round(mindist(MP[lev], pm)[0], 3), lab))
    r["min_pcb_nondesigned_at_stop"] = sorted(rows)[:3]
    r["parts_at_stop"] = {o: round(mindist(MP[lev], M[o])[0], 3) for o in PARTS if o != lev and bbgap(MP[lev], M[o]) < 2.0}
    mo[lev] = r; print("MO", lev, r, flush=True)

r = dict(press=POSE["dpi_press"], nub_rest_gap=round(float(zhit(M["dpi_button"], 40.04, -43.18, 3.0) - 7.595), 3),
         plunger_travel=POSE["dpi_press"])
rows = []
for k, pm in PCB.items():
    lab = k.split(":", 1)[1]
    if lab == "SW_dpi_plunger" or bbgap(MP["dpi_button"], pm) > 2.0: continue
    rows.append((round(mindist(MP["dpi_button"], pm)[0], 3), lab))
r["min_pcb_nondesigned_pressed"] = sorted(rows)[:3]
r["parts_pressed"] = {o: round(mindist(MP["dpi_button"], M[o])[0], 3) for o in ("top_shell", "wheel_body")}
mo["dpi_button"] = r; print("MO dpi", r, flush=True)
OUT["motion"] = mo

# ---------------------------------------------------------------- 3. assembly sweeps
sw = {}
fixed_all = {**{k: v for k, v in PCB.items()}, **{n: M[n] for n in ["bottom_shell", "wheel_body", "axle_pin", "wheel_yoke",
                                                                     "side_btn_fwd", "side_btn_back"]}}
top_group = {n: M[n] for n in ["top_shell", "button_L", "button_R", "dpi_button"]}
h = sweep(top_group, fixed_all, (0, 0, -1), 15.0); sw["top_group_drop_15"] = summarize(h)
by = {}
for p, t, nm in h: by.setdefault(nm, 0); by[nm] += 1
sw["top_group_drop_15"]["count_by_source"] = by
print("SW top drop", sw["top_group_drop_15"], flush=True)
h = sweep({"top_shell": M["top_shell"]}, fixed_all, (0, 0, -1), 15.0); sw["top_shell_alone_drop_15"] = summarize(h)

# buttons into the top shell (sub-assembly, off the mouse): which straight directions are free?
for side in ("button_L", "button_R"):
    res = {}
    for ang in (90, 75, 60, 45, 30, 15, 0, -15, -30, -45, -60, -90):    # motion dir in the YZ plane: (0, -cos, sin)
        d = (0, -math.cos(math.radians(ang)), math.sin(math.radians(ang)))
        hh = sweep({side: M[side]}, {"top_shell": M["top_shell"]}, d, 30.0)
        res[ang] = dict(n=len(hh), tmin=min([x[1] for x in hh], default=None),
                        where=summarize(hh).get("bbox"))
    sw[f"{side}_insert_into_top_shell"] = res
    print("SW", side, {k: v["n"] for k, v in res.items()}, flush=True)
h = sweep({"dpi_button": M["dpi_button"]}, {"top_shell": M["top_shell"]}, (0, 0, 1), 20.0)
sw["dpi_insert_from_below"] = summarize(h)
cradle = lambda P: ((P[:, 0] - 12.2) ** 2 + (P[:, 2] + 1.6) ** 2) < 1.75 ** 2
for lev in ("side_btn_fwd", "side_btn_back"):
    h = sweep({lev: M[lev]}, {"bottom_shell": M["bottom_shell"], **PCB}, (0, 0, -1), 20.0, ignore=cradle)
    sw[f"{lev}_drop_into_cradles"] = summarize(h)
    h = sweep({lev: M[lev]}, {"bottom_shell": M["bottom_shell"], **PCB}, (1, 0, -1), 20.0, ignore=cradle)
    sw[f"{lev}_in_from_outboard_45"] = summarize(h)
    print("SW", lev, sw[f"{lev}_drop_into_cradles"]["n"], sw[f"{lev}_in_from_outboard_45"]["n"], flush=True)
# wheel: body (no pin yet) lowered at +2.1 X, then slid -X 2.1 onto the hex; yoke in place or not
wb_off = M["wheel_body"].copy(); wb_off.apply_translation((2.1, 0, 0))
fx = {"bottom_shell": M["bottom_shell"], **PCB}
sw["wheel_body_lower_at_+2.1X"] = summarize(sweep({"wb": wb_off}, fx, (0, 0, -1), 25.0))
sw["wheel_body_slide_-X_2.1_no_yoke"] = summarize(sweep({"wheel_body": M["wheel_body"]},
                                                       {k: v for k, v in fx.items() if not k.endswith("EC10E")}, (-1, 0, 0), 2.1))
sw["wheel_body_slide_-X_2.1_yoke_seated"] = summarize(sweep({"wheel_body": M["wheel_body"]}, {"wheel_yoke": M["wheel_yoke"]}, (-1, 0, 0), 2.1))
sw["wheel_assembly_slide_-X_2.1_yoke_seated"] = summarize(sweep({"wheel_body": M["wheel_body"], "axle_pin": M["axle_pin"]},
                                                               {"wheel_yoke": M["wheel_yoke"]}, (-1, 0, 0), 2.1))
sw["yoke_drop_into_socket"] = summarize(sweep({"wheel_yoke": M["wheel_yoke"]}, {**fx, "wheel_body": M["wheel_body"]}, (0, 0, -1), 20.0))
sw["axle_pin_push_-X_through_yoke"] = summarize(sweep({"axle_pin": M["axle_pin"]}, {**fx, "wheel_yoke": M["wheel_yoke"]}, (-1, 0, 0), 20.0))
for k in list(sw):
    if k.startswith("wheel") or k.startswith("yoke") or k.startswith("axle") or k.startswith("dpi") or k.startswith("top_shell_alone"):
        print("SW", k, sw[k], flush=True)
OUT["sweeps"] = sw
json.dump(OUT, open(ASM / "mesh_checks.json", "w"), indent=1, default=str)
print("done")
