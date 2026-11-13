import { NOISE } from './noise'

export const STAR_VERTEX = `
varying vec3 vObj; varying vec3 vNormalW; varying vec3 vPosW;
void main(){
  vObj = position;
  vec4 wp = modelMatrix*vec4(position,1.0);
  vPosW = wp.xyz; vNormalW = normalize(mat3(modelMatrix)*normal);
  gl_Position = projectionMatrix*viewMatrix*wp;
}`

export const STAR_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform vec3 uEdge; uniform float uIntensity; uniform float uTime; uniform float uSeed;
uniform int uKind; uniform float uPulse; uniform float uHover;
varying vec3 vObj; varying vec3 vNormalW; varying vec3 vPosW;
void main(){
  vec3 p = normalize(vObj);
  vec3 N = normalize(vNormalW); vec3 V = normalize(cameraPosition - vPosW);
  float mu = clamp(dot(N,V), 0.0, 1.0);
  float g1 = fbm(p*3.2 + vec3(0.0, 0.0, uTime*0.035) + uSeed, 5);
  float g2 = snoise(p*15.0 + vec3(uTime*0.09)) * 0.5 + 0.5;
  vec3 col = mix(uEdge, uColor, smoothstep(-0.4, 0.4, g1)) * (0.62 + 0.55*g2);
  col *= 0.5 + 0.5*pow(max(mu, 0.0), 0.55);
  col += vec3(1.0, 0.97, 0.92) * pow(max(mu, 0.0), 3.0) * 0.45;
  col *= uIntensity;
  if (uKind == 1) {
    float cr = smoothstep(0.86, 0.985, 1.0 - abs(snoise(p*4.5 + uSeed)));
    col = vec3(0.10, 0.105, 0.11) * (0.6 + 0.6*g2) * (0.4 + 0.6*mu);
    col += uColor * cr * (0.9 + 0.5*sin(uTime*0.7 + g1*6.0)) * 1.4;
  } else if (uKind == 2) {
    col = uColor * pow(max(1.0 - mu, 0.0), 10.0) * 1.6;
  } else if (uKind == 3) {
    vec2 w = worley(p*3.3 + uSeed);
    float crack = 1.0 - smoothstep(0.015, 0.09, w.y - w.x);
    vec3 plate = uEdge * (0.22 + 0.25*g2) * (0.5 + 0.5*mu);
    col = mix(plate, vec3(1.0, 0.93, 0.78) * uIntensity * 2.4, crack);
  } else if (uKind == 4) {
    col *= 0.55 + uPulse*1.1;
  } else if (uKind == 7) {
    float bands = 0.5 + 0.5*sin(p.y*11.0 + g1*2.6 + uSeed);
    col = mix(uEdge*0.35, uColor*0.75, bands) * (0.45 + 0.55*pow(max(mu, 0.0), 0.7));
    col += uColor*pow(max(1.0 - mu, 0.0), 4.0)*0.35;
  } else if (uKind == 8) {
    float dust = smoothstep(-0.25, 0.55, fbm(p*3.6 + vec3(uTime*0.02) + uSeed*2.0, 5));
    col = mix(col, uEdge*0.22, dust*0.72);
  } else if (uKind == 9) {
    col *= 0.62 + 0.75*uPulse;
  } else if (uKind == 10) {
    float lon = atan(p.z, p.x);
    float chain = smoothstep(0.9, 0.975, abs(sin(p.y*6.5 + sin(lon*3.0 + uSeed)*0.35)));
    float link = step(0.5, fract(lon*9.0/6.2831 + p.y*2.0));
    col = mix(col, vec3(0.04, 0.035, 0.03), chain*(0.75 + 0.25*link));
    col += uColor*smoothstep(0.8, 0.9, abs(sin(p.y*6.5 + sin(lon*3.0 + uSeed)*0.35)))*(1.0 - chain)*0.9*(0.6 + 0.4*sin(uTime*1.1 + lon*4.0));
  } else if (uKind == 11) {
    float iris = smoothstep(0.62, 0.76, mu)*(1.0 - smoothstep(0.93, 0.965, mu));
    float rays = 0.6 + 0.4*sin(atan(vObj.y, vObj.x)*28.0 + g1*4.0);
    float pupil = smoothstep(0.955, 0.975, mu);
    col = mix(col, uEdge*1.6*rays, iris);
    col = mix(col, vec3(0.0), pupil*(0.9 + 0.1*sin(uTime*0.4)));
  } else if (uKind == 12) {
    float loops = smoothstep(0.95, 1.0, abs(sin(atan(p.y, length(p.xz))*7.0 + uTime*0.6)));
    col *= 0.45 + uPulse*1.5;
    col += vec3(0.6, 0.8, 1.0)*loops*0.6;
  }
  col += vec3(0.25, 0.2, 0.12) * uHover * pow(max(1.0 - mu, 0.0), 2.0);
  gl_FragColor = vec4(col, 1.0);
}`

export const CORONA_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform float uIntensity; uniform float uTime; uniform float uSeed; uniform float uCore;
uniform float uRays; uniform float uSpike; uniform int uMode; uniform float uPulse;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float a = atan(q.y, q.x + 1e-5); vec2 cs = vec2(cos(a), sin(a));
  float x = max(d - uCore, 0.0) / (1.0 - uCore);
  vec3 col = vec3(0.0);
  if (uMode == 0) {
    float glow = exp(-x*6.0)*0.55 + exp(-x*18.0)*1.0 + (1.0 - smoothstep(0.0, 1.0, x))*0.035;
    float r1 = max(snoise(vec3(cs*3.5, uTime*0.05 + uSeed)), 0.0);
    float r2 = max(snoise(vec3(cs*9.0, uTime*0.08 + uSeed + 4.0)), 0.0);
    float rays = (r1*r1*0.9 + r2*r2*r2*1.4) * exp(-x*3.2) * uRays;
    float spike = (exp(-abs(q.x)*140.0) + exp(-abs(q.y)*140.0)) * exp(-d*2.6) * uSpike;
    col = uColor*(glow + rays) + vec3(1.0)*(exp(-x*28.0)*0.5 + spike);
    col *= 1.0 + uPulse*0.9;
  } else if (uMode == 1) {
    float ring = gauss((d - uCore*1.03)*38.0);
    float halo = exp(-max(d - uCore, 0.0)*9.0) * 0.35;
    float flicker = 0.75 + 0.25*snoise(vec3(cs*4.0, uTime*0.2 + uSeed));
    col = (vec3(1.0, 0.82, 0.62)*ring*2.4 + uColor*halo) * flicker;
  } else if (uMode == 2) {
    float n = fbm(vec3(q*2.4, uSeed + uTime*0.01), 5);
    float shell = gauss((d - 0.62 - n*0.12)*7.0);
    float fil = pow(clamp(1.0 - abs(snoise(vec3(q*5.0, uSeed + 3.0)))*2.2, 0.0, 1.0), 3.0);
    col = mix(uColor, vec3(0.45, 0.85, 0.85), smoothstep(0.4, 0.85, d)) * shell * (0.5 + fil) * 0.9;
    col += uColor * exp(-d*14.0) * 0.6;
  } else {
    float ph = fract(uTime*0.07 + uSeed);
    float rr = uCore + ph*(1.0 - uCore);
    col = uColor * gauss((d - rr)*22.0) * (1.0 - ph) * 1.4;
  }
  col *= (1.0 - smoothstep(0.72, 1.0, d));
  gl_FragColor = vec4(col*uIntensity, 1.0);
}`

export const DARK_HALO_FRAGMENT = `
uniform float uCore; uniform float uAlpha;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float a = (1.0 - smoothstep(uCore, 1.0, d));
  gl_FragColor = vec4(vec3(0.0), a*a*uAlpha);
}`

export const DISK_VERTEX = `
varying vec3 vLocal; varying vec3 vPosW;
void main(){ vLocal = position; vec4 wp = modelMatrix*vec4(position,1.0); vPosW = wp.xyz; gl_Position = projectionMatrix*viewMatrix*wp; }`

export const DISK_FRAGMENT = `
${NOISE}
uniform float uInner; uniform float uOuter; uniform float uTime; uniform float uSeed; uniform vec3 uCenter; uniform vec3 uNormal; uniform float uIntensity;
varying vec3 vLocal; varying vec3 vPosW;
void main(){
  float r = length(vLocal.xy);
  float u = clamp((r - uInner)/(uOuter - uInner), 0.0, 1.0);
  float a = atan(vLocal.y, vLocal.x);
  float aa = a + uTime*0.35/(0.25 + u);
  vec2 cs = vec2(cos(aa), sin(aa));
  float n = fbm(vec3(cs*(1.2 + u*5.0), u*9.0 + uSeed), 4);
  float streak = 0.45 + 0.55*smoothstep(-0.5, 0.6, n);
  float prof = smoothstep(0.0, 0.06, u) * pow(max(1.0 - u, 0.0), 1.7);
  vec3 hot = mix(vec3(1.0, 0.95, 0.86), vec3(1.0, 0.52, 0.18), smoothstep(0.0, 0.32, u));
  hot = mix(hot, vec3(0.5, 0.22, 0.7), smoothstep(0.35, 1.0, u));
  vec3 V = normalize(cameraPosition - vPosW);
  vec3 tg = normalize(cross(uNormal, vPosW - uCenter));
  float dop = 0.55 + 0.6*clamp(dot(tg, V), -1.0, 1.0);
  gl_FragColor = vec4(hot*prof*streak*dop*uIntensity, 1.0);
}`

export const BEAM_VERTEX = `
varying vec3 vNormalW; varying vec3 vPosW; varying float vAlong;
void main(){
  vAlong = uv.y;
  vec4 wp = modelMatrix*vec4(position,1.0);
  vPosW = wp.xyz; vNormalW = normalize(mat3(modelMatrix)*normal);
  gl_Position = projectionMatrix*viewMatrix*wp;
}`

export const BEAM_FRAGMENT = `
uniform vec3 uColor; uniform float uIntensity;
varying vec3 vNormalW; varying vec3 vPosW; varying float vAlong;
void main(){
  vec3 V = normalize(cameraPosition - vPosW);
  float fres = pow(max(1.0 - abs(dot(normalize(vNormalW), V)), 0.0), 1.5);
  float fade = pow(max(vAlong, 0.0), 2.0);
  gl_FragColor = vec4(uColor * fres * fade * uIntensity, 1.0);
}`
