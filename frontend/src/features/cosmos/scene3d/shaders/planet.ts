import { NOISE } from './noise'

export const PLANET_VERTEX = `
uniform float uTime; uniform float uBreath;
varying vec3 vObj; varying vec3 vPosW; varying vec3 vNormalW; varying float vRadius;
void main(){
  vObj = position;
  vec3 pos = position * (1.0 + uBreath*0.03*sin(uTime*1.25));
  vec4 wp = modelMatrix*vec4(pos,1.0);
  vPosW = wp.xyz; vNormalW = normalize(mat3(modelMatrix)*normal);
  vRadius = length(modelMatrix[0].xyz);
  gl_Position = projectionMatrix*viewMatrix*wp;
}`

export const PLANET_FRAGMENT = `
${NOISE}
uniform vec3 uPal[10];
uniform vec3 uStarPos; uniform vec3 uStarColor; uniform float uLit;
uniform float uSea; uniform float uMount; uniform float uMoist; uniform float uSeed; uniform float uTime;
uniform int uType; uniform float uClouds; uniform vec3 uCloudColor; uniform vec3 uAtmColor; uniform float uAtm;
uniform float uCity; uniform vec3 uCityColor; uniform float uDim; uniform float uOpacity; uniform float uHover;
uniform vec3 uCopper; uniform vec3 uViolet;
varying vec3 vObj; varying vec3 vPosW; varying vec3 vNormalW; varying float vRadius;

vec3 palAt(float x){ x = clamp(x, 0.0, 8.999); int i = int(floor(x)); return mix(uPal[i], uPal[i+1], fract(x)); }
float lum(vec3 c){ return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
vec3 bumpNormal(vec3 N, vec3 pos, float h){
  vec3 dpx = dFdx(pos), dpy = dFdy(pos); float dhx = dFdx(h), dhy = dFdy(h);
  vec3 r1 = cross(dpy, N), r2 = cross(N, dpx); float det = dot(dpx, r1);
  vec3 grad = sign(det)*(dhx*r1 + dhy*r2);
  return normalize(abs(det)*N - grad);
}
vec3 envAt(vec3 R){
  float n = fbm(R*2.2 + 5.0, 4);
  vec3 c = vec3(0.006, 0.007, 0.011) + uCopper*smoothstep(0.0, 0.8, n)*0.08 + uViolet*smoothstep(0.2, 0.9, -n)*0.06;
  return c + vec3(pow(max(snoise(R*60.0), 0.0), 12.0)*2.0);
}

void main(){
  vec3 p = normalize(vObj);
  vec3 q = p + vec3(uSeed, uSeed*0.37, -uSeed*0.61);
  vec3 N = normalize(vNormalW);
  vec3 V = normalize(cameraPosition - vPosW);
  vec3 L = uLit > 0.5 ? normalize(uStarPos - vPosW) : normalize(V + vec3(0.3, 0.6, 0.2));
  float ndlG = dot(N, L);
  float term = smoothstep(-0.14, 0.32, ndlG);
  float nv = clamp(dot(N, V), 0.0, 1.0);
  vec3 base; float land = 0.0; float hgt = 0.0; float water = 0.0; float spec = 0.0; float specPow = 70.0;
  vec3 emis = vec3(0.0);
  float bumpAmt = 0.0;
  if (uType == 9) {
    float lat = p.y;
    float flow = uTime*0.012;
    float tw = flow*sin(lat*9.0);
    vec3 fq = vec3(p.x*cos(tw) - p.z*sin(tw), lat, p.x*sin(tw) + p.z*cos(tw));
    float tur = fbm(fq*vec3(2.0, 9.0, 2.0) + q, 5);
    float b = lat*4.2 + tur*0.55 + sin(lat*17.0 + uSeed)*0.18;
    float k = fract(b*0.5 + uSeed*0.13);
    base = palAt(2.0 + k*7.0);
    base = mix(base, uPal[3], 0.25*smoothstep(0.2, 0.8, fbm(fq*14.0 + q, 3)+0.5));
    vec3 eye = normalize(vec3(cos(uSeed*3.0), -0.32, sin(uSeed*3.0)));
    float ed = length(p - eye);
    base = mix(base, uPal[8], (1.0 - smoothstep(0.05, 0.24, ed))*0.85);
    base = mix(base, uPal[9], (1.0 - smoothstep(0.0, 0.06, ed))*0.6);
  } else if (uType == 12) {
    float swirl = fbm(q*2.0 + vec3(0.0, uTime*0.02, 0.0), 5);
    float spiral = sin(atan(p.z, p.x)*3.0 + p.y*6.0 + swirl*4.0 - uTime*0.3);
    base = mix(uPal[0], uPal[1], smoothstep(-0.6, 0.6, swirl)) * 0.25;
    emis += uViolet * smoothstep(0.7, 1.0, spiral) * 0.35;
    emis += uViolet * pow(1.0 - nv, 3.0) * 0.8;
    spec = 0.0;
  } else if (uType == 14) {
    float bands = step(0.5, fract(p.y*9.0 + 0.25));
    float panels = step(0.85, fract(atan(p.z, p.x)*6.0));
    base = mix(uPal[3], uPal[6], bands) * (0.8 + 0.2*panels);
    float windows = step(0.92, fract(p.y*40.0)) * step(0.6, fract(atan(p.z, p.x)*20.0 + p.y*3.0));
    emis += uCityColor * windows * (1.0 - term) * 0.9;
    spec = 0.9; specPow = 120.0;
  } else {
    float warp = fbm(q*1.15, 3);
    float e = fbm(q*1.7 + warp*0.65, 6);
    float rd = 1.0 - abs(snoise(q*3.4 + warp));
    e += (rd*rd - 0.45)*0.22*uMount;
    float s = (uSea - 0.5)*0.72;
    float m = fbm(q*2.3 + 7.1, 4)*0.85 + 0.5 + uMoist;
    float aw = max(fwidth(e)*1.2, 0.002);
    land = smoothstep(s - aw, s + aw, e);
    hgt = clamp((e - s)/(0.72 - s)*(0.7 + 0.5*uMount), 0.0, 1.0);
    water = clamp((s - e)/(s + 0.8), 0.0, 1.0);
    vec3 wc = mix(uPal[0], uPal[1], smoothstep(0.0, 0.32, water));
    vec3 low = mix(mix(uPal[3], uPal[4], smoothstep(0.38, 0.5, m)), uPal[5], smoothstep(0.5, 0.62, m));
    vec3 hill = mix(uPal[6], uPal[7], smoothstep(0.44, 0.56, m));
    vec3 lc = mix(uPal[2], low, smoothstep(0.015, 0.06, hgt));
    lc = mix(lc, hill, smoothstep(0.27, 0.36, hgt));
    lc = mix(lc, uPal[8], smoothstep(0.53, 0.62, hgt));
    lc = mix(lc, uPal[9], smoothstep(0.75, 0.84, hgt));
    lc *= 0.9 + 0.2*(snoise(q*22.0)*0.5 + 0.5);
    base = mix(wc, lc, land);
    if (uType == 0 || uType == 1 || uType == 3) {
      float cv = abs(p.y) + fbm(q*4.0, 3)*0.14; float cw = max(fwidth(cv), 0.01);
      float cap = smoothstep(0.82 - cw, 0.84 + cw, cv);
      base = mix(base, uPal[9], cap); land = max(land, cap);
    }
    spec = (1.0 - land)*0.55;
    bumpAmt = land;
    if (uType == 4) {
      float pul = 0.75 + 0.25*sin(uTime*0.9 + e*14.0);
      emis += uPal[0]*(1.0 - land)*2.2*pul + uPal[1]*(1.0 - land)*0.6;
      float crack = smoothstep(0.93, 0.995, 1.0 - abs(snoise(q*6.5 + warp*1.5)))*land;
      emis += uPal[9]*crack*3.2*pul;
      base = mix(base, base*0.55, land);
      spec = 0.0;
    } else if (uType == 3) {
      spec = 0.35 + 0.4*(1.0 - land); specPow = 36.0;
    } else if (uType == 6 || uType == 15) {
      float br = 0.5 + 0.5*sin(uTime*1.25);
      float vein = smoothstep(0.9, 0.99, 1.0 - abs(snoise(q*5.0 + vec3(0.0, uTime*0.02, 0.0))));
      vec3 veinColor = uType == 15 ? uPal[8] : uPal[9];
      emis += veinColor*vein*(0.35 + 0.9*br)*(uType == 15 ? 0.6 : 1.0);
      base *= (uType == 15 ? 0.7 : 0.9) + 0.15*br;
      spec = 0.25; specPow = 20.0;
    } else if (uType == 7) {
      base = mix(vec3(lum(base)), base, 0.22);
      float mist = smoothstep(-0.1, 0.6, fbm(q*3.0 + vec3(uTime*0.02, 0.0, uTime*0.013), 5));
      base = mix(base, vec3(0.62, 0.64, 0.66), mist*0.55);
      spec *= 0.3;
    } else if (uType == 5) {
      vec3 Nf = normalize(cross(dFdx(vPosW), dFdy(vPosW)));
      N = Nf; ndlG = dot(N, L); term = smoothstep(-0.1, 0.25, ndlG);
      spec = 0.9; specPow = 90.0;
      float fac = fract(sin(dot(floor(Nf*7.0 + 0.5), vec3(12.9898, 78.233, 37.719)))*43758.5453);
      emis += uPal[0]*0.07*smoothstep(0.55, 1.0, fac)*(0.6 + 0.4*sin(uTime*0.8 + fac*40.0));
      bumpAmt = 0.0;
    } else if (uType == 8) {
      float ph = (1.0 - nv)*1.1 + uTime*0.03 + warp*0.5;
      vec3 iri = 0.5 + 0.5*cos(6.2831*(ph + vec3(0.0, 0.33, 0.67)));
      base = mix(mix(base, vec3(lum(base))*vec3(0.95, 0.9, 1.05), 0.35), iri*0.8, 0.3);
      emis += iri*0.05*(1.0 - nv);
    } else if (uType == 10) {
      spec = 1.2; specPow = 240.0; bumpAmt = 0.0;
    } else if (uType == 11) {
      float side = smoothstep(-0.25, 0.35, ndlG);
      vec3 hot = mix(uPal[2], uPal[4], smoothstep(0.2, 0.8, m));
      vec3 cold = mix(uPal[8], uPal[9], smoothstep(0.3, 0.7, m));
      base = mix(cold, mix(base, hot, smoothstep(0.35, 0.8, ndlG)), side);
    } else if (uType == 13) {
      float vein = smoothstep(0.88, 0.99, 1.0 - abs(snoise(q*7.0)));
      base = mix(base, uPal[9], 0.35);
      emis += uCopper * vein * 0.9 + uCopper * pow(1.0 - nv, 2.0) * 0.25;
      spec = 0.8; specPow = 60.0;
    }
  }
  if (bumpAmt > 0.0) N = bumpNormal(N, vPosW, hgt*bumpAmt*vRadius*0.03);
  float ndl = dot(N, L);
  float diff = clamp(ndl*0.94 + 0.06, 0.0, 1.0) * term;
  vec3 H = normalize(L + V);
  vec3 col = base * (uStarColor*diff*1.3 + vec3(0.016, 0.018, 0.026));
  col += uStarColor * pow(max(dot(N, H), 0.0), specPow) * spec * term;
  if (uType == 10) {
    vec3 R = reflect(-V, N);
    float fr = 0.35 + 0.65*pow(1.0 - nv, 3.0);
    col = mix(col, envAt(R) + base*0.18*diff, 0.72) + uStarColor*pow(max(dot(R, L), 0.0), 400.0)*3.0*term*fr;
  }
  if (uClouds > 0.0) {
    float c = fbm(q*2.6 + vec3(uTime*0.006, 0.0, -uTime*0.004) + 13.0, 5);
    float cm = smoothstep(0.05, 0.55, c)*uClouds;
    col = mix(col, uCloudColor*(uStarColor*diff*1.25 + vec3(0.02)), cm);
    emis *= 1.0 - cm*0.6;
  }
  if (uCity > 0.0) {
    float ct = smoothstep(0.55, 0.9, snoise(q*38.0)) * smoothstep(0.2, 0.7, snoise(q*6.0) + 0.5);
    col += uCityColor * ct * land * (1.0 - term) * uCity * 0.9;
  }
  float fr = pow(1.0 - nv, 3.2);
  col += uAtmColor * fr * uAtm * (0.12 + term*0.8);
  col += emis;
  col += vec3(0.95, 0.78, 0.52) * pow(1.0 - nv, 2.4) * uHover * 0.9;
  col = mix(col, vec3(0.02, 0.024, 0.032) + uAtmColor*fr*0.25 + vec3(0.2, 0.22, 0.26)*fr*0.4, uDim);
  gl_FragColor = vec4(col, uOpacity);
}`

export const ATMOSPHERE_VERTEX = `
varying vec3 vPosW;
void main(){ vec4 wp = modelMatrix*vec4(position,1.0); vPosW = wp.xyz; gl_Position = projectionMatrix*viewMatrix*wp; }`

export const ATMOSPHERE_FRAGMENT = `
uniform vec3 uCenter; uniform float uRadius; uniform float uShell; uniform vec3 uColor; uniform float uIntensity; uniform vec3 uStarPos; uniform float uLit;
varying vec3 vPosW;
void main(){
  vec3 dir = normalize(vPosW - cameraPosition);
  vec3 oc = uCenter - cameraPosition;
  float t = dot(oc, dir);
  float b = length(oc - dir*t) / uRadius;
  float x = clamp((b - 1.0)/(uShell - 1.0), 0.0, 1.0);
  float a = pow(1.0 - x, 2.4) * smoothstep(0.88, 1.0, b);
  vec3 nrm = normalize(cameraPosition + dir*t - uCenter);
  vec3 L = uLit > 0.5 ? normalize(uStarPos - uCenter) : nrm;
  float lit = mix(0.12, 1.0, smoothstep(-0.35, 0.55, dot(nrm, L)));
  gl_FragColor = vec4(uColor*a*uIntensity*lit, 1.0);
}`

export const RING_VERTEX = `
varying vec3 vLocal; varying vec3 vPosW;
void main(){ vLocal = position; vec4 wp = modelMatrix*vec4(position,1.0); vPosW = wp.xyz; gl_Position = projectionMatrix*viewMatrix*wp; }`

export const RING_FRAGMENT = `
${NOISE}
uniform float uInner; uniform float uOuter; uniform float uSeed; uniform vec3 uC1; uniform vec3 uC2; uniform vec3 uC3;
uniform vec3 uCenter; uniform float uRadius; uniform vec3 uStarPos; uniform vec3 uStarColor; uniform float uLit; uniform float uOpacity;
varying vec3 vLocal; varying vec3 vPosW;
void main(){
  float r = length(vLocal.xy);
  float u = (r - uInner)/(uOuter - uInner);
  if (u < 0.0 || u > 1.0) discard;
  float n1 = snoise(vec3(u*38.0, uSeed, 0.0))*0.5 + 0.5;
  float n2 = snoise(vec3(u*140.0, uSeed, 3.0))*0.5 + 0.5;
  float a = (0.25 + 0.55*n1)*(0.6 + 0.4*n2);
  a *= smoothstep(0.0, 0.06, u)*(1.0 - smoothstep(0.86, 1.0, u));
  a *= 1.0 - 0.85*gauss((u - 0.64)*55.0);
  vec3 c = mix(mix(uC1, uC2, n1), uC3, n2*0.4);
  float sh = 1.0;
  if (uLit > 0.5) {
    vec3 L = normalize(uStarPos - vPosW);
    vec3 oc = uCenter - vPosW; float t = dot(oc, L);
    if (t > 0.0) sh = mix(0.28, 1.0, smoothstep(uRadius*0.92, uRadius*1.04, length(oc - L*t)));
  }
  vec3 col = c*(uStarColor*0.95*sh + vec3(0.03));
  gl_FragColor = vec4(col*a*uOpacity, a*uOpacity);
}`
