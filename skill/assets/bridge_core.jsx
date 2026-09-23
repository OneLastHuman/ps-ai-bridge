// jsx/bridge_core.jsx - 被 ps_bridge.py 注入执行的通用 helpers
// 保持 ASCII 无中文，兼容 CS6

// 获取完整文档信息 JSON
function bridgeGetDocumentInfo(){
    if(app.documents.length==0) return JSON.stringify({error:"No document", docCount:0});
    var d=app.activeDocument;
    var r={};
    r.name=d.name;
    r.width=d.width.as("px"); r.height=d.height.as("px");
    r.resolution=d.resolution;
    r.mode=d.mode.toString();
    r.colorProfileName=d.colorProfileName;
    r.bitsPerChannel=d.bitsPerChannel.toString();
    r.layerCount=d.layers.length;
    r.activeLayer=d.activeLayer.name;
    r.path=d.fullName ? d.fullName.fsName : "";
    return JSON.stringify(r);
}

// 列出所有图层（扁平）
function bridgeListLayers(){
    if(app.documents.length==0) return "[]";
    var doc=app.activeDocument; var arr=[];
    function walk(layers, depth){
        for(var i=0;i<layers.length;i++){
            var l=layers[i];
            var o={name:l.name, visible:l.visible, opacity:l.opacity, depth:depth, typename:l.typename};
            try{ o.kind=l.kind.toString(); }catch(e){ o.kind="group"; }
            try{ o.bounds=[l.bounds[0].as("px"), l.bounds[1].as("px"), l.bounds[2].as("px"), l.bounds[3].as("px")]; }catch(e){}
            arr.push(o);
            if(l.typename=="LayerSet") walk(l.layers, depth+1);
        }
    }
    walk(doc.layers, 0);
    return JSON.stringify(arr);
}

// 保存当前文档缩略图到临时 JPEG（COM 回落用）
function bridgeSaveTempJpeg(width, height, outPath){
    if(app.documents.length==0) throw "No document";
    var tmp=new File(outPath);
    var dup=app.activeDocument.duplicate();
    dup.resizeImage(UnitValue(width,"px"), UnitValue(height,"px"), null, ResampleMethod.BICUBIC);
    var opts=new JPEGSaveOptions(); opts.quality=8;
    dup.saveAs(tmp, opts, true, Extension.LOWERCASE);
    dup.close(SaveOptions.DONOTSAVECHANGES);
    return tmp.fsName;
}

// 安全填充矩形
function bridgeFillRect(x,y,w,h,r,g,b,opacity){
    var doc=app.activeDocument;
    var c=new SolidColor(); c.rgb.red=r; c.rgb.green=g; c.rgb.blue=b;
    doc.selection.select([[x,y],[x+w,y],[x+w,y+h],[x,y+h]]);
    doc.selection.fill(c, ColorBlendMode.NORMAL, opacity||100, false);
    doc.selection.deselect();
}

// 多边形填充
function bridgeFillPolygon(points, r,g,b){
    var doc=app.activeDocument;
    var c=new SolidColor(); c.rgb.red=r; c.rgb.green=g; c.rgb.blue=b;
    doc.selection.select(points);
    doc.selection.fill(c); doc.selection.deselect();
}
