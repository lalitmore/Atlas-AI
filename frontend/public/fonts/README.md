# Locally served PDF fonts

These assets are used only after clicking Download PDF. No font CDN is contacted at runtime.

- `NotoSans-Regular.ttf` and `NotoSans-Bold.ttf`: Latin, Greek, and Cyrillic, including accented names. Unmodified hinted TrueType files from [notofonts/noto-fonts](https://github.com/notofonts/noto-fonts/tree/main/hinted/ttf/NotoSans), under `OFL-NotoSans.txt`.
- `NotoSansJP-Regular.ttf`: Japanese and common Han characters, loaded only when the exported content contains Han, Hiragana, or Katakana. Derived at weight 400 from Google's [Noto Sans JP variable TrueType font](https://github.com/google/fonts/tree/main/ofl/notosansjp), under `OFL-NotoSansJP.txt`.
- `NotoSansKR-Regular.ttf`: Korean, loaded only when the exported content contains Hangul. Derived at weight 400 from Google's [Noto Sans KR variable TrueType font](https://github.com/google/fonts/tree/main/ofl/notosanskr), under `OFL-NotoSansKR.txt`.

The Japanese and Korean fonts are static TrueType instances, produced using FontTools 4.67.0:

```python
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

font = TTFont("NotoSansJP[wght].ttf")
instantiateVariableFont(font, {"wght": 400}, inplace=True).save("NotoSansJP-Regular.ttf")
```

Repeat with `KR` for Korean. FontTools is a one-time asset preparation utility, not an application dependency. All fonts are licensed under the SIL Open Font License 1.1; the full license and copyright notices are included alongside them. The renderer embeds only the glyphs the exported PDF uses.
