# Ergonomik Oyuncu Faresi Mekanik Tasarımı — Mühendislik Planı ve Doğrulama Raporu

**Girdi:** `C:\scan-canli\mouse\GIRDI\mouse_pcb.step` (yalnızca bu STEP girdisi kullanılmıştır)  
**CAD / Kernel:** Siemens NX 2206 (parametrik NXOpen Python journal `build_mouse.py`, `nxh` / `nxf` / `nxa`)  
**Dış Boyutlar:** ~116.0 mm (U) × 63.6 mm (G) × 39.4 mm (Y, PTFE ayaklar dâhil) · ~53 g tahmini toplam ağırlık (ABS + PCB)

---

## 1. PCB Arayüz Haritası (`mouse_pcb.step` — birebir koordinat sistemi, mm)

Tüm 7 mekanik parça, montajda sıfır dönüşüm hatası için `mouse_pcb.step` koordinat sisteminde yerinde tasarlanmıştır:
- **Simetri Ekseni (`X_C`):** `X = 39.370 mm` (`PCB X ∈ [14.478, 64.262]`, genişlik `49.784 mm`)
- **Ön / Arka (`+Y` = Burun, `-Y` = Kuyruk):** `PCB Y ∈ [-76.454, -14.732]` (uzunluk `61.722 mm`)
- **Kart Kalınlığı ve Pinler:** `Z ∈ [0.000, 1.510]`, lehimli bacaklar alt tarafta `Z = -1.905 mm`'ye kadar iner.
- **4× M2 PCB Montaj Deliği (`Ø2.2 mm`):** `(16.510, -16.764)`, `(62.230, -16.764)`, `(16.510, -74.422)`, `(62.230, -74.422)`
- **6× Omron D2F Anahtar Pistonu (`Z_top = 7.595 mm`):**
  - `LMB (S58)`: `(20.320, -23.530)` — Sol tık
  - `RMB (S09)`: `(58.420, -23.530)` — Sağ tık (LMB ile tam simetrik)
  - `MMB (S12)`: `(50.800, -27.975)` — Tekerlek sağ miliyle doğrudan tahrikli orta tık
  - `DPI (S48)`: `(40.040, -43.180)` — Tekerlek arkası üst DPI tuşu
  - `M5 İleri (S37)`: `(20.990, -50.800)` — Sol yan başparmak ileri tuşu (dikey PCB anahtarı)
  - `M4 Geri (S38)`: `(20.990, -68.580)` — Sol yan başparmak geri tuşu (dikey PCB anahtarı)
- **Alps EC10E Rotary Encoder (`S59`):** `Ø3.60 mm` boş mil ekseni `+X` boyunca `(Y = -27.900, Z = 8.595)`, en yüksek gövde noktası `Z = 12.595 mm`.
- **PMW3360 Optik Sensör (`S16`):** Merkez `(39.370, -56.520)` — fare burnundan `%45.3` geride (espor merkezli sensör konumu); 16× DIP pin sırası `X = 33.77..34.27` ve `44.47..44.97`.
- **4-Pin USB Başlık (`S46`):** Arka-sol `(19.06..29.22, -75.95..-73.41, Z_max = 10.135 mm)`; kabuk içinde >16.5 mm üst boşluk ve ön burunda `Ø4.2 mm` ayrım-hattı USB kablo çıkışı.

---

## 2. Mekanik Mimari ve Parça Listesi (7 Parça + PCB Montajı)

| # | Parça Dosyası | İşlev ve Öne Çıkan Mekanik Özellikler | Hacim (mm³) | Betti (`b0, b1, b2`) |
|---|---|---|---:|---|
| 1 | `mouse_base.prt` / `.step` | Alt şasi (`Z ≤ 2.5 mm`, `1.8 mm` et, iç taban `Z = -2.6 mm` tüm PCB pinlerini 0.70 mm geçer). 4× `Ø4.0 mm` PCB yükseltme burcu (`Z = 0.000`, `Ø1.6 mm` M2 pilot), 2× sensör yanı destek ayağı, PMW3360 optik penceresi, `Ø23 mm` tekerlek alt oluğu, PCB yarığı içinden yükselen sağ tekerlek mil kılavuz çatalı, 3× PTFE ayak yuvası (altında gizli 4× havşalı M2 gövde vidası), 3× çevre hizalama tırnağı, ön USB kablo yarım çıkışı. | 14,242.3 | `(1, 5, 0)` |
| 2 | `mouse_top_shell.prt` / `.step` | Tek ana `Through Curves` 3B serbest yüzey kubbesi + `R5.5 / R1.8` radyüs + `1.8 mm` kapalı `Shell` + `Z = 2.5 mm` ayrım düzlemiyle alt şasiyle **0.000 mm basamaksız** birleşen ergonomik üst kabuk. Bağımsız esneyen yarık LMB/RMB tetikleri (1.05 mm yarık + 1.8 mm ön etek boşluğu), LMB/RMB altından `Z = 7.650 mm`'ye inen piston vurucu ayakları (`0.055 mm` nominal boşluk), tekerlek ve DPI pencereleri, 2× sol başparmak penceresi, 3× iç menteşe yatağı (`Ø2.2 mm` eş eksenli delik), 4× M2 vida kulesi (ön ikisi sabit orta burun köprüsünde — LMB/RMB hareketini kilitlemez). | 19,207.4 | `(1, 7, 0)` |
| 3 | `mouse_scroll_wheel.prt` / `.step` | `Ø23.0 × 7.4 mm` 24 çentikli dokulu tekerlek + 5 kollu hafifletilmiş göbek. Sol tarafta Alps EC10E `Ø3.60 mm` boş miline `0.05 mm` boşlukla geçen `Ø3.50 mm` tahrik mili; sağ tarafta `Ø1.90 mm` (`R = 0.95 mm`) MMB tahrik mili (`Z_alt = 8.595 - 0.95 = 7.645 mm`, `SW S12` pistonunun tam `0.050 mm` üzerinde). | 1,914.1 | `(1, 5, 0)` |
| 4 | `mouse_dpi_button.prt` / `.step` | Kabuk eğimine uyumlu `24°` açılı üst kapak (`0.3 mm` çevresel boşluk), kabuk içinde düşmeyi önleyen alt flanş (`Z = 18.8..20.0 mm`, iç tavanla tam boşluklu) ve `SW S48` pistonuna `0.67 mm` ofsetle tam inen vurucu sap (`Z = 7.650 mm`). | 313.4 | `(1, 0, 0)` |
| 5 | `mouse_thumb_fwd.prt` / `.step` | **90° Dirsek-Kol (Bell-Crank) M5 İleri Başparmak Tuşu:** Yan duvar penceresinden `~1.8 mm` taşan ergonomik tuş yüzeyi, `(X = 14.8, Z = 11.8)` boylamsal ekseninde `Ø1.95 mm` entegre pimlerle kabuk yataklarında dönerek yatay `+X` başparmak basışını dikey `-Z` hareketine (~1:1 kaldıraç oranı) çevirir ve `SW S37` pistonuna (`Z = 7.650 mm`) tam basar. | 489.7 | `(1, 0, 0)` |
| 6 | `mouse_thumb_back.prt` / `.step` | **90° Dirsek-Kol (Bell-Crank) M4 Geri Başparmak Tuşu:** M5 ile aynı kinematik yapı; `SW S38` pistonunu (`20.990, -68.580, Z = 7.650`) tahrik ederken arka-soldaki 4-pin USB başlığından (`Y ≤ -73.41, X ≥ 19.06`) >2.5 mm emniyetle kaçar. | 526.4 | `(1, 0, 0)` |
| 7 | `mouse_skates.prt` / `.step` | `0.75 mm` kalınlığında, kenarları `0.25 mm` pahlı 3 parça virgin PTFE kaydırıcı ayak (ön, arka ve PMW3360 sensör halkası; tabandan `0.30 mm` taşar). | 515.8 | `(3, 1, 0)` |

---

## 3. Doğrulama Sonuçları (NX 2206 Parasolid + Resmi STEP Kapısı)

1. **NX Examine Geometry:** 7 parçanın tamamında 11/11 denetim `0` hata (`body_ok = true`, `feature_errors = {}`).
2. **NX Parasolid Exact Clearance Analysis (`mouse_asm.prt`, 8 bileşen + 69 PCB katısı):**
   - **Mekanik çakışma (`Hard`):** **0** (`hard_interferences_mech = []`)!
   - **Planlı temas (`Touch`):** Yalnızca `MOUSE_BASE × MOUSE_TOP_SHELL` (ayrım yüzeyi `Z = 2.500 mm`) ve `MOUSE_BASE × PCB_GIRDI_PCB` (4× PCB yükseltme burcu `Z = 0.000 mm`).
   - *(Not: `ALPS_EC10E × PCB_GIRDI_PCB` çifti doğrudan girdi dosyası `mouse_pcb.step` içindeki lehim bacağı çakışmasıdır.)*
3. **Resmi STEP Geçerlilik Kapısı (`validate_step.py`):** 7/7 STEP dosyası `exit=0`, `valid=True`, beklenen tam Betti topolojisi ile geçti.

---

## 4. Dosya Yapısı (`C:\scan-canli\mouse\tasarim\`)

- `build_mouse.py` — Tüm 7 parçayı, montajı ve STEP çıktısını tek komutta yeniden üreten parametrik NXOpen journal
- `plan.md` — Bu mühendislik raporu
- `result.json` & `step_gate.json` — NX Examine Geometry, Parasolid Clearance ve STEP kapı raporları
- `prt/` — Native Siemens NX 2206 parçaları (`mouse_asm.prt`, `mouse_mech_asm.prt`, `mouse_pcb_ref.prt`, `mouse_*.prt`)
- `step/` — Bireysel parça STEP dosyaları + `mouse_assembly_full.step` (PCB'li tam montaj) + `mouse_mechanical_only.step`
- `views/` — Blender Cycles stüdyo, X-Ray (şeffaf kabuk + PCB içi) ve patlatılmış montaj render'ları
