// jsx/drawing_primitives.jsx - 安全绘图原语，修复 Elps/中文坑
// 来源 photoshop-jsx skill 的 ps_jsx_helpers.jsx:29 精简版，全部 ASCII

app.displayDialogs=DialogModes.NO;
if(app.preferences) app.preferences.rulerUnits=Units.PIXELS;

function rgb(r,g,b){ var c=new SolidColor(); c.rgb.red=r; c.rgb.green=g; c.rgb.blue=b; return c; }
function lerpColor(c1,c2,t){ return [Math.round(c1[0]+(c2[0]-c1[0])*t), Math.round(c1[1]+(c2[1]-c1[1])*t), Math.round(c1[2]+(c2[2]-c1[2])*t)]; }
function getGradColor(stops, t){
    for(var i=0;i<stops.length-1;i++){ if(t>=stops[i].pos && t<=stops[i+1].pos){ var local=(t-stops[i].pos)/(stops[i+1].pos-stops[i].pos); return lerpColor(stops[i].color, stops[i+1].color, local);} }
    return stops[0].color;
}
function fillRect(doc, x,y,w,h, color, opacity){
    var c=rgb(color[0],color[1],color[2]);
    doc.selection.select([[x,y],[x+w,y],[x+w,y+h],[x,y+h]]);
    doc.selection.fill(c, ColorBlendMode.NORMAL, opacity||100, false);
    try{doc.selection.deselect();}catch(e){}
}
function fillEllipse(doc, cx, cy, rx, ry, color, opacity){
    // polygon 逼近，32 段，避免 charID Elps 在 CS6 报 8800
    var c=rgb(color[0],color[1],color[2]);
    var pts=[]; var segs=32;
    for(var i=0;i<segs;i++){ var a=i*2*Math.PI/segs; pts.push([cx+rx*Math.cos(a), cy+ry*Math.sin(a)]); }
    doc.selection.select(pts);
    doc.selection.fill(c, ColorBlendMode.NORMAL, opacity||100, false);
    try{doc.selection.deselect();}catch(e){}
}
function fillPolygon(doc, points, color){
    var c=rgb(color[0],color[1],color[2]);
    doc.selection.select(points);
    doc.selection.fill(c); try{doc.selection.deselect();}catch(e){}
}
function gradientBand(doc, x,y,w,h, stops, vertical){
    var band=4;
    var steps = vertical ? h/band : w/band;
    for(var i=0;i<steps;i++){
        var t=i/steps; var col=getGradColor(stops, t);
        if(vertical) fillRect(doc, x, y+i*band, w, band, col, 100);
        else fillRect(doc, x+i*band, y, band, h, col, 100);
    }
}
function cloudCluster(doc, cx, cy, scale, color){
    for(var i=0;i<5;i++){ var ang=Math.random()*Math.PI*2; var r=Math.random()*scale; fillEllipse(doc, cx+Math.cos(ang)*r, cy+Math.sin(ang)*r, scale*0.6, scale*0.4, color, 60); }
}
