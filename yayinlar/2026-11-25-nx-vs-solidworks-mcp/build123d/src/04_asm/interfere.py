"""WP-I step 2: exact OCC common volumes, every part pair + every part vs every PCB solid, at rest and with
each moving part in its stop pose.  python interfere.py   -> interfere.json"""
import time, json, multiprocessing as mp
from asm_common import *     # noqa

G = {}
POSE = json.load(open(ASM / "poses.json"))
POSES = {"button_L": (BTN_AXIS, POSE["btn_stop_deg"]), "button_R": (BTN_AXIS, POSE["btn_stop_deg"]),
         "wheel_body": (WHEEL_AXIS, POSE["wheel_stop_deg"]), "axle_pin": (WHEEL_AXIS, POSE["wheel_stop_deg"]),
         "side_btn_fwd": (SIDE_AXIS, POSE["side_stop_deg"]), "side_btn_back": (SIDE_AXIS, POSE["side_stop_deg"]),
         "dpi_button": (None, -POSE["dpi_press"])}
# designed contacts (pair -> why); pose-only contacts are the actuation itself
DESIGNED = {("button_L", "SW_mainL_plunger"): "nub/plunger", ("button_R", "SW_mainR_plunger"): "nub/plunger",
            ("button_L", "board"): "stop post on board", ("button_R", "board"): "stop post on board",
            ("dpi_button", "SW_dpi_plunger"): "nub/plunger",
            ("wheel_body", "SW_middle_plunger"): "axle/plunger", ("axle_pin", "SW_middle_plunger"): "axle/plunger",
            ("wheel_body", "EC10E"): "hex in rotor", ("axle_pin", "wheel_body"): "pin press fit",
            ("wheel_body", "axle_pin"): "pin press fit",
            ("side_btn_fwd", "SW_side_fwd_plunger"): "nub/plunger", ("side_btn_back", "SW_side_back_plunger"): "nub/plunger",
            ("side_btn_fwd", "board"): "stop face on board edge", ("side_btn_back", "board"): "stop face on board edge",
            ("bottom_shell", "board"): "boss tops", ("bottom_shell", "top_shell"): "parting plane",
            ("top_shell", "button_L"): "leaf clamp", ("top_shell", "button_R"): "leaf clamp",
            ("bottom_shell", "side_btn_fwd"): "pin in cradle", ("bottom_shell", "side_btn_back"): "pin in cradle"}


def init():
    _, ps = pcb_solids()
    G["pcb"] = {f"pcb{d['idx']:02d}:{d['label']}": d["solid"] for d in ps}
    G["parts"] = {n: load_part(n) for n, *_ in PARTS_LIST}
    G["pose"] = {}
    for n, (ax, v) in POSES.items():
        G["pose"][n] = G["parts"][n].rotate(ax, v) if ax else G["parts"][n].translate((0, 0, v))


def get(key):
    if key.startswith("pcb"):
        return G["pcb"][key]
    if key.endswith("@pose"):
        return G["pose"][key[:-5]]
    return G["parts"][key]


def job(t):
    a, b = t
    t0 = time.time()
    try:
        v = common_vol(get(a), get(b))
    except Exception as e:
        v = None
    return a, b, v, round(time.time() - t0, 2)


def keybase(k):
    k = k.replace("@pose", "")
    return k.split(":", 1)[1] if k.startswith("pcb") else k


if __name__ == "__main__":
    t0 = time.time()
    init()
    keys_parts = list(G["parts"]); keys_pcb = list(G["pcb"])
    bbs = {k: bbox_of(get(k)) for k in keys_parts + keys_pcb}
    for n in POSES:
        bbs[n + "@pose"] = bbox_of(G["pose"][n])
    tasks = []
    for i, a in enumerate(keys_parts):
        for b in keys_parts[i + 1:] + keys_pcb:
            if bb_overlap(bbs[a], bbs[b]): tasks.append((a, b))
    for n in POSES:
        a = n + "@pose"
        for b in [k for k in keys_parts if k != n] + keys_pcb:
            if n in ("wheel_body", "axle_pin") and b in ("wheel_body", "axle_pin"):
                continue    # they move together
            if n.startswith("button") and b.startswith("button"):
                continue    # both-pressed case covered by the other button's pose vs rest (gap > 2)
            if bb_overlap(bbs[a], bbs[b]): tasks.append((a, b))
    print(len(tasks), "tasks after bbox prefilter", flush=True)
    res = []
    with mp.Pool(10, initializer=init) as pool:
        for r in pool.imap_unordered(job, tasks):
            res.append(r)
            if r[2] is None or r[2] > 0.01:
                print(r, flush=True)
    out = []
    for a, b, v, dt in sorted(res):
        pa, pb = keybase(a), keybase(b)
        dsg = DESIGNED.get((pa, pb)) or DESIGNED.get((pb, pa))
        if dsg is None and pb.endswith("_plunger"):
            dsg = None
        out.append(dict(a=a, b=b, vol=None if v is None else round(v, 4), t=dt, designed=dsg,
                        flag=(v is None) or (v > 0.01 and not dsg)))
    json.dump(out, open(ASM / "interfere.json", "w"), indent=1)
    print("---- overlaps > 0.01 mm3 ----")
    for o in out:
        if o["vol"] is None or o["vol"] > 0.01:
            print(f"{o['a']:28s} {o['b']:34s} {o['vol']}  designed={o['designed']}  FLAG={o['flag']}")
    print(f"done {time.time()-t0:.0f}s, {len(out)} pairs, {sum(o['flag'] for o in out)} flagged")
