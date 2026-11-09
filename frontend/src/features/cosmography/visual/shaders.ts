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
  float ring = exp(-pow((d - 0.72)*7.0, 2.0)) * (0.6 + 0.6*n);
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
uniform vec3 uColor; uniform float uAlpha; uniform float uTime; uniform float uSeed; uniform float uRings;
varying vec2 vUv;
void main(){
  vec2 q = vUv*2.0-1.0; float d = length(q);
  if (d > 1.0) discard;
  float edge = smoothstep(1.0, 0.94, d) * smoothstep(0.86, 0.98, d);
  float grid = smoothstep(0.985, 1.0, abs(sin(d*uRings*3.14159))) * 0.35;
  float spokes = smoothstep(0.995, 1.0, abs(sin(atan(q.y, q.x)*6.0))) * 0.18 * (1.0 - d);
  float n = fbm(vec3(q*1.4, uSeed + uTime*0.015), 4);
  float body = (1.0 - d) * 0.22 * (0.6 + 0.6*n);
  vec3 c = uColor*(body + edge*1.2 + grid*(1.0 - d*0.5) + spokes);
  gl_FragColor = vec4(c*uAlpha, 1.0);
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
