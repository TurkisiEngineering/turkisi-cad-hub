# assets/

Hub görselleri. Palet ve KUMPAS çizimi profil reposundaki (`mikbalarikan/mikbalarikan` → `assets/build_assets.py`) "Lacivert Çelik" tokenlarıyla aynı.

| Dosya | Boyut | Nerede |
|---|---|---|
| `banner-dark.svg` · `banner-light.svg` | 1280×320 | Hub README üstü (`<picture>`, tema ile değişir) |
| `org-banner-dark.svg` · `org-banner-light.svg` | 1280×280 | `TurkisiEngineering/.github` → `profile/README.md` |
| `hub-card-dark.svg` · `hub-card-light.svg` | 1200×220 | Kişisel profil README'leri (bkz. kit `snippets/profile-readme-block.md`) |
| `social-preview.png` | 1280×640 | Hub → Settings → General → Social preview (UI'dan yüklenir) |
| `org-avatar.png` | 500×500 | Org → Settings → Profile picture (UI'dan yüklenir) |
| `kumpas-welcome.png` | 600×300 | "Buradan başlayın" açılış başlığı |
| `src/*.svg` | | PNG'lerin vektör kaynakları |
| `src/parts/*.webp` · `parts.json` | | Lig parçalarının render'ları (aşağıda) |

**Parça render'ları:** [Agentic CAD Ligi](https://github.com/TurkisiEngineering/turkisi-cad)'nde ajanların kör çizdiği parçalar (koşu çıktıları, MIT). Kahraman görsel P16 konik dişli: yarısı STL üçgen ağı, yarısı temiz CAD; Ø 32.56 STEP'ten ölçülen dış çap. Diğerleri P10 tırtıllı topuz, P19 döner tekerlek ve P05 rotil başı. Kaynak STEP linkleri ve skorlar `src/parts/parts.json` içinde.

Yeniden üretmek için:

```bash
python assets/build_assets.py          # SVG'ler
python assets/build_assets.py --png    # + PNG'ler (Playwright + Edge ya da Chromium)
```

SVG'ler GitHub'da `<img>` olarak gösterilir: script, harici font ve harici görsel yok, metinler sistem fontlarıyla çizilir ve `textLength` ile genişlikleri sabitlenir.
