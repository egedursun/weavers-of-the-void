import { NOISE } from './noise'

export const SKY_VERTEX = `
varying vec3 vDir;
void main(){ vDir = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`

export const SKY_FRAGMENT = `
${NOISE}
uniform vec3 uBg; uniform vec3 uCopper; uniform vec3 uViolet; uniform vec3 uTeal; uniform vec3 uBone;
varying vec3 vDir;
void main(){
  vec3 d = normalize(vDir);
  float w = fbm(d*1.4 + 3.0, 3);
  float n1 = fbm(d*2.1 + w*0.8 + 11.0, 5);
  float n2 = fbm(d*3.3 - w*0.6 + 27.0, 5);
  float n3 = fbm(d*6.0 + 5.0, 4);
  float bandY = d.y*0.92 + d.x*0.18 + w*0.12;
  float band = exp(-bandY*bandY*9.0);
  vec3 c = uBg;
  c += uCopper * smoothstep(0.10, 0.85, n1) * 0.016 * (0.35 + band);
  c += uViolet * smoothstep(0.15, 0.90, n2) * 0.014;
  c += uTeal * smoothstep(0.40, 0.95, n2*n1*2.0+0.2) * 0.006;
  c += uBone * band * 0.009 * (0.6 + 0.4*n3);
  c *= 1.0 - 0.55*smoothstep(0.15, 0.65, n3) * band;
  gl_FragColor = vec4(c, 1.0);
}`

export const DUST_VERTEX = `
attribute float aSize; attribute vec3 aColor; attribute float aSeed;
uniform float uTime; uniform float uRatio; uniform float uAttenuate;
varying vec3 vColor;
void main(){
  vec4 mv = modelViewMatrix*vec4(position,1.0);
  gl_Position = projectionMatrix*mv;
  float twinkle = 0.72 + 0.28*sin(uTime*(0.4+aSeed*1.9) + aSeed*61.0);
  float s = aSize*uRatio;
  if (uAttenuate > 0.0) s *= clamp(uAttenuate / -mv.z, 0.35, 2.2);
  gl_PointSize = max(s, 1.0);
  vColor = aColor*twinkle;
}`

export const DUST_FRAGMENT = `
varying vec3 vColor;
void main(){
  vec2 q = gl_PointCoord*2.0-1.0; float d = dot(q,q);
  if (d > 1.0) discard;
  float a = exp(-d*3.5) + exp(-d*24.0)*0.8;
  gl_FragColor = vec4(vColor*a, 1.0);
}`

export const NEBULA_FRAGMENT = `
${NOISE}
uniform vec3 uColor; uniform float uIntensity; uniform float uSeed; uniform float uTime;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float n = fbm(vec3(q*1.6, uSeed + uTime*0.004), 5);
  float m = (1.0 - smoothstep(0.1, 1.0, d)) * smoothstep(-0.25, 0.55, n + (0.4 - d*0.5));
  gl_FragColor = vec4(uColor*m*uIntensity, 1.0);
}`
