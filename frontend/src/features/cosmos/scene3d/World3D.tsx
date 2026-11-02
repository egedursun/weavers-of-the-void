import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import {
  BackSide,
  Color,
  DoubleSide,
  type Group,
  InstancedMesh,
  MeshBasicMaterial,
  Object3D,
  Vector3,
} from 'three'
import {
  type CosmosWorld,
  type ForeignGodRecord,
  type StarRecord,
} from '../api'
import { isMisty } from '../model/cosmosModel'
import { seededRandom, signedHash, unitHash } from '../model/hash'
import { type WorldBody } from '../model/layout3d'
import {
  ATMOSPHERE_LOOK,
  GAS_ATMOSPHERE,
  SURFACE_CODE,
  WORLD_BODY,
} from '../model/looks'
import { ForeignGodSeal } from './ForeignGodSeal'
import { LEAK_VISIBLE_FROM, LeakEffect } from './LeakEffect'
import { billboardMaterial, shaderMaterial, uniform } from './materials'
import { paletteColors, tokenColor } from './sceneColors'
import { useScene } from './sceneContext'
import { FOG_FRAGMENT, INDICATOR_FRAGMENT } from './shaders/effects'
import {
  ATMOSPHERE_FRAGMENT,
  ATMOSPHERE_VERTEX,
  PLANET_FRAGMENT,
  PLANET_VERTEX,
  RING_FRAGMENT,
  RING_VERTEX,
} from './shaders/planet'
import { starLight } from './starLight'
import { useLatest } from './useLatest'

const CITY_LOG = 5
const CITY_SCALE = 0.9
const DIM_FORGOTTEN = 0.93
const DIM_UNKNOWN = 0.86
const LEGEND_OPACITY = 0.6
const MISTY_ATMOSPHERE = 0.25
const LEGEND_ATMOSPHERE = 0.6
const FOG_SCALE = 5.2
const LEGEND_RING = 3.1
const SELECT_RING = 3
const HOVER_RING = 2.8
const GAS_SELECT_RING = 5.9
const GAS_HOVER_RING = 5.6
const RING_TILT = 0.24
const RING_TILT_SPREAD = 0.125
const RING_YAW = 0.35
const BELT_ROCKS = 140
const BELT_SPREAD = 0.18
const HOVER_EASE = 8
const SEA_DEFAULT = 0.5
const SEA_SPREAD = 0.18
const center = new Vector3()
const TERRAIN_SEA: Partial<Record<string, number>> = {
  ocean: 0.82,
  sand: 0.12,
  ice: 0.4,
  lava: 0.45,
  dead: 0.3,
}

type World3DProps = {
  item: CosmosWorld
  body: WorldBody
  palette: string[]
  star: StarRecord | undefined
  starPosition: Vector3 | undefined
  god: ForeignGodRecord | undefined
  selected: boolean
  hovered: boolean
}

export function World3D({
  item,
  body,
  palette,
  star,
  starPosition,
  god,
  selected,
  hovered,
}: World3DProps) {
  const { geometries, frameRef } = useScene()
  const world = item.world
  const look = WORLD_BODY[world.world_type]
  const misty = isMisty(item)
  const legend = world.discovery === 'legend'
  const atmosphere = look.gas
    ? GAS_ATMOSPHERE
    : ATMOSPHERE_LOOK[world.atmosphere]
  const paletteKey = palette.join(',')
  const starType = star?.star_type
  const starBrightness = star?.brightness ?? 0
  const materials = useMemo(() => {
    const colors = paletteColors(paletteKey.split(','), '--cosmos-fog')
    const light = starLight(starType, starBrightness)
    const toxic = atmosphere?.toxic ?? false
    const atmosphereColor = toxic
      ? tokenColor('--cosmos-toxic')
      : (look.gas ? colors[3] : colors[1])
          .clone()
          .lerp(new Color(1, 1, 1), 0.35)
    const cloudColor = toxic
      ? tokenColor('--cosmos-toxic-cloud')
      : colors[9].clone().lerp(tokenColor('--cosmos-bone'), 0.5)
    const city =
      look.cities && !misty
        ? Math.min(Math.log10(item.counts.population + 1) / CITY_LOG, 1) *
          CITY_SCALE
        : 0
    const lit = starType ? 1 : 0
    const surface = shaderMaterial({
      vertex: PLANET_VERTEX,
      fragment: PLANET_FRAGMENT,
      uniforms: {
        uPal: uniform(colors),
        uStarPos: uniform(starPosition?.clone() ?? new Vector3()),
        uStarColor: uniform(light),
        uLit: uniform(lit),
        uSea: uniform(
          TERRAIN_SEA[world.world_type] ??
            SEA_DEFAULT + signedHash(`sea${world.id}`) * SEA_SPREAD
        ),
        uMount: uniform(0.5 + unitHash(`mt${world.id}`) * 0.6),
        uMoist: uniform(signedHash(`ms${world.id}`) * 0.15),
        uSeed: uniform(unitHash(`seed${world.id}`) * 10),
        uTime: uniform(0),
        uBreath: uniform(look.breath ? 1 : 0),
        uType: uniform(SURFACE_CODE[look.surface]),
        uClouds: uniform(look.cloudy && atmosphere ? atmosphere.clouds : 0),
        uCloudColor: uniform(cloudColor),
        uAtmColor: uniform(atmosphereColor),
        uAtm: uniform(atmosphere ? atmosphere.intensity * 0.35 : 0),
        uCity: uniform(city),
        uCityColor: uniform(tokenColor('--cosmos-city')),
        uDim: uniform(
          world.discovery === 'forgotten'
            ? DIM_FORGOTTEN
            : world.discovery === 'unknown'
              ? DIM_UNKNOWN
              : 0
        ),
        uOpacity: uniform(legend ? LEGEND_OPACITY : 1),
        uHover: uniform(0),
        uCopper: uniform(tokenColor('--cosmos-copper')),
        uViolet: uniform(tokenColor('--cosmos-violet')),
      },
      transparent: legend,
      depthWrite: !legend,
    })
    const shell = atmosphere
      ? shaderMaterial({
          vertex: ATMOSPHERE_VERTEX,
          fragment: ATMOSPHERE_FRAGMENT,
          uniforms: {
            uCenter: uniform(new Vector3()),
            uRadius: uniform(1),
            uShell: uniform(atmosphere.shell),
            uColor: uniform(atmosphereColor),
            uIntensity: uniform(
              atmosphere.intensity *
                (misty ? MISTY_ATMOSPHERE : legend ? LEGEND_ATMOSPHERE : 1)
            ),
            uStarPos: uniform(starPosition?.clone() ?? new Vector3()),
            uLit: uniform(lit),
          },
          blend: 'additive',
          side: BackSide,
        })
      : null
    const ring = look.ring
      ? shaderMaterial({
          vertex: RING_VERTEX,
          fragment: RING_FRAGMENT,
          uniforms: {
            uInner: uniform(1.32),
            uOuter: uniform(2.25),
            uSeed: uniform(unitHash(`ring${world.id}`) * 10),
            uC1: uniform(colors[2]),
            uC2: uniform(colors[6]),
            uC3: uniform(colors[4]),
            uCenter: uniform(new Vector3()),
            uRadius: uniform(1),
            uStarPos: uniform(starPosition?.clone() ?? new Vector3()),
            uStarColor: uniform(light),
            uLit: uniform(lit),
            uOpacity: uniform(misty ? 0.15 : legend ? 0.55 : 0.92),
          },
          blend: 'premultiplied',
          side: DoubleSide,
        })
      : null
    const fog = misty
      ? billboardMaterial(
          FOG_FRAGMENT,
          {
            uTime: uniform(0),
            uSeed: uniform(world.id * 0.73),
            uAlpha: uniform(world.discovery === 'forgotten' ? 0.75 : 0.6),
            uColor: uniform(tokenColor('--cosmos-fog')),
          },
          'premultiplied'
        )
      : null
    if (fog) fog.uniforms.uSize.value = FOG_SCALE
    const indicator = (mode: number, token: string, size: number) => {
      const material = billboardMaterial(INDICATOR_FRAGMENT, {
        uColor: uniform(tokenColor(token)),
        uTime: uniform(0),
        uAlpha: uniform(1),
        uMode: uniform(mode),
      })
      material.uniforms.uSize.value = size
      return material
    }
    return {
      surface,
      shell,
      ring,
      fog,
      legendRing: legend ? indicator(2, '--cosmos-violet', LEGEND_RING) : null,
      selectRing: indicator(
        0,
        '--cosmos-copper',
        look.gas ? GAS_SELECT_RING : SELECT_RING
      ),
      hoverRing: indicator(
        1,
        '--cosmos-bone',
        look.gas ? GAS_HOVER_RING : HOVER_RING
      ),
    }
  }, [
    paletteKey,
    starType,
    starBrightness,
    starPosition,
    atmosphere,
    look,
    misty,
    legend,
    item.counts.population,
    world.id,
    world.world_type,
    world.discovery,
  ])
  useEffect(
    () => () => {
      for (const material of Object.values(materials)) material?.dispose()
    },
    [materials]
  )
  const root = useRef<Group>(null)
  const spin = useRef<Group>(null)
  const hover = useRef(0)
  const materialsRef = useLatest(materials)
  useFrame((_, delta) => {
    const frame = frameRef.current
    const live = materialsRef.current
    const position = frame.worldPosition.get(world.id)
    const scale = frame.worldScale.get(world.id) ?? 1
    if (root.current && position) {
      root.current.position.copy(position)
      root.current.scale.setScalar(scale)
    }
    if (spin.current && !frame.reduced)
      spin.current.rotation.y += body.spinRate * Math.min(delta, 0.1)
    const target = hovered || selected ? 1 : 0
    hover.current +=
      (target - hover.current) * Math.min(1, Math.min(delta, 0.1) * HOVER_EASE)
    const time = frame.time
    live.surface.uniforms.uTime.value = time
    live.surface.uniforms.uHover.value = hover.current * 0.6
    if (starPosition) {
      live.surface.uniforms.uStarPos.value.copy(starPosition)
      if (live.shell) live.shell.uniforms.uStarPos.value.copy(starPosition)
      if (live.ring) live.ring.uniforms.uStarPos.value.copy(starPosition)
    }
    if (position) center.copy(position)
    if (live.shell) {
      live.shell.uniforms.uCenter.value.copy(center)
      live.shell.uniforms.uRadius.value = body.radius * scale
    }
    if (live.ring) {
      live.ring.uniforms.uCenter.value.copy(center)
      live.ring.uniforms.uRadius.value = body.radius * scale
    }
    if (live.fog) live.fog.uniforms.uTime.value = time
    for (const ring of [live.legendRing, live.selectRing])
      if (ring) ring.uniforms.uTime.value = time
    live.hoverRing.uniforms.uAlpha.value =
      hovered && !selected ? hover.current : 0
  })
  const radius = body.radius
  const geometry =
    look.surface === 'crystal'
      ? geometries.crystal
      : look.surface === 'ship'
        ? geometries.ship
        : geometries.sphere
  const ringRotation = useMemo(
    () =>
      [
        Math.PI / 2 +
          RING_TILT +
          signedHash(`rt${world.id}`) * RING_TILT_SPREAD,
        signedHash(`ry${world.id}`) * RING_YAW,
        0,
      ] as const,
    [world.id]
  )
  return (
    <group ref={root}>
      {look.surface !== 'belt' && (
        <group rotation={[0, 0, body.tilt]}>
          <group ref={spin}>
            <mesh
              geometry={geometry}
              material={materials.surface}
              scale={radius}
            />
          </group>
        </group>
      )}
      {look.surface === 'belt' && (
        <mesh
          geometry={geometries.rock}
          material={materials.surface}
          scale={radius * 0.6}
        />
      )}
      {materials.shell && atmosphere && (
        <mesh
          geometry={geometries.sphere}
          material={materials.shell}
          scale={radius * atmosphere.shell}
        />
      )}
      {materials.ring && (
        <mesh
          geometry={geometries.ring}
          material={materials.ring}
          scale={radius}
          rotation={ringRotation}
        />
      )}
      {world.leakage >= LEAK_VISIBLE_FROM && (
        <LeakEffect
          worldId={world.id}
          leakage={world.leakage}
          radius={radius}
        />
      )}
      {materials.fog && (
        <mesh
          geometry={geometries.plane}
          material={materials.fog}
          scale={radius}
          frustumCulled={false}
        />
      )}
      {materials.legendRing && (
        <mesh
          geometry={geometries.plane}
          material={materials.legendRing}
          scale={radius}
          frustumCulled={false}
        />
      )}
      {selected && (
        <mesh
          geometry={geometries.plane}
          material={materials.selectRing}
          scale={radius}
          frustumCulled={false}
        />
      )}
      <mesh
        geometry={geometries.plane}
        material={materials.hoverRing}
        scale={radius}
        frustumCulled={false}
      />
      {god && <ForeignGodSeal god={god} radius={radius} gas={look.gas} />}
    </group>
  )
}

type BeltProps = {
  item: CosmosWorld
  body: WorldBody
  palette: string[]
}

export function AsteroidBelt({ item, body, palette }: BeltProps) {
  const { geometries, frameRef } = useScene()
  const paletteKey = palette.join(',')
  const mesh = useMemo(() => {
    const colors = paletteColors(paletteKey.split(','), '--cosmos-fog')
    const material = new MeshBasicMaterial({ vertexColors: false })
    const rocks = new InstancedMesh(geometries.rock, material, BELT_ROCKS)
    const random = seededRandom(item.world.id * 104729 + 3)
    const holder = new Object3D()
    const tint = new Color()
    for (let index = 0; index < BELT_ROCKS; index += 1) {
      const angle = random() * Math.PI * 2
      const spread = 1 + (random() * 2 - 1) * BELT_SPREAD
      holder.position.set(
        Math.cos(angle) * body.orbitRadius * spread,
        (random() * 2 - 1) * body.orbitRadius * 0.02,
        Math.sin(angle) * body.orbitRadius * spread
      )
      holder.rotation.set(random() * 3, random() * 3, random() * 3)
      holder.scale.setScalar(body.radius * (0.15 + random() * 0.35))
      holder.updateMatrix()
      rocks.setMatrixAt(index, holder.matrix)
      tint.copy(colors[2 + Math.floor(random() * 6)]).multiplyScalar(0.55)
      rocks.setColorAt(index, tint)
    }
    rocks.instanceMatrix.needsUpdate = true
    return rocks
  }, [
    geometries.rock,
    paletteKey,
    item.world.id,
    body.orbitRadius,
    body.radius,
  ])
  useEffect(
    () => () => {
      ;(mesh.material as MeshBasicMaterial).dispose()
      mesh.dispose()
    },
    [mesh]
  )
  const group = useRef<Group>(null)
  useFrame(() => {
    const frame = frameRef.current
    if (group.current) group.current.rotation.y = frame.time * body.speed
  })
  return (
    <group
      position={body.anchor}
      rotation={[body.inclination, body.node, 0, 'YXZ']}
    >
      <group ref={group}>
        <primitive object={mesh} />
      </group>
    </group>
  )
}
