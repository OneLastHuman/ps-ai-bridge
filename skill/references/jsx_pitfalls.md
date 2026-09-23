# JSX Pitfalls (CS6)

- **No Chinese** in .jsx source: `DoJavaScript` mangles UTF-8 -> `line 374 unterminated string`. Use ASCII, JSON polyfill escapes `\uXXXX`.
- **No charID Elps** `charIDToTypeID("Elps")` fails 8800 in CS6. Use `fillEllipse` polygon 32 segs in `assets/drawing_primitives.jsx:29`.
- **No stringID ellipse** `stringIDToTypeID("ellipse")` unknown.
- Always `app.displayDialogs=DialogModes.NO; app.preferences.rulerUnits=Units.PIXELS` first.
- `doc.selection.deselect()` in try/catch.
- `saveAs` needs existing dir: Python `Path.mkdir` before.
- `place` not DOM in CS6: use `open+copy+paste` fallback (`ps_bridge.py:701`).
- Background locked: `isBackgroundLayer=false` before `resize/rotate`.
- File encoding: set `File.encoding="UTF-8"` before `open("w")`.
