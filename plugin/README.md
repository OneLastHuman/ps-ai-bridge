# plugin/ - C++ Filter 插件骨架（可选扩展）

MVP 主通道已通过 `connectionsdk` 满足 看/画/改/全工具。若需**像素级直写**（如 AI inpaint 滤镜、实时神经滤波），可在此新建 `Filter` 插件，复用 `pluginsdk/photoshopapi/photoshop/PIFilter.h:421` 的 `FilterRecord`。

## 最小骨架
```
plugin/AiFilter/
  AiFilter.cpp        # filterSelectorStart/Continue/Finish
  AiFilter.r          # PiPL 资源 ('fici' FilterCaseInfo)
  AiFilter.vcxproj    # 引用 Photoshop SDK pluginsdk/photoshopapi（自行从 Adobe 下载）
```

`PIFilter.h` 关键：
- `FilterRecord.inData/outData/maskData + inRowBytes/outRowBytes` Tile 循环
- `BigDocumentStruct` 支持 >30k 大图
- `depth` 1/8/16/32 位
- `sSPBasic->AcquireSuite(kPSBufferSuite)` 分配缓冲

示例 `filterSelectorContinue`：
```cpp
for(y=filterRect.top; y<filterRect.bottom; y++){
  // inData/outData 为 interleaved 平面数据
  memcpy(outRow, inRow, width * planes);
  // 在此插入 AI 推理（如 ONNX）
}
```

编译后产出 `AiFilter.8bf` 放 `Adobe Photoshop CS6/Plug-ins/Filters/`，重启后在 `滤镜 > AiFilter` 出现。Python 端通过 `execute_action` 或 `execute_jsx` 调用：
```js
executeAction(stringIDToTypeID("AiFilter"), desc, DialogModes.NO)
```

MVP 阶段无需编译，保持空目录即可；需要时参考 `pluginsdk/samplecode/filter/dissolve`。
