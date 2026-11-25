r"""Import mouse_pcb.step so ALL PCB sub-component .prt files live directly inside
`C:\Users\marya\Desktop\Neon Mouse\prt`, rebuild `mouse_asm.prt` with every component
loaded and saved, and export a complete `mouse_assembly_full.step` (PCB + 7 mechanical parts).
"""
import os
import sys
import traceback

sys.path.insert(0, os.environ.get("NXH_DIR", r"H:\My Drive\NX HARNESS VERSIONS\v2\skills\nx-journal-core\scripts"))
import NXOpen
import nxh
import nxf
import nxa


def main():
    prt_dir = sys.argv[1]
    stp_dir = sys.argv[2]
    pcb_step = sys.argv[3]
    res_json = sys.argv[4]

    res = {"result": "FAIL", "saved_parts": [], "loaded_components": []}
    try:
        # Remove old mouse_pcb_ref.prt and mouse_asm.prt so NX creates clean ones
        pcb_prt_path = os.path.join(prt_dir, "mouse_pcb_ref.prt")
        asm_path = os.path.join(prt_dir, "mouse_asm.prt")
        for p in (pcb_prt_path, asm_path):
            if os.path.exists(p):
                os.remove(p)

        # 1. Import mouse_pcb.step directly into prt_dir so every sub-component .prt is saved in prt_dir!
        pcb_part = nxh.new_part(pcb_prt_path)
        scratch_prt = os.path.join(prt_dir, "_pcb_import_tmp.prt")
        nxf.step_import(pcb_part, pcb_step, scratch_prt)

        # Save ALL loaded parts in the session (writes all 12 PCB sub-component .prt files to prt_dir!)
        for loaded in nxh.S.Parts:
            try:
                loaded.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
                res["saved_parts"].append(os.path.basename(loaded.FullPath))
            except Exception as e:
                res.setdefault("save_warnings", []).append(f"{loaded.FullPath}: {e}")

        # 2. Create clean mouse_asm.prt referencing all parts in prt_dir
        mech_names = [
            "mouse_base",
            "mouse_top_shell",
            "mouse_scroll_wheel",
            "mouse_dpi_button",
            "mouse_thumb_fwd",
            "mouse_thumb_back",
            "mouse_skates",
        ]
        asm = nxa.new_assembly(asm_path)
        # Add PCB assembly with Entire Part so all sub-components show & export cleanly
        nxa.add_component(asm, pcb_prt_path, "MOUSE_PCB", refset="Entire Part")
        for name in mech_names:
            p = os.path.join(prt_dir, name + ".prt")
            nxa.add_component(asm, p, name.upper(), refset="MODEL")

        asm.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)

        # Verify all leaf instances and solid counts
        insts = nxf.instance_solids(asm, load=True)
        res["loaded_components"] = [
            {"name": r["name"], "solids": len(r["bodies"])} for r in insts
        ]
        res["total_solids_in_asm"] = sum(len(r["bodies"]) for r in insts)

        # Export TRUE full assembly STEP (PCB + 7 mechanical parts!)
        full_stp = os.path.join(stp_dir, "mouse_assembly_full.step")
        nxf.step_export(asm, full_stp, ap242=False)
        res["full_step_bytes"] = os.path.getsize(full_stp) if os.path.exists(full_stp) else 0

        # Clean up unused scratch file if not referenced
        if os.path.exists(scratch_prt):
            try:
                os.remove(scratch_prt)
            except Exception:
                pass

        res["result"] = "PASS" if res["total_solids_in_asm"] >= 70 else "WARN"
    except Exception:
        res["error"] = traceback.format_exc()

    nxh.write_json(res_json, res)


if __name__ == "__main__":
    main()
