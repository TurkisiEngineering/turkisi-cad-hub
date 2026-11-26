# DIY oyuncu faresi kabuğu: Siemens NX 2206 (yerel) sürümü

**Toplam süre:** 01:01 → 03:01, yaklaşık 2 saat. Buna bir Claude Code çökmesi ve yeniden başlatma da dahil. Başlangıç zamanı `NX/results/START_EPOCH.txt` dosyasında.

Bu teslim, `mouse_pcb.step` girdisinden (SHA-256 `da66ded6…f439` doğrulandı) sıfırdan, **yerel NX 2206** ile kuruldu.
Modelleme başsız (headless) NXOpen Python journal'larıyla yapıldı. Parçaların hepsi geçmişli (history) ve parametriktir;
adlandırılmış ifadeler kullanıldı. Kurgu yukarıdan aşağıya: bir kontrol parçası ve WAVE bağlantıları.

## Klasör

| Yol | İçerik |
|---|---|
| `mouse_assembly_step.zip` | Montaj STEP (AP214), zip içinde: PCB + tüm parçalar, isimli bileşenler (+ pimler, LM19-LSI lens zarfı) |
| `STL/*.stl` | Basılan her parça için bir STL, **baskı yönünde** (z = 0 yatak) |
| `NX/nx_prt.zip` | Bütün NX 2206 `.prt` dosyaları: `mouse_asm.prt` (üretim montajı), `mouse_design.prt` (tasarım montajı + kontrol parçası) ve parçalar. Aynı klasöre açın, montaj bileşenleri yanındaki dosyalardan yüklenir |
| `NX/journals/` | Modeli yeniden üreten journal'lar (`j1_ctrl` … `j6_asm`) |
| `NX/results/` | Her journal'ın ölçüm sonuçları (JSON) |
| `renders/` | Ara ve son kontrol render'ları |
| `renders/blender/` | Blender 5.1 Cycles stüdyo render'ları (2560 × 1440): kahraman, üst, yan, alt, X-ray, patlatma, tekerlek yakın plan, baskı plakası. Betikler: `NX/journals/blender/` (`mesh.py` montaj STEP'ini inceltip gruplar, `render_bl.py` sahneyi kurar) |
| `CHECKS.md` | Ölçülmüş bütün kontroller |

## Parçalar

| Parça | Dosya | Not |
|---|---|---|
| Üst kabuk | `top_shell` | Avuç sırtı, DPI dili (uzun konsol, SW4 nub'ı), tekerlek yarığı, 4 PCB sıkma göbeği, 2 tuş dili göbeği, yan tuş menteşe kulakları, arka kablo çıkışı Ø4.5 |
| Alt kabuk | `bottom_shell` | Taban 1.8 mm, 4 standoff + M2 havşa, lens cebi + 9×14 açıklık, tekerlek pimi çatalı (PCB çentiğinden yukarı çıkar) |
| Sol / sağ tuş | `btn_left`, `btn_right` | Kabuğun ön kısmı; Ø3 nub → SW1/SW2, 1.0 mm esnek dil, M2×5 ile üst kabuğa |
| Yan tuş ileri / geri | `key_fwd`, `key_back` | Sol yan pencere; kol SW5/SW6'ya basar, Ø1.75 filament pim menteşe (z 3.6) |
| Tekerlek | `wheel` | Ø22 × 7, 24 kanal, EC10E için Ø3.4 D-düz uç, Ø2 pim için pres delik |

Ölçüler: dış zarf 62.9 × 117.0 mm. Yükseklik yüzeyden 36.8 mm (kaydırıcılar dahil). Kabuk duvarı 1.8 mm.

## Malzeme ve baskı ayarları (öneri)

- PETG (tuşlar için tercih edilir; esnek dil yorulmaya dayanır) ya da PLA. Nozul 0.4, katman 0.16–0.2, 3 çevre (perimeter), %20 gyroid dolgu.
- **Alt kabuk:** taban yatakta, destek gerekmez.
- **Üst kabuk:** ayırma kenarı yatakta. İç tavan için ağaç (tree) destek gerekir (çıkıntı tablosu `CHECKS.md` §6'da).
- **Sol / sağ tuş:** montaj yönünde basılır. Dil yatay katmanlarla basılmalı, yani dile dik basılmaz. Deri ve dil altına ağaç destek konur.
- **Yan tuşlar:** montaj yönünde, destek az.
- **Tekerlek:** ekseni dik, düz sağ yüzü yatakta, destek gerekmez. Ø1.95 pres deliği ve Ø3.4 uç ölçüsel deliklerdir; ilk baskıda pim ve enkoder geçişini deneyin.

## Satın alınacaklar (BOM)

| Adet | Parça |
|---|---|
| 4 | M2 × 8 silindir başlı vida (alt kabuk → PCB → üst kabuk) |
| 2 | M2 × 5 vida (tuş dilleri, plastiğe diş açan) |
| 1 | Ø2 × 14 çelik pim (ISO 2338 2 m6×14) – tekerlek aksı / orta tık |
| 2 | Ø1.75 × 9 filament parçası – yan tuş menteşe pimi |
| 4 | PTFE fare kaydırıcısı, 0.8 mm (ör. 12 × 6). Kalınlık sensör yüksekliğini belirler, farklı kalınlık kullanmayın |
| 1 | PixArt LM19-LSI lens (PMW3360 için) |
| 1 | 4 pin Dupont kablo (USB başlığına) |
| 6 | Omron D2F (öneri: D2F-01F, 0.74 N, ana tuşlarda daha hafif tık) |

## Montaj sırası

1. Lens'i sensöre takın. Kartı alt kabuktaki 4 standoff'a oturtun. Tekerlek çatalı PCB çentiğinden geçer.
2. Ø2 pimi tekerleğin sağ yüzündeki deliğe preslenip sonuna kadar itin.
3. Tekerleğin D-uçlu sol mili EC10E deliğine girer. Pimi çatalın üst tırnağından içeri bastırın; pim SW3 plungerının üstüne oturur.
4. Dupont kabloyu USB başlığına takın. Kabloyu üst kabuğun arka deliğinden geçirip içeride düğüm atın (gerginlik önleyici).
5. Sol ve sağ tuşları dilleriyle üst kabuk göbeklerine M2×5 ile vidalayın.
6. Yan tuşları kulaklar arasına yerleştirin. Ø1.75 filament pimi iterek takın; uçları kabuk kulaklarında kalır.
7. Üst kabuğu kapatın. 4 × M2×8 vidayı alttan (havşa) sıkın; PCB iki kabuk arasında sıkışır.
8. Kaydırıcıları tabana yapıştırın. Lens açıklığını kapatmayın.

## Ölçülen temel değerler (ayrıntı `CHECKS.md`)

- Bütün nub ile plunger arası boşluk **0.20 mm** (SW1, SW2, SW4, SW5, SW6). Tıka kadar yol ≤ 0.7 mm.
- Orta tık: pim SW3 plungerına oturur (0.00). Tam basışta eğim 2.03°. Enkoder, kabuklar ve PCB ile girişim yok.
- Lens referans düzlemi yüzeye **2.40 mm**, PCB üstü yüzeye **7.40 mm** (PMW3360 veri sayfası Şekil 4).
- Montajda tek katı örtüşme var: tekerlek ile Ø2 pim arasındaki kasıtlı pres geçme (0.667 mm³). Diğer bütün çiftler boşlukta ya da istenen temasta.
- Bütün STL'ler su geçirmez. Alt kabuk ve tekerlek desteksiz basılır.

## NX kurgusu (yeniden üretim)

- `mouse_ctrl.prt` kontrol parçasıdır ve şunları içerir:
  - ana ifadeler: sensör yığını, plunger konumları, tuş ve menteşe ölçüleri, 7 kesitin genişlik ve yükseklikleri;
  - `PARTING` ve `BASE` datum'ları;
  - dış deri: ifadeyle sürülen 16 akıllı noktadan geçen periyodik studio spline kesitleri → Through Curves → Trim → Blend;
  - `ENVELOPE` (dolu) ve `HOUSING` (kapalı Shell 1.8);
  - tuş ve yarık araç gövdeleri (DOF 0 çizimler).
- Parçalar `mouse_design.prt` içinde iş parçası (work part) yapılarak kuruldu:
  - `HOUSING`, `ENVELOPE`, araç gövdeleri ve PCB kartı WAVE ile bağlandı;
  - ölçüler ara-parça ifadeleriyle (`"mouse_ctrl"::…`) alındı;
  - PCB delik konumları bağlı kenarların merkez noktalarından alındı.
- `mouse_asm.prt` üretim montajıdır. Clearance Analysis, STEP ve STL burada üretilir.
- Yeniden üretim sırası: `j1_ctrl → j2_bottom, j5_wheel → j3_top, j4_keys → j6_asm → j7_regen` (her biri `run_journal`).
  STL yönlendirme, ölçüm ve render betikleri: `post.py`, `render_all.py`, `stepcheck.py`, `make_checks.py`.
  `j1` kontrol parçasını ve boş bileşenleri yeniden oluşturur.
  Betiklerdeki mutlak Windows yolları (`C:\Users\USER\...`, `C:\NX_MCP_WORKSPACE\...`) bizim makinemize ait; kendi makinenizde değiştirin.

## Açık noktalar / varsayımlar

- **EC10E mil deliği:** STEP'te Ø3.6 yuvarlak yer tutucu var. Gerçek enkoderin delik profiline göre D-düz uç (`stub_d`, `stub_flat`) ayarlanmalı.
- **D2F ve EC10E gövdeleri** STEP'te yaklaşık. Nub boşluğu (`nub_gap` 0.2) ilk baskıdan sonra 0.1–0.3 arasında ayarlanabilir.
- **Lens açıklığı** (9 × 14) veri sayfasındaki önerilen taban açıklığı çiziminden ölçülmedi. Lens çevresi için kesin değil, LM19-LSI çizimiyle teyit edilmeli.
- **Lens zarfı** (`lm19_lens_envelope`) yalnız yer kontrolü için basit bir bloktur.
- **Dış deri kesitleri:** spline noktaları ifadelerle sürülür. Süper-elips üsleri (`n_up` 2.3, `n_low` 5) ise formüllere sayı olarak gömülüdür.
- **PCB sıkma göbekleri:** göbekler PCB deliklerinin WAVE merkez noktalarına bağlı. Göbekleri yan duvara bağlayan 2 mm kanatların konumu ise sayısal girildi; PCB delikleri taşınırsa kanatlar elle güncellenmeli.
- **Kabuk hizalama:** iki kabuk arasında dil/oluk yok. Hizalama 4 vida ve PCB ile sağlanıyor. İstenirse ayırma kenarına 0.1 boşluklu bir dudak eklenebilir.
- **Yan tuşlar:** başparmak içe ve hafif aşağı basar (menteşe altta). Gerçek kullanımda kuvvet ve hissin denenmesi gerekir.
- **Kablo:** Dupont soket gövdesi ile arka sol sıkma göbeği arasında yalnız ~0.3 mm var (başlık pimlerine 0.35 ölçüldü). Daha geniş bir soket kullanılacaksa göbek kanadı kısaltılmalı.
