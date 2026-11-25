# CHECKS: son ölçüm RV02 (2026-11-26)

Ölçüm kaynağı: teslim edilen STEP dosyaları ve orijinal `mouse_pcb.step`. Montaj `work/04_asm/assemble.py` ile yeniden kuruldu (yan kol pozu 5.15°). Mesafeler 0.01 mm ağdan (`mesh_checks.py`, iki yönlü), basılabilirlik `*_print.stl` üzerinde (`work/06_final/rv02_print.py`, normal 45° kuralı). Bu turda değişmeyen parçalar (bottom_shell, button_L/R, wheel, yoke) için RV01 bağımsız ölçümü geçerli ve öyle işaretlendi.

**Sonuç: A1..A25'ten 22'si PASS, 3'ü FAIL (A15, A17, A18). Ayrıca ana tuşların üst kabuğa takılması ispatlanamadı (süpürme FAIL). Teslim, baskıya hazır değil.**

## Kabul tablosu
| # | ölçülen | sınır | sonuç |
|---|---|---|---|
| A1 | 10 STEP'in hepsi 1 katı, geçerli. Hacimler mm³: bottom 20493.5, top 19573.1, button_L 2674.7, button_R 2655.8, wheel_body 3151.2, axle_pin 50.3, yoke 145.2, dpi 465.7, side_fwd 620.5, side_back 575.7 | n=1, geçerli | PASS |
| A2 | alt yüz Z -5.40, masa -5.85, lens 2.40 (RV01, alt kabuk değişmedi) | -5.85 ±0.05 | PASS |
| A3 | optik prizmada malzeme 0.0000 mm³ (RV01) | 0 | PASS |
| A4 | lens cebinde malzeme 0.0000 mm³ (RV01) | 0 | PASS |
| A5 | ağ mesafeleri: hiçbir parça PCB katısına girmiyor (en küçük tasarım dışı mesafe > 0). Kesin boolean: RV01'de 0.00000 (değişmeyenler); WP-H yeni kollar ve DPI için 0.0 | 0 | PASS |
| A6 | kabuklar: alt 0.995 (EC10E bacak ucu, tasarım 0.99), üst 2.297. Hareketliler: tuşlar 0.52, tekerlek 0.743, pim 1.00, DPI 1.00 (basılı 0.30), yoke 0.42, kollar stopta anahtar gövdesine 0.277 | ≥1.0 / ≥0.25 | PASS |
| A7 | ana nub boşluğu 0.100 (L, R) | 0.05..0.30 | PASS |
| A8 | DPI 0.000; yan kollar 0.100 (ped), merkezde 0.123; ped artık 3.5 x 3.5, plunger 1.2 x 2.9'u Y'de ±0.3 payla örtüyor | 0..0.30 | PASS |
| A9 | stop direği stopta Z 1.510, direk tabanı - 1.51 = 0.80 | 0.75..0.90 | PASS |
| A10 | aks plunger üstünde 0.000; yarık üstü 0.10; stop 1.943°, plunger stroku 0.672 | 0..0.10 / 0.05..0.15 / 0.6..0.8 | PASS |
| A11 | tuş-üst kabuk 0.50, ön ayrım 1.40 (RV01, değişmedi) | 0.40..0.60, ≥1.30 | PASS |
| A12 | tuş stopta (−1.112°): PCB tasarım dışı 0.31; diğer parçalar ≥ 1.51; üst kabuğa 0.212, yaprak kelepçesi hariç (RV01) | hacim 0 | PASS |
| A13 | tekerlek-üst kabuk: dinlenmede 0.370, 0.30 düşük 0.370, **orta tık stopunda (1.943°) 0.303**, yukarı stopta 0.296; alt kabuk 0.783 / stopta 0.445 | ≥0.30 | PASS (RV01'de 0.000 idi) |
| A14 | tekerlek üstü 20.395 − kabuk 17.254 = 3.14 | 2.5..4.0 | PASS |
| A15 | üst kabuk: buton ayrım çizgilerinde ve tekerlek penceresi ön kenarında ince kenar, örneklerin %2.2'si < 1.6, min 0.001 (RV01; üst kabukta bu bölge değişmedi) | ≥1.6 | **FAIL** (F-8) |
| A16 | üst kabuk min Z 1.000, alt düzlemler hepsi Z 1.000 | tam | PASS |
| A17 | bkz. basılabilirlik tablosu: arka ayak tavanı köprüsü 11.0, çentik tepeleri 13 mm dış köprü, yan kollarda tabla teması 0 | §4.8 | **FAIL** (F-4, F-5, F-7) |
| A18 | Ø4.5 takım yolunda TS vida başına 1.052 mm³ (kovan Ø4.4); Ø4.4 yolda 0; PCB vidaları üstten açık (RV01, alt kabuk değişmedi) | Ø4.5'te 0 | **FAIL** (F-9, spec çelişkisi) |
| A19 | PCB pilot Ø1.6 x 4.6; insert Ø3.2 x 4.0 (x3); yaprak pilotu Ø1.6 x 6.0 (RV01) | listedeki gibi | PASS |
| A20 | kanal 4.0, taban -3.90 (çıkışta -4.05 çukur), çıkış Ø3.8, X 46.5 (RV01) | listedeki gibi | PASS |
| A21 | yuva derinliği 0.35, kenara ≥ 3.3, 3 vida başı örtülü (RV01) | listedeki gibi | PASS |
| A22 | kollar 5.15° stopta: alt kabuk 0.150 (yatak), üst kabuk 0.169, PCB tasarım dışı 0.277; stop yüzü kart kenarına (X 14.478) oturuyor | hacim 0, ≥0.15 | PASS |
| A23 | üst kabuk + tuşlar + DPI 15 mm'den indirildi: kollar, tekerlek, yoke, PCB ile 0 çarpışma. Yalnız sağ dudakta kabuk-kabuk sürtmesi: 55 nokta, X 69.2..69.4, Z 1.0..2.5, son konumdan 0.69 yukarıda (0.1 esneme) | çarpışma yok | PASS (küçük not) |
| A24 | 120.00 x 63.50 x 39.93 | 118-126 x 62-68 x 38-42 | PASS |
| A25 | alt yüz ve üst kabuk kenarında pah var (RV01) | var | PASS |

## Hareket (stop pozlarında, ağ)
| hareket | ölçülen |
|---|---|
| ana tuş L/R, −1.112° | nub stroku 0.776, plunger 0.676, uç 1.149 iner, direk Z 1.510'a oturur |
| orta tık, 1.943° | plunger 0.672, tekerlek tepesi 0.204 iner, üst kabuğa 0.303, yoke yarığında aks 0.0 (tasarım stopu) |
| yan kol fwd/back, 5.15° | nub stroku merkezde 0.778 (en derin ped noktası 0.809, WP-H), anahtar gövdesine 0.277 |
| DPI, 0.70 basış | anahtar gövdesine 0.30, kılıfa 0.15, tekerleğe 0.372 |

## Çakışma (dinlenme, iki yönlü ağ mesafesi)
Tasarım temasları dışında bütün parça çiftleri > 0: tekerlek-yoke 0.98, aks-yoke 0.10 (yarık üstü), tekerlek-DPI 0.564, kol-üst kabuk 0.133 (fwd) / 0.164 (back), kol-alt kabuk 0.15 (yatak). Sıfır olanlar yalnız tasarım temasları: kabuk ayrım düzlemi, yoke yuvası, yaprak kelepçesi, pim-tekerlek presi. Kesin OCC boolean'ı B-spline kabuklarda tamamlanmıyor; karar ağ mesafelerine dayanıyor (RV01'de biten çiftler ağ ile aynı çıktı).

## Montaj / takma süpürmeleri
| adım | sonuç |
|---|---|
| tekerlek altıgeni EC10E'ye kayar (yalnız PCB) | 0 çarpışma, PASS |
| PCB + tekerlek birlikte alt kabuğa iner | 0, PASS |
| yoke, tekerlek takılıyken yuvasına iner | 0, PASS |
| çelik pim yoke yarığından −X 20 mm itilir | 0, PASS |
| DPI kapağı üst kabuğa alttan | 0, PASS |
| **ana tuş L/R üst kabuğa, YZ düzleminde 12 düz yön** | **her yönde 1636..7999 çarpışma; L-yolunda 918 / 936. FAIL** |
| yan kol yatağa dik iner | fwd 35 / back 29 nokta (çentik tırnağı 0.3 taşıyor), zorla takma |
| üst kabuk dik iner | sağ dudakta 0.1 esneme (A23 notu) |

## Basılabilirlik (*_print.stl, baskı yönünde)
| parça | tabla teması mm² | >45° çıkıntı mm² (hepsi) | not | sonuç |
|---|---|---|---|---|
| bottom_shell | 6249 | 1365 | arka ayak tavanı 36.0 x 11.0 düz köprü (sınır 10); diğerleri köprü ≤ 6.4 veya pah | **FAIL** (F-4) |
| top_shell | 512 | 3411 | iç tavan/ped/ray/kılıf ağaç destekte (beyan edilen bölge); çentik tepeleri dışta 13 mm köprü (RV01, değişmedi) | **FAIL** (F-5) |
| button_L / R | 5.1 | 1366 / 1377 | panel altı ve yaprak beyan edilen destek bölgesinde; brim gerekli | PASS (not) |
| wheel_body | 356 | 3.1 | Ø2 kör delik tavanı, köprü 2.0 | PASS |
| wheel_yoke | 119 | 3.4 | kenar pahı | PASS |
| dpi_button | 8.75 | **0.0** | RV01'de 26 mm² idi; brim önerilir | PASS |
| side_btn_fwd / back | **0.0** | **209.5 / 207.9** | düz tabla yüzü yok; WP-H kendi yöntemiyle 50.9 / 49.1 bildirdi, bu ölçüm RV01 yöntemi (45.5° normal) | **FAIL** (F-7) |

## İnceleme bulgularının durumu (RV01 → RV02)
| bulgu | sahibi | durum | yeniden ölçülen |
|---|---|---|---|
| tekerlek orta tıkta raya sürtüyor (F-1 + master) | WP-E | **KAPANDI** | 0.000 → 0.303, içeride örnek 0 |
| ana tuşlar takılamıyor | MASTER | **AÇIK** | 12 yönün hepsinde çarpışma, L-yolu 918/936 |
| tekerlek montaj sırası | MASTER | **KAPANDI (belge)** | yeni sıra 4 adımda 0 çarpışma; README'de. DESIGN_SPEC §3 ve pim Ø2.03 boşluklu geçme yapılmadı |
| F-2 yan ped Y | MASTER | KAPANDI (WP-H parçasında) | ped 3.5 x 3.5; master.py sabiti hâlâ 2.5 |
| F-3 yan kol fazla strok | WP-H | **KAPANDI** | 0.858 → 0.809 (en derin), 0.778 (merkez) |
| F-4 arka ayak köprüsü | MASTER | **AÇIK** | 36.0 x 11.0 |
| F-5 çentik tepesi köprüsü | MASTER | **AÇIK** | değişmedi |
| F-6 DPI flanş çıkıntısı | WP-H | **KAPANDI** | 26 → 0.0 mm² |
| F-7 yan kol baskısı | WP-H | **AÇIK** | tabla 0.0, çıkıntı 209 mm² |
| F-8 üst kabuk ince kenar | MASTER | **AÇIK** | değişmedi |
| F-9 kovan Ø4.4 / takım Ø4.5 | MASTER | **AÇIK** | 1.052 mm³ |
| ped-gövde 0.212 (küçük) | WP-H | KAPANDI | 0.277 |
| kol yatağa takma (küçük) | WP-D | açık | 35 / 29 nokta |
| üst kabuk dudak sürtmesi (küçük) | WP-D | açık | 55 nokta, 0.1 |
| F-10..F-20 (küçük) | çeşitli | açık (F-19 kapandı: hacimler STEP'ten) | değişmedi |
