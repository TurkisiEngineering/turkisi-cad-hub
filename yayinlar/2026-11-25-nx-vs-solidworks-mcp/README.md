# 25 Kasım 2026 · Ajanlar Yarışıyor: SolidWorks MCP vs NX MCP

📺 Yayın: https://youtu.be/p9tGvunJSg8 · 💬 Duyuru ve sorular: [#2](https://github.com/TurkisiEngineering/turkisi-cad-hub/discussions/2)

Ajanlar aynı PCB STEP dosyasından **3B yazıcıyla basılabilir DIY oyuncu faresi kabuğu** tasarlıyor:
üst kabuk, alt kabuk, tuşlar, tekerlek. Yöntem ve prompt serbest, girdi herkes için aynı.

## Girdi

[`girdi/mouse_pcb.step`](girdi/mouse_pcb.step) · SHA-256 `da66ded68762658dcbcef532b2fd1c550f8a20c2086669cb0d8221ffd974f439`
Görev metni ve kriterler: [`girdi/GOREV.md`](girdi/GOREV.md)

Kart 49.8 × 61.7 × 1.6 mm: 6 × Omron D2F mikro anahtar, PMW3360 optik sensör, EC10E tekerlek encoder'ı, RP2040,
4 × M2 delik, 4 pin USB başlığı. D2F tuşlar, sensör gövdesi ve encoder yaklaşık (yer kaplama) gövdeler; ölçüleri
footprint'ten, yükseklikleri tahmin. Gerçek parçayla basacaksanız bu üç ölçüyü kumpasla doğrulayın.

## Sonuçlar

| Klasör | Ne | Araç zinciri | Durum |
|---|---|---|---|
| [`neon-mouse/`](neon-mouse/) | Yayın öncesi örnek fare | Antigravity · Neon modeli + bizim NX harness'ımız (NX 2206, NXOpen journal) | ✅ hazır |
| `nx-mcp/` | Yayındaki NX ajanı | NX MCP | ⏳ yayında |
| `solidcraft-contabo/` | Açık kaynak CAD ajanı | SolidCraft, Contabo Linux VPS | ⏳ yayında |
| `solidworks-mcp/` | Konuğumuz Ahmet Talha Olmuştur | SolidWorks MCP | ⏳ yayında |

Kıyas kriterleri: basılabilirlik · tuş/tekerlek uyumu · sensör açıklığı · montaj/vida · ergonomi · süre.

## Neon Mouse içeriği

~116 × 63.6 × 39.4 mm, 7 parça: alt şasi, üst kabuk, tekerlek, DPI tuşu, iki başparmak tuşu, PTFE ayaklar.

| Klasör | İçerik |
|---|---|
| [`plan.md`](neon-mouse/plan.md) | Mühendislik planı ve doğrulama raporu (PCB arayüz haritası, parça listesi) |
| [`step/`](neon-mouse/step/) | Parça STEP'leri, `mouse_assembly_full.step` (PCB dahil montaj), `mouse_mechanical_only.step` |
| [`stl/`](neon-mouse/stl/) | Baskı için parça başına STL |
| [`prt/`](neon-mouse/prt/) | NX 2206 parça ve montaj dosyaları (`mouse_asm.prt`) |
| [`views/`](neon-mouse/views/), [`views_hq/`](neon-mouse/views_hq/) | Renderlar: iso, üst, yan, alt, PCB röntgen, patlatılmış, neon |
| [`scripts/`](neon-mouse/scripts/) | Modeli üreten NXOpen journal (`build_mouse.py`), girişim kontrolü, render ve STL betikleri |
| `result.json`, `step_gate.json`, `pcb_asm_result.json` | NX gövde kontrolü, STEP doğrulaması, PCB montaj sonucu |

![Neon Mouse](neon-mouse/views_hq/07_hero_neon_v3.png)

Betiklerdeki mutlak Windows yolları bizim makinemize ait; kendi makinenizde çalıştırırken değiştirin.
