// jsx/example_scene.jsx - 任意图生成范例（AI 可替换此模板）
// 演示：用 drawing_primitives.jsx 原语画“赛博城市夜景”，全 ASCII 安全

#include "drawing_primitives.jsx"

var doc = app.documents.add(UnitValue(1920,"px"), UnitValue(1080,"px"), 72, "CyberCity", NewDocumentMode.RGB, DocumentFill.BLACK);

// 天空渐变
gradientBand(doc, 0,0,1920,600, [{pos:0,color:[10,10,40]},{pos:0.5,color:[30,20,80]},{pos:1,color:[80,40,120]}], true);
// 城市剪影
fillPolygon(doc, [[0,600],[0,800],[1920,750],[1920,600]], [15,15,25]);
// 楼群
for(var i=0;i<12;i++){
  var x=i*160+20; var h=200+Math.random()*300;
  fillRect(doc, x, 600-h, 100, h, [40+Math.random()*30,40+Math.random()*30,60+Math.random()*40], 100);
  // 窗光
  for(var wy=0; wy<h; wy+=30) for(var wx=0; wx<100; wx+=20) if(Math.random()>0.3) fillRect(doc, x+wx, 600-h+wy, 8,12, [255,220,120], 80);
}
// 光晕
fillEllipse(doc, 1600,200, 120,120, [255,100,180], 40);
fillEllipse(doc, 1600,200, 80,80, [255,180,220], 60);

// 保存
var outDir=new Folder(Folder.temp.fsName+"/ps-ai-bridge");
if(!outDir.exists) outDir.create();
var out=new File(outDir.fsName+"/cyber_city.jpg");
doc.saveAs(out, new JPEGSaveOptions(), true, Extension.LOWERCASE);
"cyber city done";
