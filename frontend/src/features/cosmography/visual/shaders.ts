import { NOISE } from '@/features/cosmos/scene3d/shaders/noise'

export const QUAD_VERTEX = `
varying vec2 vUv;
void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`

export const CORE_FRAGMENT = `
uniform vec3 uColor; uniform vec3 uEdge; uniform float uStrength; uniform float uTime;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = dot(q,q);
  if (d > 1.0) discard;
  float pulse = 0.92 + 0.08*sin(uTime*0.8);
  float core = exp(-d*22.0);
  float halo = exp(-d*5.0)*0.55;
  float wide = exp(-d*1.6)*0.18;
  vec3 c = uColor*core*1.6 + mix(uEdge, uColor, 0.4)*halo + uEdge*wide;
  float fade = 1.0 - smoothstep(0.35, 1.0, sqrt(d));
  gl_FragColor = vec4(c*uStrength*pulse*fade, 1.0);
}`

export const CLOUD_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform float uIntensity; uniform float uSeed; uniform float uTime;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float n = fbm(vec3(q*1.8, uSeed + uTime*0.01), 5);
  float m = (1.0 - smoothstep(0.05, 1.0, d)) * smoothstep(-0.3, 0.6, n + (0.45 - d*0.55));
  gl_FragColor = vec4(uColor*m*uIntensity, 1.0);
}`

export const SHELL_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform float uIntensity; uniform float uSeed; uniform float uTime;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float n = fbm(vec3(q*3.0, uSeed + uTime*0.02), 4);
  float band = (d - 0.72)*7.0;
  float ring = exp(-band*band) * (0.6 + 0.6*n);
  float inner = exp(-d*d*10.0)*0.25;
  gl_FragColor = vec4(uColor*(ring + inner)*uIntensity, 1.0);
}`

export const DARK_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform float uIntensity; uniform float uSeed;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float n = fbm(vec3(q*2.2, uSeed), 5);
  float m = (1.0 - smoothstep(0.1, 1.0, d)) * smoothstep(-0.2, 0.5, n + (0.4 - d*0.5));
  gl_FragColor = vec4(uColor, m*uIntensity);
}`

export const DARK_DUST_VERTEX = `
attribute float aSize;
uniform float uRatio; uniform float uAttenuate;
void main(){
  vec4 mv = modelViewMatrix*vec4(position,1.0);
  gl_Position = projectionMatrix*mv;
  gl_PointSize = max(aSize*uRatio*clamp(uAttenuate / -mv.z, 0.35, 3.0), 1.0);
}`

export const DARK_DUST_FRAGMENT = `
uniform vec3 uColor; uniform float uAlpha;
void main(){
  vec2 q = gl_PointCoord*2.0-1.0; float d = dot(q,q);
  if (d > 1.0) discard;
  gl_FragColor = vec4(uColor, exp(-d*2.5)*uAlpha);
}`

export const PLANE_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform vec3 uAccent; uniform float uAlpha; uniform float uTime; uniform float uSeed; uniform float uRings;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float a = atan(q.y, q.x);
  float swirl = a + d*3.4 - uTime*0.01;
  vec2 s = vec2(cos(swirl), sin(swirl))*d*2.2;
  float n = fbm(vec3(s, uSeed + uTime*0.012), 5);
  float m = fbm(vec3(q*4.0, uSeed*1.7 - uTime*0.02), 3);
  float near = (d - 0.975)*70.0; float wide = (d - 0.96)*12.0;
  float rim = exp(-near*near)*1.1 + exp(-wide*wide)*0.16;
  float shimmer = 0.75 + 0.25*sin(a*24.0 + uTime*0.6 + n*4.0);
  float grid = smoothstep(0.992, 1.0, abs(sin(d*uRings*3.14159))) * 0.16 * (1.0 - d*0.6);
  float spokes = smoothstep(0.997, 1.0, abs(sin(a*6.0))) * 0.08 * (1.0 - d);
  float body = (1.0 - smoothstep(0.0, 1.0, d)) * (0.04 + 0.13*smoothstep(-0.15, 0.7, n));
  float veins = smoothstep(0.35, 0.75, m) * (1.0 - d) * 0.1;
  float heart = exp(-d*d*28.0)*0.1;
  vec3 c = uColor*(rim*shimmer + grid + spokes + body) + uAccent*(veins + body*0.6*smoothstep(0.1, 0.8, n)) + mix(uColor, vec3(1.0), 0.5)*heart;
  gl_FragColor = vec4(c*uAlpha, 1.0);
}`

export const CURTAIN_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform vec3 uAccent; uniform float uAlpha; uniform float uTime; uniform float uSeed;
varying vec2 vUv;
void main(){
  float up = vUv.y;
  float n = fbm(vec3(vUv.x*28.0, up*1.6 - uTime*0.05, uSeed), 4);
  float wave = clamp(0.5 + 0.5*sin(vUv.x*6.28318*64.0 + n*5.0), 0.0, 1.0);
  float rays = 0.45 + 0.55*wave*wave*wave;
  float fade = pow(clamp(1.0 - up, 0.0, 1.0), 2.6) * smoothstep(0.0, 0.03, up);
  float body = smoothstep(-0.35, 0.65, n);
  vec3 c = mix(uColor, uAccent, smoothstep(0.1, 0.9, up + n*0.3));
  gl_FragColor = vec4(max(c*fade*body*rays*uAlpha, 0.0), 1.0);
}`

export const DEEP_SKY_FRAGMENT = `
${NOISE}
uniform vec3 uBg; uniform vec3 uViolet; uniform vec3 uTeal; uniform vec3 uRose; uniform vec3 uGold; uniform vec3 uBone; uniform float uTime;
varying vec3 vDir;
void main(){
  vec3 d = normalize(vDir);
  float warp = fbm(d*1.3 + 7.0, 3);
  float a = fbm(d*1.7 + warp*1.2 + vec3(0.0, uTime*0.003, 0.0), 5);
  float b = fbm(d*2.6 - warp*0.9 + 19.0, 5);
  float c = fbm(d*5.2 + warp + 41.0, 4);
  float bandY = d.y*0.82 + d.z*0.38 + warp*0.2;
  float band = exp(-bandY*bandY*5.5);
  vec3 col = uBg;
  col += uViolet * smoothstep(-0.1, 0.75, a) * 0.11;
  col += uTeal * smoothstep(0.05, 0.85, b) * 0.075;
  col += uRose * smoothstep(0.3, 0.9, a + b*0.6) * 0.06;
  col += uGold * smoothstep(0.3, 0.9, c) * band * 0.06;
  col += uBone * band * (0.035 + 0.04*smoothstep(-0.2, 0.6, c));
  col *= 1.0 - 0.5*smoothstep(0.15, 0.65, c*b*2.5) * band;
  col *= 0.7 + 0.3*smoothstep(-0.9, 0.3, d.y);
  gl_FragColor = vec4(col, 1.0);
}`

export const FAR_GALAXY_VERTEX = `
attribute float aSize; attribute vec3 aColor; attribute float aSeed;
uniform float uRatio;
varying vec3 vColor; varying float vSeed;
void main(){
  vec4 mv = modelViewMatrix*vec4(position,1.0);
  gl_Position = projectionMatrix*mv;
  gl_PointSize = max(aSize*uRatio, 1.0);
  vColor = aColor; vSeed = aSeed;
}`

export const FAR_GALAXY_FRAGMENT = `
varying vec3 vColor; varying float vSeed;
void main(){
  vec2 q = gl_PointCoord*2.0-1.0;
  float turn = vSeed*6.28318; float c = cos(turn); float s = sin(turn);
  q = vec2(c*q.x - s*q.y, s*q.x + c*q.y);
  q.y /= 0.22 + 0.6*fract(vSeed*7.31);
  float d = dot(q,q);
  if (d > 1.0) discard;
  float r = sqrt(d); float th = atan(q.y, q.x);
  float arms = step(0.5, fract(vSeed*3.7)) * (0.5 + 0.5*sin(th*2.0 - r*10.0)) * exp(-d*3.0) * 0.5;
  float light = exp(-d*22.0)*1.2 + exp(-d*4.5)*0.4 + arms;
  gl_FragColor = vec4(vColor*light*(1.0 - d), 1.0);
}`

export const FLARE_FRAGMENT = `
varying vec3 vColor; varying float vSeed;
void main(){
  vec2 q = gl_PointCoord*2.0-1.0; float d = dot(q,q);
  if (d > 1.0) discard;
  float spikes = exp(-abs(q.x)*36.0)*exp(-abs(q.y)*2.6) + exp(-abs(q.y)*36.0)*exp(-abs(q.x)*2.6);
  float light = exp(-d*40.0)*1.6 + exp(-d*7.0)*0.25 + spikes*0.7;
  gl_FragColor = vec4(vColor*light*(1.0 - d), 1.0);
}`

export const BEAM_FRAGMENT = `
uniform vec3 uColor; uniform float uAlpha; uniform float uTime;
varying vec2 vUv;
void main(){
  float across = abs(vUv.x*2.0-1.0);
  float body = exp(-across*across*14.0);
  float flow = 0.6 + 0.4*sin(vUv.y*28.0 - uTime*3.0);
  gl_FragColor = vec4(uColor*body*flow*uAlpha, 1.0);
}`

export const DIMENSION_FRAGMENT = `
${NOISE}
uniform vec3 uCore; uniform vec3 uBody; uniform vec3 uEdge; uniform vec3 uRingColor;
uniform float uMode; uniform float uTime; uniform float uSeed; uniform float uSpin;
uniform float uTurb; uniform float uSparkle; uniform float uHalo; uniform float uVeil;
uniform float uFlicker; uniform float uLight; uniform float uRing; uniform float uTone;
varying vec2 vUv;
const float R = 0.6;
const float TAU = 6.28318;

vec3 turnY(vec3 p, float a){ float c = cos(a); float s = sin(a); return vec3(c*p.x + s*p.z, p.y, -s*p.x + c*p.z); }
float ridge(float v){ float k = 1.0 - abs(v); return k*k; }
float specks(vec3 p, float density){
  vec3 cell = floor(p); vec3 h = hash33(cell);
  vec3 f = fract(p) - 0.5 - (h - 0.5)*0.6;
  return step(1.0 - density, h.x) * exp(-dot(f, f)*420.0) * (0.6 + 0.4*sin(uTime*(1.0 + h.y*3.0) + h.z*20.0));
}
vec3 film(float hue){ return 0.5 + 0.5*cos(TAU*(hue + vec3(0.0, 0.33, 0.67))); }

vec3 interior(int mode, vec3 p, vec3 deep, vec2 q, float s, float t){
  float w = fbm(p*1.4 + uSeed, 3);
  if (mode == 0) {
    float a = fbm(p*2.2 + w*1.6, 5);
    float b = fbm(deep*3.1 - w, 4);
    vec3 c = mix(uBody*0.18, uBody, smoothstep(-0.25, 0.65, a));
    c += uEdge*smoothstep(0.1, 0.8, b)*0.45;
    c += uCore*smoothstep(0.35, 0.9, a + b*0.5)*0.9;
    return c + uCore*exp(-s*s*6.0)*0.5;
  }
  if (mode == 1) {
    float f = fbm(p*2.6 + w*2.4*uTurb + vec3(0.0, t*0.08, 0.0), 5);
    float r1 = ridge(f); float r2 = ridge(fbm(deep*5.0 - w*2.0, 4));
    vec3 c = uBody*0.16*(0.6 + 0.8*smoothstep(-0.3, 0.6, f));
    c += uEdge*r1*r1*1.4 + uCore*r1*r1*r1*r1*2.2 + uEdge*r2*r2*r2*0.6;
    return c;
  }
  if (mode == 2) {
    vec2 cell = worley(p*3.2 + uSeed);
    vec2 inner = worley(deep*6.0 - uSeed);
    float edge = 1.0 - smoothstep(0.0, 0.07, cell.y - cell.x);
    float fine = 1.0 - smoothstep(0.0, 0.05, inner.y - inner.x);
    vec3 c = uBody*0.12*(0.4 + cell.x) + uEdge*edge*1.5 + uBody*fine*0.35;
    return c + uCore*exp(-s*s*7.0)*0.55 + uCore*edge*(1.0 - smoothstep(0.0, 0.6, s))*0.4;
  }
  if (mode == 3) {
    vec3 c = uBody*0.03;
    float a = atan(q.y, q.x);
    float swirl = fbm(vec3(a*2.0 + t*0.3, s*5.0, uSeed), 4);
    float disc = (s - 0.86)*11.0; float photon = (s - 0.975)*55.0;
    c += uCore*exp(-disc*disc)*(0.55 + 0.6*swirl);
    c += uEdge*exp(-disc*disc*0.25)*0.25;
    c += mix(uCore, vec3(1.0), 0.5)*exp(-photon*photon)*1.4;
    return c * smoothstep(0.35, 0.8, s) + uEdge*0.02;
  }
  if (mode == 4) {
    float a = atan(q.y, q.x);
    float fold = abs(mod(a + t*uSpin*0.5, TAU/6.0) - TAU/12.0);
    vec2 k = vec2(cos(fold), sin(fold))*s;
    float g = fbm(vec3(k*3.4, uSeed + t*0.04), 5);
    vec3 c = mix(uEdge*0.18, uBody*0.85, smoothstep(-0.1, 0.6, g));
    float glint = abs(sin(g*14.0)); glint = glint*glint*glint*glint*glint*glint;
    c += uCore*glint*0.7;
    vec2 spot = q/R - vec2(-0.32, 0.38);
    return c + vec3(1.0)*exp(-dot(spot, spot)*16.0)*0.55;
  }
  if (mode == 5) {
    float v = fbm(vec3(p.x*2.0, p.y*0.6 - t*0.05, p.z*2.0) + uSeed, 4);
    float bands = smoothstep(0.55, 1.0, 0.5 + 0.5*sin(p.y*9.0 + v*7.0 + t*0.2));
    float mist = smoothstep(-0.3, 0.7, fbm(deep*2.0 + w, 4));
    vec3 c = uBody*(0.12 + 0.4*mist) + uEdge*bands*(0.4 + 0.8*uTurb)*0.9;
    return c + uCore*smoothstep(0.3, 0.95, v)*0.45;
  }
  if (mode == 6) {
    float grain = worley(p*6.5 + vec3(0.0, t*0.05, 0.0)).x;
    float boil = fbm(p*3.6 + vec3(t*0.06), 5);
    float heat = clamp(1.0 - grain*1.3 + boil*0.6, 0.0, 1.0);
    vec3 c = mix(uEdge*0.55, uBody*1.35, heat);
    c = mix(c, uCore*1.8, smoothstep(0.55, 1.0, heat));
    return c*(0.95 + 0.6*boil);
  }
  if (mode == 7) {
    float a = atan(q.y, q.x);
    float n = fbm(vec3(a*3.0, t*0.1, uSeed), 3);
    float rays = abs(sin(a*7.0 + n*2.0 + t*0.1)); rays = rays*rays*rays*rays*rays*rays*rays*rays;
    vec3 c = uBody*0.35*(1.0 - s*s) + uCore*exp(-s*s*3.5)*1.3;
    c += uCore*rays*(1.0 - s)*0.55 + uEdge*smoothstep(-0.2, 0.7, fbm(p*2.0 + w, 4))*0.3;
    return c;
  }
  if (mode == 8) {
    float limb = sqrt(max(1.0 - s*s, 0.0));
    float hue = fract(fbm(p*1.8 + uSeed, 3)*0.8 + s*1.2 + t*0.02);
    float rim = 1.0 - limb; rim = rim*rim;
    vec3 c = mix(film(hue), uEdge, 0.35)*(0.08 + rim*1.1);
    float a = atan(q.y, q.x); float inner = s/0.3;
    float arms = 0.5 + 0.5*sin(a*2.0 - log(inner + 0.05)*4.0 - t*0.3);
    c += (uCore*exp(-inner*inner*3.0) + uBody*arms*exp(-inner*inner*1.2)*0.6)*step(inner, 1.6);
    return c;
  }
  if (mode == 9) {
    vec3 c = uBody*0.06;
    for (int i = 0; i < 5; i++) {
      float fi = float(i);
      float h = -0.72 + fi*0.36 + fbm(vec3(p.xz*1.6, fi*3.1 + uSeed + t*0.03), 3)*0.18;
      float d = (p.y - h)*14.0;
      c += mix(uBody, uEdge, mod(fi, 2.0))*exp(-d*d)*(0.55 + 0.35*fbm(vec3(p.xz*3.0, fi + t*0.05), 3));
    }
    return c + uCore*exp(-s*s*8.0)*0.35;
  }
  if (mode == 10) {
    float inner = s/0.42;
    vec3 c = uEdge*0.05 + uBody*smoothstep(-0.2, 0.7, fbm(p*1.8 + w, 4))*0.12;
    if (inner < 1.0) {
      float a = fbm(deep*4.0 + uSeed, 5);
      vec3 core = mix(uBody*0.3, uBody*1.1, smoothstep(-0.2, 0.6, a)) + uCore*exp(-inner*inner*3.0)*0.9;
      float shell = (inner - 0.97)*30.0;
      c = core + uEdge*exp(-shell*shell)*0.9;
    }
    return c;
  }
  if (mode == 11) {
    vec2 cell = worley(p*3.6 + uSeed);
    float crack = 1.0 - smoothstep(0.0, 0.06, cell.y - cell.x);
    float glow = smoothstep(-0.2, 0.8, fbm(p*2.2 + vec3(t*0.05), 4));
    vec3 c = uBody*(0.5 + 0.5*glow) + uEdge*glow*0.25;
    c += uEdge*crack*1.3 + uCore*crack*crack*crack*1.2;
    return c + uEdge*exp(-s*s*4.0)*0.3;
  }
  if (mode == 12) {
    float smoke = fbm(p*1.8 + w*1.5*uTurb + vec3(0.0, -t*0.04, 0.0), 5);
    float wisp = ridge(fbm(deep*3.0 + w, 4));
    vec3 c = uBody*0.4 + uEdge*smoothstep(0.1, 0.8, smoke)*0.35 + uCore*wisp*wisp*wisp*0.55;
    return c*mix(0.35, 1.0, smoothstep(0.0, 0.9, s));
  }
  if (mode == 13) {
    float warp = fbm(p*2.0 + uSeed, 3)*1.6;
    float r1 = ridge(snoise(p*2.6 + warp)); float r2 = ridge(snoise(p*6.0 - warp + t*0.05));
    float r18 = r1*r1*r1*r1; r18 = r18*r18*r18;
    float r28 = r2*r2*r2*r2; r28 = r28*r28;
    vec3 c = uBody*0.14 + uCore*(r18*1.8 + r28*0.8) + uEdge*r1*r1*0.3;
    return c + uEdge*smoothstep(-0.2, 0.7, fbm(deep*2.0, 3))*0.12;
  }
  if (mode == 14) {
    vec2 cell = worley(p*8.5 + uSeed);
    vec2 big = worley(deep*3.0 - uSeed);
    float edge = 1.0 - smoothstep(0.0, 0.05, cell.y - cell.x);
    vec3 c = uBody*(0.08 + 0.4*cell.x) + uEdge*edge*0.6;
    return c + uCore*(1.0 - smoothstep(0.0, 0.08, big.y - big.x))*0.35;
  }
  if (mode == 15) {
    vec2 left = q/R - vec2(-0.3, 0.05); vec2 right = q/R - vec2(0.3, -0.05);
    float a = fbm(p*2.4 + w, 5);
    vec3 c = uBody*0.12 + uBody*smoothstep(-0.1, 0.7, a)*0.35;
    c += uCore*exp(-dot(left, left)*16.0)*1.1 + uEdge*exp(-dot(left, left)*4.0)*0.4;
    c += uEdge*exp(-dot(right, right)*16.0)*1.1 + uCore*exp(-dot(right, right)*4.0)*0.3;
    float bridge = exp(-q.y*q.y*90.0)*(1.0 - smoothstep(0.0, 0.35, abs(q.x)))*0.35;
    return c + mix(uCore, uEdge, 0.5)*bridge;
  }
  if (mode == 16) {
    float f = fbm(p*2.4 + w*1.4, 5);
    vec3 c = uBody*0.2 + uEdge*smoothstep(0.2, 0.8, f)*0.18;
    float hole = smoothstep(0.1, 0.55, fbm(deep*3.5 + uSeed, 4));
    c *= 1.0 - hole*0.8;
    float b1 = (s - 0.84 - f*0.04)*26.0; float b2 = (s - 0.93 + f*0.03)*30.0;
    c += uEdge*exp(-b1*b1)*1.3 + uCore*exp(-b2*b2)*1.3;
    return c;
  }
  if (mode == 17) {
    float a = atan(q.y, q.x);
    float n = fbm(p*2.0 + w, 4);
    float arm = 0.5 + 0.5*sin(a*3.0 + log(s + 0.04)*5.0 + t*uSpin*6.0 + n*2.0);
    arm = smoothstep(0.55, 1.0, arm);
    vec3 c = uBody*(0.14 + 0.25*smoothstep(-0.2, 0.7, n)) + uEdge*arm*(1.0 - s*0.5)*0.9;
    return c + uCore*exp(-s*s*22.0)*1.4;
  }
  if (mode == 18) {
    vec3 n = vec3(q/R, sqrt(max(1.0 - s*s, 0.0)));
    float light = 0.45 + 0.55*max(dot(n, normalize(vec3(-0.45, 0.55, 0.7))), 0.0);
    vec2 d = q/R;
    float lat = abs(fract(asin(clamp(p.y, -1.0, 1.0))*3.8) - 0.5);
    float lon = abs(fract(atan(p.z, p.x)*2.5) - 0.5);
    float grid = (1.0 - smoothstep(0.0, 0.025, lat)) + (1.0 - smoothstep(0.0, 0.025, lon));
    vec3 c = uBody*(0.05 + grid*0.08)*light + uCore*exp(-s*s*3.0)*0.32;
    float metal = 0.0; float bevel = 0.0;
    for (int i = 0; i < 4; i++) {
      vec2 centre = vec2(-0.18, 0.12); float radius = 0.46; float teeth = 18.0; float turn = 1.0;
      if (i == 1) { centre = vec2(0.394, -0.316); radius = 0.26; teeth = 10.0; turn = -1.0; }
      if (i == 2) { centre = vec2(-0.62, 0.61); radius = 0.2; teeth = 8.0; turn = -1.0; }
      if (i == 3) { centre = vec2(0.66, 0.02); radius = 0.15; teeth = 6.0; turn = 1.0; }
      vec2 v = d - centre; float len = length(v);
      float a = atan(v.y, v.x) - turn*t*0.22*0.46/radius;
      float outer = radius + 0.04*smoothstep(-0.25, 0.25, sin(a*teeth));
      float inside = 1.0 - smoothstep(outer - 0.01, outer, len);
      float rim = inside*smoothstep(radius*0.7 - 0.012, radius*0.7, len);
      float hub = 1.0 - smoothstep(radius*0.2, radius*0.2 + 0.012, len);
      float axle = 1.0 - smoothstep(radius*0.07, radius*0.07 + 0.008, len);
      float spoke = (1.0 - smoothstep(0.1, 0.18, abs(sin(a*2.5))))*inside*(1.0 - smoothstep(radius*0.68, radius*0.7, len));
      float part = max(max(rim, hub), spoke)*(1.0 - axle);
      metal = max(metal, part);
      bevel = max(bevel, (1.0 - smoothstep(0.0, 0.012, abs(len - outer)))*inside + (1.0 - smoothstep(0.0, 0.01, abs(len - radius*0.7)))*inside);
    }
    vec3 brass = mix(uBody*0.35, uBody*0.95 + uCore*0.15, light);
    c = mix(c, brass*(0.8 + 0.2*fbm(p*9.0, 2)), metal) + uEdge*bevel*0.55*light;
    for (int k = 0; k < 2; k++) {
      vec3 axis = k == 0 ? turnY(normalize(vec3(0.35, 1.0, 0.25)), t*0.18) : turnY(normalize(vec3(1.0, 0.25, -0.45)), -t*0.13);
      float across = abs(dot(n, axis));
      float band = 1.0 - smoothstep(0.035, 0.05, across);
      vec3 side = normalize(cross(axis, vec3(0.0, 0.0, 1.0)) + vec3(0.0001));
      float around = atan(dot(n, cross(axis, side)), dot(n, side));
      float tick = (1.0 - smoothstep(0.0, 0.08, abs(fract(around*48.0/6.28318) - 0.5)*2.0 - 0.84))*(1.0 - smoothstep(0.0, 0.02, across));
      c = mix(c, (uCore*0.7 + uBody*0.3)*light, band*0.8) + uCore*tick*band*0.5;
    }
    return c;
  }
  vec3 c = uBody*0.08;
  for (int i = 0; i < 6; i++) {
    float fi = float(i);
    vec2 centre = vec2(sin(t*0.13*(1.0 + fi*0.3) + fi*2.1 + uSeed), cos(t*0.11*(1.0 + fi*0.2) + fi*1.7))*0.45*R;
    vec2 d = (q - centre)/R;
    vec3 tint = mod(fi, 3.0) < 1.0 ? uCore : (mod(fi, 3.0) < 2.0 ? uBody : uEdge);
    c += tint*exp(-dot(d, d)*9.0)*0.55;
  }
  return c + uEdge*smoothstep(-0.2, 0.8, fbm(p*1.6 + w, 4))*0.2;
}

void main(){
  vec2 q = vUv*2.0 - 1.0; float r = length(q);
  if (r > 1.0) discard;
  float t = uTime;
  int mode = int(uMode + 0.5);
  float s = r/R;
  vec3 c = vec3(0.0);
  if (s < 1.0) {
    vec3 n = vec3(q/R, sqrt(max(1.0 - s*s, 0.0)));
    vec3 p = turnY(n, t*uSpin + uSeed);
    vec3 deep = turnY(n*0.72, t*uSpin*0.55 + uSeed*1.3);
    float rim = 1.0 - n.z; rim = rim*rim*rim;
    c = interior(mode, p, deep, q, s, t);
    c += uCore*specks(p*34.0 + uSeed, uSparkle*0.09)*1.6;
    c += uEdge*rim*(0.5 + 0.7*uVeil/100.0)*(mode == 18 ? 0.3 : 1.0);
    c *= (1.0 - smoothstep(0.97, 1.0, s));
  }
  float outside = max(r - R, 0.0);
  float halo = exp(-outside*(13.0 - uHalo*7.0))*smoothstep(R*0.8, R, r);
  c += mix(uEdge, uCore, 0.2)*halo*(0.35 + 0.35*uHalo)*(mode == 18 ? 0.55 : 1.0);
  float flicker = 1.0 - uFlicker*0.35*(0.5 + 0.5*sin(t*5.0 + uSeed*3.0));
  c *= uLight*flicker;
  if (uTone > 0.5) c = vec3(1.0) - exp(-c*1.5);
  float band = (r - 0.93)*40.0;
  c += uRingColor*exp(-band*band)*uRing;
  gl_FragColor = vec4(max(c, 0.0)*(1.0 - smoothstep(0.9, 1.0, r)), 1.0);
}`
