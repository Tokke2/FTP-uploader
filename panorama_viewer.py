# Copyright (c) 2026 Rickard Längkvist
"""Self-contained WebGL equirectangular viewer; opt-in 2:1 detection."""
import html
from pathlib import Path
from gallery_delivery import script_json

VIEWER = r'''<!doctype html><html lang="sv"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>360° panorama</title><style>body{margin:0;background:#101827;color:white;font:16px system-ui}header{padding:12px;display:flex;gap:12px;flex-wrap:wrap}a{color:#67e8f9}button,select{font:inherit;padding:8px}canvas{display:block;width:100%;height:75vh;touch-action:none}#status{padding:12px}</style>
<header><a href="index.html">Till galleriet</a><label>Panorama <select id="images"></select></label><button id="reset">Återställ vy</button><label>Synfält <input id="fov" type="range" min="35" max="110" value="75"></label></header>
<p id="status" role="status">Dra för att titta runt. Piltangenter styr vyn när bilden har fokus.</p><canvas id="view" tabindex="0" aria-label="Interaktiv panoramavy"></canvas>
<script>
const items=__ITEMS__,c=document.getElementById('view'),status=document.getElementById('status'),list=document.getElementById('images'),fov=document.getElementById('fov');
items.forEach((p,i)=>{let o=document.createElement('option');o.value=i;o.textContent=p.name;list.appendChild(o);});
const gl=c.getContext('webgl');let yaw=0,pitch=0,drag=null,loaded=false;
function fail(message){status.textContent=message;let a=document.createElement('a');a.href=items[Number(list.value)||0].src;a.textContent=' Öppna panoramabilden';status.appendChild(a);}
if(!gl){fail('WebGL saknas.');}else{try{
function shader(type,source){let s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error('shader');return s;}
let program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,'attribute vec2 p;varying vec2 uv;void main(){uv=p;gl_Position=vec4(p,0.,1.);}'));
gl.attachShader(program,shader(gl.FRAGMENT_SHADER,`precision mediump float;varying vec2 uv;uniform sampler2D image;uniform float yaw,pitch,fov,aspect;
void main(){vec3 d=normalize(vec3(uv.x*aspect*tan(fov/2.),uv.y*tan(fov/2.),-1.));float cp=cos(pitch),sp=sin(pitch);d=vec3(d.x,d.y*cp-d.z*sp,d.y*sp+d.z*cp);float cy=cos(yaw),sy=sin(yaw);d=vec3(d.x*cy+d.z*sy,d.y,-d.x*sy+d.z*cy);vec2 t=vec2(fract(atan(d.z,d.x)/6.2831853+.5),.5-asin(clamp(d.y,-1.,1.))/3.14159265);gl_FragColor=texture2D(image,t);}`));
gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('program');gl.useProgram(program);
let buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);let attr=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(attr);gl.vertexAttribPointer(attr,2,gl.FLOAT,false,0,0);
let texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
function draw(){if(!loaded)return;let r=c.getBoundingClientRect(),scale=Math.min(devicePixelRatio||1,2);c.width=Math.max(1,Math.round(r.width*scale));c.height=Math.max(1,Math.round(r.height*scale));gl.viewport(0,0,c.width,c.height);for(let [key,value] of Object.entries({yaw,pitch,fov:Number(fov.value)*Math.PI/180,aspect:c.width/c.height}))gl.uniform1f(gl.getUniformLocation(program,key),value);gl.drawArrays(gl.TRIANGLES,0,6);}
let serial=0;function load(){let version=++serial;loaded=false;let image=new Image();image.onload=function(){if(version!==serial)return;try{let max=gl.getParameter(gl.MAX_TEXTURE_SIZE),src=image;if(image.width>max||image.height>max){let tmp=document.createElement('canvas'),factor=Math.min(max/image.width,max/image.height);tmp.width=Math.floor(image.width*factor);tmp.height=Math.floor(image.height*factor);tmp.getContext('2d').drawImage(image,0,0,tmp.width,tmp.height);src=tmp;}gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,src);loaded=true;yaw=pitch=0;status.textContent='Dra för att se dig omkring. Piltangenter fungerar när bilden har fokus.';draw();}catch(e){fail('Webbläsaren kunde inte läsa bildtexturen. Prova via en webbserver.');}};image.onerror=()=>{if(version===serial)fail('Bilden kunde inte laddas.');};image.src=items[Number(list.value)||0].src;}
list.onchange=load;fov.oninput=draw;document.getElementById('reset').onclick=()=>{yaw=pitch=0;fov.value=75;draw();};
c.onpointerdown=e=>{drag=[e.clientX,e.clientY];c.setPointerCapture(e.pointerId);c.focus();};c.onpointermove=e=>{if(!drag)return;yaw-=(e.clientX-drag[0])*.006;pitch=Math.max(-1.5,Math.min(1.5,pitch+(e.clientY-drag[1])*.006));drag=[e.clientX,e.clientY];draw();};c.onpointerup=c.onpointercancel=()=>{drag=null;};
c.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')yaw-=.1;if(e.key==='ArrowRight')yaw+=.1;if(e.key==='ArrowUp')pitch=Math.min(1.5,pitch+.1);if(e.key==='ArrowDown')pitch=Math.max(-1.5,pitch-.1);draw();};window.addEventListener('resize',draw);load();
}catch(e){fail('Panoramavisaren kunde inte starta.');}}
</script></html>'''


def export_panoramas(entries, output):
    from PIL import Image
    output = Path(output)
    items = []
    for entry in entries:
        path = Path(entry.get('full_dst', ''))
        if not path.is_file(): continue
        with Image.open(path) as image:
            ratio = image.width / max(1, image.height)
        if 1.95 <= ratio <= 2.05:
            relative = path.relative_to(output).as_posix()
            items.append({'src': relative, 'name': entry.get('title') or path.name})
    if not items: return ''
    (output / 'panorama.html').write_text(VIEWER.replace('__ITEMS__', script_json(items)), encoding='utf-8')
    return '<p style="text-align:center"><a href="panorama.html">Öppna 360°-panoraman (%d)</a></p>' % len(items)
