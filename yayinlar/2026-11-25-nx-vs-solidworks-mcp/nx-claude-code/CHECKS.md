# CHECKS – NX fare kabuğu (ölçülmüş değerler)

Tüm değerler ölçüldü. Bir kısmı NX 2206 içinde alındı: NXOpen `AskMinimumDist`, Simple Interference, Clearance Analysis. Kalanı NX'ten alınan STL / STEP üzerinde Python (trimesh, OCP) ile hesaplandı. Ham sonuçlar: `NX/results/*.json`.

Koordinat sistemi:
- Kart merkezi = orijin (KiCad STEP'i x −39.370, y +45.593 kaydırıldı).
- +Y = farenin önü.
- Kart alt yüzü z = 0, bileşen oturma düzlemi z = 1.595.

## 1. Journal özetleri

| Journal | Sonuç | Kontrol | Hata |
|---|---|---|---|
| j1_ctrl | FAIL | 32 | 1 |
| j2_bottom | PASS | 9 | 0 |
| j3_top | PASS | 12 | 0 |
| j4_keys | PASS | 20 | 0 |
| j5_wheel | PASS | 6 | 0 |
| j6_asm | PASS | 9 | 0 |
| j7_regen | PASS | 4 | 0 |

j1_ctrl'deki tek HATA'nın açıklaması §9'da.

## 2. Girişim (interference)

NX Clearance Analysis (tüm bileşenler, tam hesap, bölge 0):

| Çift | Tür | Yorum |
|---|---|---|
| AXLE_PIN – PCB | Touch | Ø2 pim SW3 plungerına oturuyor (orta tık, istenen temas) |
| AXLE_PIN – WHEEL | Hard | Ø2.0 pim, Ø1.95 tekerlek deliğine pres geçme (istenen) |
| BOTTOM_SHELL – PCB | Touch | PCB 4 standoff üzerinde (istenen temas) |
| BOTTOM_SHELL – TOP_SHELL | Touch | kabuklar z = −1.0 ayırma düzleminde birbirine oturuyor |
| BTN_LEFT – TOP_SHELL | Touch | tuş dili, üst kabuktaki vida göbeğine sıkışıyor (M2) |
| BTN_RIGHT – TOP_SHELL | Touch | tuş dili, üst kabuktaki vida göbeğine sıkışıyor (M2) |

Gövde-gövde Simple Interference uygulandı: birbirine 1.5 mm'den yakın bütün çiftler, PCB'nin 69 gövdesi tek tek ele alındı. 58 çift incelendi. Katı örtüşme yalnız şurada: wheel–axle_pin 0.667 mm³ (pres geçme).

| A | B | min mesafe (mm) | sonuç |
|---|---|---|---|
| bottom_shell | top_shell | 0.000 | OnlyEdgesOrFacesInterfere |
| bottom_shell | pcb:PCB | 0.000 | OnlyEdgesOrFacesInterfere |
| top_shell | btn_left | 0.000 | OnlyEdgesOrFacesInterfere |
| top_shell | btn_right | 0.000 | OnlyEdgesOrFacesInterfere |
| wheel | axle_pin | 0.000 | InterferenceExists |
| axle_pin | pcb:SW3 | 0.000 | OnlyEdgesOrFacesInterfere |
| top_shell | pcb:PCB | 0.090 | NoInterference |
| lens | pcb:U2_0 | 0.095 | NoInterference |
| lens | pcb:U2_1 | 0.095 | NoInterference |
| lens | pcb:U2_2 | 0.095 | NoInterference |
| lens | pcb:U2_3 | 0.095 | NoInterference |
| lens | pcb:U2_4 | 0.095 | NoInterference |
| lens | pcb:U2_5 | 0.095 | NoInterference |
| lens | pcb:U2_6 | 0.095 | NoInterference |
| lens | pcb:U2_7 | 0.095 | NoInterference |
| lens | pcb:U2_8 | 0.095 | NoInterference |
| lens | pcb:U2_9 | 0.095 | NoInterference |
| lens | pcb:U2_10 | 0.095 | NoInterference |
| lens | pcb:U2_11 | 0.095 | NoInterference |
| lens | pcb:U2_12 | 0.095 | NoInterference |
| lens | pcb:U2_13 | 0.095 | NoInterference |
| lens | pcb:U2_14 | 0.095 | NoInterference |
| lens | pcb:U2_15 | 0.095 | NoInterference |
| lens | pcb:U2_16 | 0.095 | NoInterference |
| bottom_shell | axle_pin | 0.100 | NoInterference |
| top_shell | hinge_f | 0.100 | NoInterference |
| top_shell | hinge_b | 0.100 | NoInterference |
| key_fwd | hinge_f | 0.100 | NoInterference |
| key_back | hinge_b | 0.100 | NoInterference |
| wheel | pcb:ENCODER1 | 0.100 | NoInterference |
| bottom_shell | lens | 0.150 | NoInterference |
| lens | pcb:PCB | 0.170 | NoInterference |
| top_shell | pcb:SW4 | 0.200 | NoInterference |
| btn_left | pcb:SW1 | 0.200 | NoInterference |
| btn_right | pcb:SW2 | 0.200 | NoInterference |
| key_fwd | pcb:SW5 | 0.200 | NoInterference |
| key_back | pcb:SW6 | 0.200 | NoInterference |
| top_shell | pcb:SW2 | 0.214 | NoInterference |
| top_shell | pcb:SW1 | 0.214 | NoInterference |
| top_shell | key_fwd | 0.300 | NoInterference |
| top_shell | key_back | 0.300 | NoInterference |
| key_fwd | pcb:PCB | 0.315 | NoInterference |
| key_back | pcb:PCB | 0.315 | NoInterference |
| top_shell | pcb:USB1 | 0.350 | NoInterference |
| bottom_shell | wheel | 0.400 | NoInterference |
| btn_left | btn_right | 0.600 | NoInterference |
| top_shell | pcb:SW6 | 0.742 | NoInterference |
| btn_left | pcb:ENCODER1 | 0.833 | NoInterference |
| bottom_shell | pcb:USB1 | 1.000 | NoInterference |
| btn_left | key_fwd | 1.200 | NoInterference |
| bottom_shell | pcb:SW2 | 1.300 | NoInterference |
| bottom_shell | pcb:SW3 | 1.300 | NoInterference |
| bottom_shell | pcb:SW5 | 1.300 | NoInterference |
| bottom_shell | pcb:SW6 | 1.300 | NoInterference |
| bottom_shell | pcb:SW4 | 1.300 | NoInterference |
| bottom_shell | pcb:SW1 | 1.300 | NoInterference |
| bottom_shell | pcb:ENCODER1 | 1.300 | NoInterference |
| top_shell | pcb:C300 | 1.440 | NoInterference |

## 3. Tuş nub – plunger boşlukları (dinlenme)

Omron D2F (pim plunger) değerleri:
- çalışma konumu OP 5.5 ± 0.3 (oturma düzleminden);
- ön hareket PT ≤ 0.5;
- aşırı hareket OT ≥ 0.25.

STEP'te plunger üstü z = 7.595 = serbest konum (OP + PT).

| Tuş | Anahtar | Ölçülen boşluk (mm) | Tıka kadar yol (boşluk + PT ≤ 0.5) |
|---|---|---|---|
| btn_left | SW1 sol tık | 0.200 | ≤ 0.70 |
| btn_right | SW2 sağ tık | 0.200 | ≤ 0.70 |
| top_shell(DPI nub) | SW4 DPI (üst kabuk dili) | 0.200 | ≤ 0.70 |
| key_fwd | SW5 yan ileri | 0.200 | ≤ 0.70 |
| key_back | SW6 yan geri | 0.200 | ≤ 0.70 |
| tekerlek pimi | SW3 orta tık | 0.000 (oturuyor) | ≤ 0.50 |

Diğer tuş boşlukları:
- sol/sağ tuş – üst kabuk yan boşluğu: 0.6 (`btn_gap`);
- yan tuş – üst kabuk (menteşe kulakları): 0.300 / 0.300 mm;
- tuş dili: 1.0 mm esnek dil, serbest boyu ≈ 6 mm.

## 4. Tekerlek ve orta tık

- Tekerlek Ø22 × 7. Ekseni EC10E mili ekseninde (y 17.693, z 8.595).
- Sol göbekteki Ø3.4 D-düz uç, EC10E deliğine (STEP'te Ø3.6) 4.6 mm girer.
- Sağdaki Ø2 × 14 çelik pim SW3 plungerının üstüne oturur. Pimi alt kabuktaki çatal tutar (yarık 2.2, üstte 0.15 tırnak).
- Dinlenme konumu:
  - tekerlek – EC10E radyal boşluk 0.100 mm;
  - tekerlek – alt kabuk 0.400 mm, tekerlek – üst kabuk 2.791 mm;
  - pim – çatal 0.100 mm.
- Basılı poz: NX'te tekerlek ve pim bileşenleri, enkoder deliği ortasındaki pivot etrafında 2.033° döndürüldü. Bu durumda pim SW3 üzerinde 0.75 mm aşağıdadır (PT 0.5 + OT 0.25). Ölçülenler:
  - tekerlek – EC10E: min 0.0171 mm, NoInterference;
  - tekerlek – alt kabuk: min 0.3416 mm, NoInterference;
  - tekerlek – üst kabuk: min 2.7914 mm, NoInterference;
  - pim – çatal: min 0.1000 mm, NoInterference;
  - tekerlek – PCB: 2.3187 mm;
  - pim – SW3: InterferenceExists, 2.378 mm³. Bu plungerın 0.75 mm basılmasıdır; STEP'teki plunger rijit bir yer tutucu olduğu için beklenen sonuçtur.
- Tekerleğin kabuk üstündeki çıkıntısı **2.29 mm**: tekerlek tepesi z 19.595, kabuk dış yüzü (x 0, y 17.693) z 17.304.
- Gereken eğim 2.03°, enkoder deliğinin izin verdiği eğimin (2·0.1/4.6 rad = 2.49°) altında.

## 5. Sensör (PMW3360 + LM19-LSI)

- Veri sayfası (PMW3360, Şekil 4):
  - PCB üstü → yüzey: 7.40;
  - lens flanşının altı (referans düzlemi) → yüzey: Z = 2.40 (2.2–2.6).
- Modeldeki yığın:
  - bileşen oturma düzlemi z 1.595 → seyir yüzeyi z −5.805 (`z_surf`);
  - taban alt yüzü z −5.005; altına 0.8 mm PTFE kaydırıcı eklenince yüzeye iner.
- Sonuç: lens referans düzlemi z −3.405, yüzeye **2.400 mm** (ifade `lens_ref`). PCB üstü yüzeye **7.400 mm**.
- Lens cebi 19.25 × 21.55 (lens flanşı 18.85 × 21.15, her yanda 0.2 boşluk). Cep tabanı lens düzleminin 0.15 altında.
- Alt kabuk – lens zarfı min mesafe **0.150 mm**, girişim yok.
- Optik merkez (0, −11.497): veri sayfası Şekil 3'e göre pin 1'den 5.66 öne, iki pin sırasının ortasında.
- Tabandaki açıklık 9 × 14 mm (Y boyunca uzun, LED yolu dahil) ve optik merkezde ortalı.
- Alt kabuk – sensör gövdesi (U2) min mesafe 5.150 mm.

## 6. Et kalınlığı ve çıkıntılar (baskı yönünde, NX STL üzerinde)

- **Et kalınlığı:** yüzeydeki 4000 noktadan içe ışın atılarak ölçüldü (trimesh). Tasarım duvarı 1.8 mm (`wall`).
- p5 değerleri, eğimli kenar ve delik kenarlarındaki eğik ışınları da içerir. Tuşlarda 1.0 değeri esnek dilin kalınlığıdır. Yan tuşlarda 0.78 değeri pim deliği etrafındaki ettir.
- **Çıkıntı:** aşağı bakan ve dikeyle 45°'den büyük açı yapan yüzey alanı; yatağa değen yüzey hariç.

| Parça | Baskı yönü | Hacim mm³ | Kutu (baskı) mm | Yatak teması mm² | Çıkıntı >45° mm² (%) | Et p5 / medyan mm |
|---|---|---|---|---|---|---|
| bottom_shell | taban yatakta | 12428 | 60.5 × 117.0 × 15.0 | 5896 | 113 (0.8) | 1.45 / 1.80 |
| top_shell | ayırma kenarı yatakta, iç tavana ağaç destek | 15484 | 62.9 × 117.0 × 32.0 | 603 | 3406 (17.9) | 1.35 / 1.80 |
| btn_left | montaj yönü, alt destek | 2444 | 30.1 × 63.5 × 16.0 | 7 | 1293 (41.0) | 1.00 / 1.80 |
| btn_right | montaj yönü, alt destek | 2444 | 30.1 × 63.5 × 16.0 | 7 | 1293 (41.0) | 1.00 / 1.80 |
| key_fwd | montaj yönü (kulak altı yatakta) | 256 | 14.4 × 7.2 × 11.7 | 10 | 50 (12.7) | 0.89 / 3.00 |
| key_back | montaj yönü (kulak altı yatakta) | 311 | 14.8 × 11.0 × 11.7 | 10 | 59 (12.5) | 1.02 / 2.50 |
| wheel | eksen dikey, düz sağ yüz yatakta | 2674 | 22.0 × 22.0 × 15.5 | 326 | 17 (1.1) | 1.52 / 7.00 |

Tüm STL'ler su geçirmez (watertight = True).

## 7. Montaj / vidalar

- 4 × M2 PCB deliği (Ø2.2, konum (±22.86, ±28.829)) WAVE ile alt ve üst kabuğa bağlandı (arc-centre noktaları).
- **Alt kabuk:** Ø5 standoff (z −5.005 → 0), Ø2.4 geçiş deliği, Ø4.4 havşa. Vida başı z −2.005'te oturur.
- **Üst kabuk:** Ø4.4 göbek (z 1.6 → 8.0), yan duvara 2 mm kanatla bağlı. Ø1.7 pilot delik 5.6 mm derin.
- Vida boyu: baş yüzeyinden pilot dibine 2.005 + 1.6 + 5.6 = 9.2 mm → **M2 × 8**, 4 adet (4.4 mm diş tutuşu). Bu vidalar iki kabuğu ve PCB'yi birlikte sıkar.
- **Ana tuş dilleri:** Ø5 göbek, Ø1.7 pilot 6 mm derin; dil 1.0 mm, Ø2.4 delikli → **M2 × 5**, 2 adet.
- Üst kabuk – USB başlığı min 0.350 mm (arka sol göbekte). Üst kabuk – EC10E 9.028 mm.

## 8. STEP geri okuma (OCP / XCAF)

`mouse_assembly.step` kökü `mouse_asm`. İsimli örnekler aşağıda:

| Örnek | Ürün | Katı | Hacim mm³ |
|---|---|---|---|
| PCB | pcb | 69 | 7442.6 |
| BOTTOM_SHELL | bottom_shell | 1 | 12457.4 |
| TOP_SHELL | top_shell | 1 | 15494.7 |
| BTN_LEFT | btn_left | 1 | 2444.4 |
| BTN_RIGHT | btn_right | 1 | 2444.1 |
| KEY_FWD | key_fwd | 1 | 256.0 |
| KEY_BACK | key_back | 1 | 311.0 |
| WHEEL | wheel | 1 | 2674.5 |
| AXLE_PIN | axle_pin | 1 | 44.0 |
| HINGE_PIN_F | hinge_pin | 1 | 21.6 |
| HINGE_PIN_B | hinge_pin | 1 | 21.6 |
| LM19_LSI_LENS_ENVELOPE | lm19_lens_envelope | 1 | 1157.9 |

## 9. Parametrik kontroller

j7_regen'de kaydedilmiş kontrol parçası açıldı. Ana ifadeler değiştirildi, sonuç ölçüldü, değerler geri alındı; parça kaydedilmedi.

- regen: skf_y1 +1 grows T_SKF by 1 x (40+sk_x) x (sk_z1-sk_z0): **OK** [657.0000000000002, 748.2500000000003, 91.25]
- regen: palm height 31->33 and wall 1.8->2.0 change HOUSING, nominal restores it: **OK** [33103.45314939882, 33314.14746810519, 36790.62547928122, 33103.45314939882]
- regen: whl_d 22->24 lengthens the wheel slot by 1 mm (rear end at ax_y-whl_d/2-0.8): **OK** [8837.481015000001, 9196.626014999998]
- ctrl feature errors none: **OK** 

j1_ctrl'deki aynı regen kontrolü bu son çalıştırmada HATA yazdı. Nedeni geometri değil, kontroldeki eski sabit beklenen değerdi:
- kontrol, yan tuş penceresinin alt kenarı 4.0 iken yazılmış sabit bir değerle karşılaştırıyordu;
- ölçülen artış [657.0, 748.2500000000003] mm³, yani 1 × 12.5 × 7.3 (yeni `sk_z0` = 6.2 ile) — geometri doğru;
- kontrol formülü ifadelerden hesaplanacak şekilde düzeltildi ve değer j7_regen ile yeniden ölçüldü.

j1'in diğer 31 kontrolü OK.

- Kontrol parçasındaki 11 araç çiziminin hepsi DOF 0, otomatik ölçü 0 (j1_ctrl).
