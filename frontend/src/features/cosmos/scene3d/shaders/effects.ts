import { NOISE } from './noise'

export const LEAK_FRAGMENT = `
${NOISE}
uniform float uTime; uniform float uSeed; uniform float uInner; uniform float uStrength; uniform vec3 uDeep; uniform vec3 uGlow;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float a = atan(q.y, q.x + 1e-5);
  float t = clamp((d - uInner)/(1.0 - uInner), 0.0, 1.0);
  vec3 nc = vec3(cos(a)*1.7, sin(a)*1.7, d*2.2 - uTime*0.11 + uSeed);
  float n = fbm(nc, 4);
  float n2 = fbm(nc*2.3 + 7.0, 3);
  float inner = smoothstep(uInner*0.9, uInner*1.03, d);
  float halo = inner * exp(-t*4.2);
  float rim = inner * exp(-t*14.0);
  float f = n + n2*0.35;
  float tend = smoothstep(0.12, 0.5, f) * (1.0 - smoothstep(0.5, 0.75, f)) * inner * (1.0 - smoothstep(0.1, 0.95, t));
  vec3 col = uDeep*halo*0.32 + uGlow*(tend*0.42*(1.0 - t) + rim*0.5);
  float alpha = clamp(halo*0.6 + tend*0.25, 0.0, 0.85);
  col *= 1.0 - smoothstep(0.85, 1.0, d); alpha *= 1.0 - smoothstep(0.85, 1.0, d);
  gl_FragColor = vec4(col*uStrength, alpha*uStrength);
}`

export const SPARK_VERTEX = `
attribute vec3 aDir; attribute float aSeed;
uniform float uTime; uniform float uStrength; uniform float uRatio;
varying float vAlpha;
void main(){
  float life = fract(uTime*(0.05 + aSeed*0.06) + aSeed*7.13);
  vec3 d = normalize(aDir + vec3(sin(uTime*0.3 + aSeed*20.0), cos(uTime*0.25 + aSeed*13.0), 0.0)*0.25*life);
  float sc = length(modelMatrix[0].xyz);
  vec3 pos = d * (1.0 + life*(0.6 + uStrength*1.9));
  vec4 mv = modelViewMatrix*vec4(pos, 1.0);
  gl_Position = projectionMatrix*mv;
  vAlpha = sin(life*3.14159) * (0.5 + 0.5*aSeed);
  gl_PointSize = clamp((2.0 + aSeed*3.0)*uRatio * (sc*40.0 / -mv.z), 1.0, 7.0*uRatio);
}`

export const SPARK_FRAGMENT = `
uniform float uStrength; uniform vec3 uGlow;
varying float vAlpha;
void main(){
  vec2 q = gl_PointCoord*2.0-1.0; float d = dot(q,q); if (d > 1.0) discard;
  gl_FragColor = vec4(uGlow*exp(-d*3.0)*vAlpha*1.6*uStrength, 1.0);
}`

export const FOG_FRAGMENT = `
${NOISE}
uniform float uTime; uniform float uSeed; uniform float uAlpha; uniform vec3 uColor;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float n = fbm(vec3(q*2.2 + vec2(uTime*0.01, 0.0), uSeed + uTime*0.015), 5);
  float m = (1.0 - smoothstep(0.25, 1.0, d)) * smoothstep(-0.35, 0.45, n);
  gl_FragColor = vec4(uColor*m*0.5, m*uAlpha);
}`

export const INDICATOR_FRAGMENT = `
float gaussian(float x){ return exp(-x*x); }
uniform vec3 uColor; uniform float uTime; uniform float uAlpha; uniform int uMode;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float a = atan(q.y, q.x + 1e-5);
  float c = 0.0;
  if (uMode == 0) {
    c = gaussian((d - 0.80)*95.0)*0.9;
    float seg = fract((a + uTime*0.12)/6.28318*72.0);
    c += step(seg, 0.32)*gaussian((d - 0.865)*150.0)*0.45;
    float br = fract((a - uTime*0.2)/1.570796);
    c += (step(br, 0.09) + step(0.91, br))*gaussian((d - 0.93)*120.0)*0.9;
  } else if (uMode == 1) {
    c = gaussian((d - 0.82)*60.0)*0.9;
  } else {
    float dash = step(0.5, fract((a + uTime*0.06)/6.28318*40.0));
    c = gaussian((d - 0.88)*80.0)*dash*0.9;
  }
  gl_FragColor = vec4(uColor*c*uAlpha, 1.0);
}`

export const SEAL_FRAGMENT = `
uniform sampler2D uMap; uniform float uTime; uniform float uAlpha; uniform vec3 uColor;
varying vec2 vUv;
void main(){
  vec2 q = vUv - 0.5;
  float s = sin(uTime*0.05), c = cos(uTime*0.05);
  q = mat2(c, -s, s, c)*q;
  vec4 t = texture2D(uMap, q + 0.5);
  float d = length(vUv - 0.5)*2.0;
  float a = t.a * (1.0 - smoothstep(0.9, 1.0, d));
  gl_FragColor = vec4(uColor*a*uAlpha, 1.0);
}`

export const ORBIT_VERTEX = `
attribute float aAngle;
varying float vAngle;
void main(){ vAngle = aAngle; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`

export const ORBIT_FRAGMENT = `
uniform vec3 uColor; uniform vec3 uTrail; uniform float uAlpha; uniform float uPhase; uniform float uSelected;
varying float vAngle;
void main(){
  float behind = fract(vAngle - uPhase);
  float trail = exp(-behind*9.0);
  vec3 c = uColor*uAlpha*(0.55 + 0.45*uSelected) + uTrail*trail*(0.32 + 0.5*uSelected);
  gl_FragColor = vec4(c, 1.0);
}`

export const ROUTE_VERTEX = `
attribute float aT; attribute float aSide;
uniform vec3 uA; uniform vec3 uB; uniform vec3 uC; uniform vec2 uResolution; uniform float uWidth; uniform float uTime; uniform float uStyle; uniform float uHover;
varying float vT; varying float vSide;
vec3 bez(float t){ float u = 1.0 - t; return u*u*uA + 2.0*u*t*uC + t*t*uB; }
void main(){
  vec3 p = bez(aT);
  vec3 pa = bez(clamp(aT - 0.004, 0.0, 1.0)), pb = bez(clamp(aT + 0.004, 0.0, 1.0));
  mat4 vp = projectionMatrix*viewMatrix;
  vec4 c = vp*vec4(p, 1.0), ca = vp*vec4(pa, 1.0), cb = vp*vec4(pb, 1.0);
  vec2 sa = ca.xy/ca.w*uResolution, sb = cb.xy/cb.w*uResolution;
  vec2 dir = sb - sa; dir = length(dir) > 1e-5 ? normalize(dir) : vec2(1.0, 0.0);
  vec2 nrm = vec2(-dir.y, dir.x);
  float w = uWidth*(1.0 + uHover*0.7);
  if (uStyle > 7.5) w *= 0.75 + 0.45*sin(aT*34.0 - uTime*2.6);
  c.xy += nrm*aSide*w/uResolution*c.w;
  vT = aT; vSide = aSide;
  gl_Position = c;
}`

export const ROUTE_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform float uIntensity; uniform float uTime; uniform float uLength; uniform float uStyle; uniform float uAlpha; uniform float uHover; uniform float uSeed; uniform float uFlow;
varying float vT; varying float vSide;
void main(){
  float s = vT*uLength;
  float sd = vSide*vSide;
  float prof = exp(-sd*4.5); float core = exp(-sd*38.0);
  float m = 1.0; vec3 col = uColor; float dark = 0.0;
  float tt = uTime*uFlow;
  int st = int(uStyle + 0.5);
  if (st == 0) {
    core *= 1.4;
    m = 0.95 + 0.08*sin(s*0.035 - tt*1.4);
  } else if (st == 1) {
    m = step(fract(s/15.0 - tt*0.12), 0.56);
  } else if (st == 2) {
    float f = fract(s/8.0 - tt*0.25);
    float dt = 1.0 - smoothstep(0.18, 0.42, length(vec2((f - 0.5)*2.4, vSide)));
    prof = dt; core = dt;
    col = mix(uColor, vec3(0.55, 0.72, 1.0), 0.5 + 0.5*sin(s*0.06 + uTime*1.4));
    col *= 0.7 + 0.6*(0.5 + 0.5*sin(s*0.9 - uTime*3.0));
  } else if (st == 3) {
    float n = snoise(vec3(s*0.05 - tt*0.5, vSide*1.6, uSeed));
    float speck = smoothstep(0.55, 0.9, n)*core;
    dark = exp(-sd*2.2)*0.85;
    col = uColor*(gauss((abs(vSide) - 0.62)*5.0)*0.55 + speck*1.2);
    prof = 1.0; core = 0.0;
  } else if (st == 4) {
    float seg = floor(s/18.0);
    float fl = step(0.38, fract(sin(seg*12.9898 + floor(uTime*7.0)*3.17)*43758.5453));
    m = mix(0.08, 1.25, fl);
  } else if (st == 5) {
    m = 0.3 + 0.7*step(fract(s/5.0 - tt*0.35), 0.35);
    prof *= 0.6;
  } else if (st == 6) {
    float f = fract(s/22.0 - tt*0.14);
    m = step(f, 0.5) + step(0.62, f)*step(f, 0.72);
  } else if (st == 7) {
    float f = fract(s/13.0 - tt*0.1);
    float dt = 1.0 - smoothstep(0.12, 0.32, length(vec2((f - 0.5)*2.0, vSide)));
    prof = dt; core = dt;
  } else {
    m = 0.8 + 0.4*sin(vT*34.0 - uTime*2.6);
  }
  float ends = smoothstep(0.0, 0.035, vT)*(1.0 - smoothstep(0.965, 1.0, vT));
  float k = uIntensity*(1.0 + uHover*0.9)*ends*uAlpha;
  vec3 o = col*(prof*0.45 + core*1.15)*m*k;
  gl_FragColor = vec4(o, dark*ends*uAlpha);
}`

export const VORTEX_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform float uTime; uniform float uAlpha; uniform float uSeed;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float a = atan(q.y, q.x + 1e-5) + uTime*0.8 + d*4.0;
  float n = snoise(vec3(cos(a)*d*2.0, sin(a)*d*2.0, uTime*0.2 + uSeed))*0.5 + 0.5;
  float m = (1.0 - smoothstep(0.2, 1.0, d))*(0.25 + 0.75*n);
  gl_FragColor = vec4(uColor*m*0.45*uAlpha, 1.0);
}`

export const GLOW_FRAGMENT = `
uniform vec3 uColor; uniform float uAlpha;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = dot(q,q);
  if (d > 1.0) discard;
  float core = exp(-d*18.0);
  float halo = exp(-d*4.0)*0.6;
  vec2 tip = q - vec2(0.0, 0.18);
  float arrow = step(abs(tip.x)*1.6 + tip.y*-1.0, 0.25) * step(-0.35, tip.y) * step(tip.y, 0.3);
  vec3 c = uColor*(halo + core) + vec3(1.0)*arrow*0.9;
  gl_FragColor = vec4(c*uAlpha, 1.0);
}`

export const VOYAGE_VERTEX = `
uniform float uSize; uniform float uAngle;
varying vec2 vUv;
void main(){
  vUv = uv;
  vec4 mv = modelViewMatrix * vec4(0.0,0.0,0.0,1.0);
  float c = cos(uAngle), s = sin(uAngle);
  vec2 p = vec2(c*position.x - s*position.y, s*position.x + c*position.y);
  mv.xy += p * uSize;
  gl_Position = projectionMatrix * mv;
}`
