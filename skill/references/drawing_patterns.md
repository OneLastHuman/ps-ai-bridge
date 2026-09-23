# Drawing Patterns - Prompt to Primitives

Map any natural language prompt to `assets/drawing_primitives.jsx` primitives: `fillRect/fillEllipse/fillPolygon/gradientBand`.

**Primitives**
- `rgb(r,g,b)` `lerpColor` `getGradColor`
- `fillRect(doc,x,y,w,h,color,opacity)`
- `fillEllipse(doc,cx,cy,rx,ry,color)` polygon 32
- `fillPolygon(doc,points,color)`
- `gradientBand(doc,x,y,w,h,stops,vertical)` band=4
- `cloudCluster(doc,cx,cy,scale,color)`

**Patterns**
- **Sky**: `gradientBand` vertical with stops `[10,10,40]->[80,40,120]`
- **Sun/glow**: concentric `fillEllipse` with `SCREEN` and opacity 60/40
- **Clouds**: `cloudCluster` 5 ellipses random
- **Water**: `gradientBand` horizontal + `SCREEN` rects for reflection
- **City/buildings**: `fillRect` loop + window lights `fillRect 8x12`
- **Trees/hills**: `fillPolygon` silhouettes
- **Text**: `textTool` via `select_tool` then `execute_jsx` with `TextItem`

Example: `assets/example_scene.jsx` cyber-city uses all.

Always decompose prompt: subject -> shapes -> colors -> layers.
