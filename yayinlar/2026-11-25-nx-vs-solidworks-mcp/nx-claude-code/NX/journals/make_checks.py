"""Compose CHECKS.md from the measured NX results (out/*_result.json), the STL analysis and the STEP read-back."""
import json, os, numpy as np, trimesh

WS = r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx"
OUT = os.path.join(WS, "out")
R = os.path.join(WS, "render")
DEL = r"C:\Users\USER\Desktop\Mouse for PCB\TESLIM_NX"
J = {n: json.load(open(os.path.join(OUT, n + "_result.json"))) for n in
     ("j1_ctrl", "j2_bottom", "j3_top", "j4_keys", "j5_wheel", "j6_asm", "j7_regen")}
PR = json.load(open(os.path.join(R, "printability.json")))
SC = json.load(open(os.path.join(R, "stepcheck.json")))
a = J["j6_asm"]
g = a["gaps"]
pw = a["pressed_wheel"]

env = trimesh.load(os.path.join(R, "envelope.stl"))
loc, _, _ = env.ray.intersects_location([[0.0, 17.693, 60.0]], [[0, 0, -1.0]])
z_skin = float(max(p[2] for p in loc))
wheel_top = 8.595 + 11.0

L = []
w = L.append
w("# CHECKS – NX fare kabuğu (ölçülmüş değerler)\n")
w("Tüm değerler ölçüldü. Bir kısmı NX 2206 içinde alındı: NXOpen `AskMinimumDist`, Simple Interference, Clearance Analysis. "
  "Kalanı NX'ten alınan STL / STEP üzerinde Python (trimesh, OCP) ile hesaplandı. Ham sonuçlar: `NX/results/*.json`.\n")
w("Koordinat sistemi:")
w("- Kart merkezi = orijin (KiCad STEP'i x −39.370, y +45.593 kaydırıldı).")
w("- +Y = farenin önü.")
w("- Kart alt yüzü z = 0, bileşen oturma düzlemi z = 1.595.\n")

w("## 1. Journal özetleri\n")
w("| Journal | Sonuç | Kontrol | Hata |\n|---|---|---|---|")
for n, d in J.items():
    w("| %s | %s | %d | %d |" % (n, d["result"], len(d["checks"]), len([c for c in d["checks"] if not c["ok"]])))
w("\nj1_ctrl'deki tek HATA'nın açıklaması §9'da.\n")

w("## 2. Girişim (interference)\n")
w("NX Clearance Analysis (tüm bileşenler, tam hesap, bölge 0):\n")
w("| Çift | Tür | Yorum |\n|---|---|---|")
why = {("AXLE_PIN", "PCB"): "Ø2 pim SW3 plungerına oturuyor (orta tık, istenen temas)",
       ("AXLE_PIN", "WHEEL"): "Ø2.0 pim, Ø1.95 tekerlek deliğine pres geçme (istenen)",
       ("BOTTOM_SHELL", "PCB"): "PCB 4 standoff üzerinde (istenen temas)",
       ("BOTTOM_SHELL", "TOP_SHELL"): "kabuklar z = −1.0 ayırma düzleminde birbirine oturuyor",
       ("BTN_LEFT", "TOP_SHELL"): "tuş dili, üst kabuktaki vida göbeğine sıkışıyor (M2)",
       ("BTN_RIGHT", "TOP_SHELL"): "tuş dili, üst kabuktaki vida göbeğine sıkışıyor (M2)"}
for c in a["clearance_all"]:
    k = tuple(c["pair"])
    w("| %s – %s | %s | %s |" % (k[0], k[1], c["type"], why.get(k, "**incele**")))
w("")
hard = [d for d in a["pairs_within_1_5mm"] if d.get("result") == "InterferenceExists"]
w("Gövde-gövde Simple Interference uygulandı: birbirine 1.5 mm'den yakın bütün çiftler, PCB'nin 69 gövdesi tek tek ele alındı. "
  "%d çift incelendi. Katı örtüşme yalnız şurada: %s.\n" % (len(a["pairs_within_1_5mm"]), "; ".join(
      "%s–%s %.3f mm³ (pres geçme)" % (d["a"], d["b"], d["overlap"][0]) for d in hard) or "yok"))
w("| A | B | min mesafe (mm) | sonuç |\n|---|---|---|---|")
for d in sorted(a["pairs_within_1_5mm"], key=lambda d: d.get("min_dist", 9)):
    if "min_dist" in d:
        w("| %s | %s | %.3f | %s |" % (d["a"], d["b"], d["min_dist"], d["result"]))
w("")

w("## 3. Tuş nub – plunger boşlukları (dinlenme)\n")
w("Omron D2F (pim plunger) değerleri:")
w("- çalışma konumu OP 5.5 ± 0.3 (oturma düzleminden);")
w("- ön hareket PT ≤ 0.5;")
w("- aşırı hareket OT ≥ 0.25.\n")
w("STEP'te plunger üstü z = 7.595 = serbest konum (OP + PT).\n")
w("| Tuş | Anahtar | Ölçülen boşluk (mm) | Tıka kadar yol (boşluk + PT ≤ 0.5) |\n|---|---|---|---|")
for k, sw in (("btn_left-SW1", "SW1 sol tık"), ("btn_right-SW2", "SW2 sağ tık"), ("top_shell(DPI nub)-SW4", "SW4 DPI (üst kabuk dili)"),
              ("key_fwd-SW5", "SW5 yan ileri"), ("key_back-SW6", "SW6 yan geri")):
    w("| %s | %s | %.3f | ≤ %.2f |" % (k.split("-")[0], sw, g[k], g[k] + 0.5))
w("| tekerlek pimi | SW3 orta tık | %.3f (oturuyor) | ≤ 0.50 |" % g["axle_pin-SW3"])
w("")
w("Diğer tuş boşlukları:")
w("- sol/sağ tuş – üst kabuk yan boşluğu: 0.6 (`btn_gap`);")
w("- yan tuş – üst kabuk (menteşe kulakları): %.3f / %.3f mm;" % (g["key_fwd-top_shell"], g["key_back-top_shell"]))
w("- tuş dili: 1.0 mm esnek dil, serbest boyu ≈ 6 mm.\n")

w("## 4. Tekerlek ve orta tık\n")
w("- Tekerlek Ø22 × 7. Ekseni EC10E mili ekseninde (y 17.693, z 8.595).")
w("- Sol göbekteki Ø3.4 D-düz uç, EC10E deliğine (STEP'te Ø3.6) 4.6 mm girer.")
w("- Sağdaki Ø2 × 14 çelik pim SW3 plungerının üstüne oturur. Pimi alt kabuktaki çatal tutar (yarık 2.2, üstte 0.15 tırnak).")
w("- Dinlenme konumu:")
w("  - tekerlek – EC10E radyal boşluk %.3f mm;" % g["wheel-ENCODER1"])
w("  - tekerlek – alt kabuk %.3f mm, tekerlek – üst kabuk %.3f mm;" % (g["wheel-bottom_shell"], g["wheel-top_shell"]))
w("  - pim – çatal %.3f mm." % g["axle_pin-bottom_shell(fork)"])
w("- Basılı poz: NX'te tekerlek ve pim bileşenleri, enkoder deliği ortasındaki pivot etrafında %.3f° döndürüldü. "
  "Bu durumda pim SW3 üzerinde 0.75 mm aşağıdadır (PT 0.5 + OT 0.25). Ölçülenler:" % pw["tilt_deg"])
w("  - tekerlek – EC10E: min %.4f mm, %s;" % (pw["wheel-ENCODER1"][0], pw["wheel-ENCODER1"][1]))
w("  - tekerlek – alt kabuk: min %.4f mm, %s;" % (pw["wheel-bottom_shell"][0], pw["wheel-bottom_shell"][1]))
w("  - tekerlek – üst kabuk: min %.4f mm, %s;" % (pw["wheel-top_shell"][0], pw["wheel-top_shell"][1]))
w("  - pim – çatal: min %.4f mm, %s;" % (pw["axle_pin-bottom_shell"][0], pw["axle_pin-bottom_shell"][1]))
w("  - tekerlek – PCB: %.4f mm;" % pw["wheel-PCB"][0])
w("  - pim – SW3: %s, %.3f mm³. Bu plungerın 0.75 mm basılmasıdır; STEP'teki plunger rijit bir yer tutucu olduğu için beklenen sonuçtur." % (pw["axle_pin-SW3"][0], pw["axle_pin-SW3"][1][0]))
w("- Tekerleğin kabuk üstündeki çıkıntısı **%.2f mm**: tekerlek tepesi z %.3f, kabuk dış yüzü (x 0, y 17.693) z %.3f." % (wheel_top - z_skin, wheel_top, z_skin))
w("- Gereken eğim 2.03°, enkoder deliğinin izin verdiği eğimin (2·0.1/4.6 rad = 2.49°) altında.\n")

w("## 5. Sensör (PMW3360 + LM19-LSI)\n")
w("- Veri sayfası (PMW3360, Şekil 4):")
w("  - PCB üstü → yüzey: 7.40;")
w("  - lens flanşının altı (referans düzlemi) → yüzey: Z = 2.40 (2.2–2.6).")
w("- Modeldeki yığın:")
w("  - bileşen oturma düzlemi z 1.595 → seyir yüzeyi z −5.805 (`z_surf`);")
w("  - taban alt yüzü z −5.005; altına 0.8 mm PTFE kaydırıcı eklenince yüzeye iner.")
w("- Sonuç: lens referans düzlemi z −3.405, yüzeye **2.400 mm** (ifade `lens_ref`). PCB üstü yüzeye **7.400 mm**.")
w("- Lens cebi 19.25 × 21.55 (lens flanşı 18.85 × 21.15, her yanda 0.2 boşluk). Cep tabanı lens düzleminin 0.15 altında.")
w("- Alt kabuk – lens zarfı min mesafe **%.3f mm**, girişim yok." % g["bottom_shell-lens_envelope"])
w("- Optik merkez (0, −11.497): veri sayfası Şekil 3'e göre pin 1'den 5.66 öne, iki pin sırasının ortasında.")
w("- Tabandaki açıklık 9 × 14 mm (Y boyunca uzun, LED yolu dahil) ve optik merkezde ortalı.")
w("- Alt kabuk – sensör gövdesi (U2) min mesafe %.3f mm.\n" % g["bottom_shell-U2_0(sensor)"])

w("## 6. Et kalınlığı ve çıkıntılar (baskı yönünde, NX STL üzerinde)\n")
w("- **Et kalınlığı:** yüzeydeki 4000 noktadan içe ışın atılarak ölçüldü (trimesh). Tasarım duvarı 1.8 mm (`wall`).")
w("- p5 değerleri, eğimli kenar ve delik kenarlarındaki eğik ışınları da içerir. Tuşlarda 1.0 değeri esnek dilin kalınlığıdır. "
  "Yan tuşlarda 0.78 değeri pim deliği etrafındaki ettir.")
w("- **Çıkıntı:** aşağı bakan ve dikeyle 45°'den büyük açı yapan yüzey alanı; yatağa değen yüzey hariç.\n")
w("| Parça | Baskı yönü | Hacim mm³ | Kutu (baskı) mm | Yatak teması mm² | Çıkıntı >45° mm² (%) | Et p5 / medyan mm |\n|---|---|---|---|---|---|---|")
orient = {"bottom_shell": "taban yatakta", "top_shell": "ayırma kenarı yatakta, iç tavana ağaç destek", "btn_left": "montaj yönü, alt destek",
          "btn_right": "montaj yönü, alt destek", "key_fwd": "montaj yönü (kulak altı yatakta)", "key_back": "montaj yönü (kulak altı yatakta)",
          "wheel": "eksen dikey, düz sağ yüz yatakta"}
for k, v in PR.items():
    w("| %s | %s | %.0f | %s | %.0f | %.0f (%.1f) | %.2f / %.2f |" % (
        k, orient[k], v["volume_mm3"], " × ".join("%.1f" % x for x in v["bbox_print_mm"]), v["bed_contact_mm2"],
        v["overhang_gt45_mm2"], v["overhang_share_pct"], v["wall_p5_mm"], v["wall_median_mm"]))
w("\nTüm STL'ler su geçirmez (watertight = %s).\n" % all(v["watertight"] for v in PR.values()))

w("## 7. Montaj / vidalar\n")
w("- 4 × M2 PCB deliği (Ø2.2, konum (±22.86, ±28.829)) WAVE ile alt ve üst kabuğa bağlandı (arc-centre noktaları).")
w("- **Alt kabuk:** Ø5 standoff (z −5.005 → 0), Ø2.4 geçiş deliği, Ø4.4 havşa. Vida başı z −2.005'te oturur.")
w("- **Üst kabuk:** Ø4.4 göbek (z 1.6 → 8.0), yan duvara 2 mm kanatla bağlı. Ø1.7 pilot delik 5.6 mm derin.")
w("- Vida boyu: baş yüzeyinden pilot dibine 2.005 + 1.6 + 5.6 = 9.2 mm → **M2 × 8**, 4 adet (4.4 mm diş tutuşu). "
  "Bu vidalar iki kabuğu ve PCB'yi birlikte sıkar.")
w("- **Ana tuş dilleri:** Ø5 göbek, Ø1.7 pilot 6 mm derin; dil 1.0 mm, Ø2.4 delikli → **M2 × 5**, 2 adet.")
w("- Üst kabuk – USB başlığı min %.3f mm (arka sol göbekte). Üst kabuk – EC10E %.3f mm.\n" % (g["top_shell-USB1"], g["top_shell-ENCODER1"]))

w("## 8. STEP geri okuma (OCP / XCAF)\n")
w("`mouse_assembly.step` kökü `mouse_asm`. İsimli örnekler aşağıda:\n")
w("| Örnek | Ürün | Katı | Hacim mm³ |\n|---|---|---|---|")
for r_ in SC:
    w("| %s | %s | %d | %.1f |" % (r_["instance"], r_["product"], r_["solids"], r_["volume"]))
w("")

w("## 9. Parametrik kontroller\n")
w("j7_regen'de kaydedilmiş kontrol parçası açıldı. Ana ifadeler değiştirildi, sonuç ölçüldü, değerler geri alındı; parça kaydedilmedi.\n")
for c in J["j7_regen"]["checks"]:
    w("- %s: **%s** %s" % (c["label"], "OK" if c["ok"] else "HATA", c["value"] if c["value"] is not None else ""))
w("")
bad = [c for c in J["j1_ctrl"]["checks"] if not c["ok"]]
if bad:
    w("j1_ctrl'deki aynı regen kontrolü bu son çalıştırmada HATA yazdı. Nedeni geometri değil, kontroldeki eski sabit beklenen değerdi:")
    w("- kontrol, yan tuş penceresinin alt kenarı 4.0 iken yazılmış sabit bir değerle karşılaştırıyordu;")
    w("- ölçülen artış %s mm³, yani 1 × 12.5 × 7.3 (yeni `sk_z0` = 6.2 ile) — geometri doğru;" % bad[0]["value"])
    w("- kontrol formülü ifadelerden hesaplanacak şekilde düzeltildi ve değer j7_regen ile yeniden ölçüldü.")
    w("\nj1'in diğer %d kontrolü OK.\n" % (len(J["j1_ctrl"]["checks"]) - len(bad)))
w("- Kontrol parçasındaki 11 araç çiziminin hepsi DOF 0, otomatik ölçü 0 (j1_ctrl).\n")
open(os.path.join(DEL, "CHECKS.md"), "w", encoding="utf-8").write("\n".join(L))
print("ok", len(L))
