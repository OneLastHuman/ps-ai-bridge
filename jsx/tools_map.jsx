// jsx/tools_map.jsx - PS 全部工具 stringID 映射（CS6/CC 通用）
// 用于 bridge.select_tool(toolID) 与 toolChanged 事件订阅

var PS_TOOLS = {
  // 移动/选区
  moveTool: "移动工具",
  rectangleMarqueeTool: "矩形选框",
  ellipticalMarqueeTool: "椭圆选框",
  lassoTool: "套索",
  polygonalLassoTool: "多边形套索",
  magneticLassoTool: "磁性套索",
  quickSelectTool: "快速选择",
  magicWandTool: "魔棒",
  cropTool: "裁剪",
  sliceTool: "切片",
  // 画笔/修复
  brushTool: "画笔",
  pencilTool: "铅笔",
  mixerBrushTool: "混合器画笔",
  cloneStampTool: "仿制图章",
  historyBrushTool: "历史记录画笔",
  artHistoryBrushTool: "艺术历史画笔",
  eraserTool: "橡皮擦",
  backgroundEraserTool: "背景橡皮擦",
  magicEraserTool: "魔术橡皮擦",
  blurTool: "模糊",
  sharpenTool: "锐化",
  smudgeTool: "涂抹",
  dodgeTool: "减淡",
  burnTool: "加深",
  spongeTool: "海绵",
  spotHealingBrushTool: "污点修复",
  healingBrushTool: "修复画笔",
  patchTool: "修补",
  redEyeTool: "红眼",
  // 矢量/文字/形状
  penTool: "钢笔",
  freeformPenTool: "自由钢笔",
  pathSelectionTool: "路径选择",
  directSelectionTool: "直接选择",
  textTool: "文字",
  shapeTool: "形状",
  customShapeTool: "自定形状",
  // 其它
  gradientTool: "渐变",
  bucketTool: "油漆桶",
  eyedropperTool: "吸管",
  colorSamplerTool: "颜色取样器",
  measureTool: "标尺",
  countTool: "计数",
  handTool: "抓手",
  zoomTool: "缩放",
  notesTool: "注释",
  audioAnnotationTool: "声音注释"
};

// 返回所有 toolID 数组
function bridgeListTools(){ var arr=[]; for(var k in PS_TOOLS) arr.push(k); return JSON.stringify(arr); }

// 选择工具（ActionManager）
function bridgeSelectTool(toolID){
    var idselect = stringIDToTypeID("select");
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putClass(stringIDToTypeID(toolID));
    desc.putReference(stringIDToTypeID("null"), ref);
    executeAction(idselect, desc, DialogModes.NO);
    return toolID+" selected";
}
