import {
  Component,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { Canvas } from '@react-three/fiber'
import { NeutralToneMapping, Vector3 } from 'three'
import { Label, Text } from '@/components/typography'
import { type GalaxyRecord } from '@/features/cosmography/api'
import {
  CoreGlow,
  GalaxyParticles,
} from '@/features/cosmography/visual/GalaxyScene3D'
import { ClockDriver } from '@/features/cosmography/visual/clock'
import { type GalaxyShape } from '@/features/cosmography/visual/galaxyForm'
import { type SonPublic } from '../api'
import { type CosmosIndex, isMisty, isUnderway } from '../model/cosmosModel'
import { STAR_LOOK } from '../model/looks'
import { type CosmosQuality } from '../useCosmosViewSettings'
import { CameraRig, type FocusRequest } from './CameraRig'
import { LabelOverlay, LabelUpdater } from './Labels3D'
import { Orbit3D } from './Orbit3D'
import { PostEffects3D } from './PostEffects3D'
import { Route3D } from './Route3D'
import { type SceneHandlers, ScenePointer } from './ScenePointer'
import { SkyBackdrop } from './SkyBackdrop'
import { SonAvatars3D } from './SonAvatars3D'
import { Star3D } from './Star3D'
import { StarCloud, type CloudStar } from './StarCloud'
import { Voyage3D } from './Voyage3D'
import { AsteroidBelt, World3D } from './World3D'
import { createGeometries, disposeGeometries } from './geometries'
import { QUALITY_PRESETS } from './quality'
import { tokenColor, tokenString } from './sceneColors'
import {
  type FrameState,
  type Hover,
  SceneContext,
  createFrameState,
} from './sceneContext'
import { FrameDriver } from './useCosmosFrame'
import { useCosmosLayout } from './useCosmosLayout'

const CAMERA_START: [number, number, number] = [0, 1600, 1400]
const GALAXY_POINTS = 52000
const GALAXY_LIGHT = 0.72
const GALAXY_CORE = 0.55
const GALAXY_ATTENUATE = 1.4
const GALAXY_DROP = -30
const GALAXY_FRAME = 1.04
const CAMERA_FOV = 40
const CAMERA_NEAR = 0.5
const CAMERA_FAR = 40000

type SceneProps = Omit<SceneHandlers, 'onHover'> & {
  index: CosmosIndex
  sons: SonPublic[]
  selectedWorldId: number | undefined
  selectedStarId: number | undefined
  highlightedRouteId: number | undefined
  quality: CosmosQuality
  reducedMotion: boolean
  focus: FocusRequest
  galaxy?: GalaxyRecord
  shape?: GalaxyShape
  onFailure: (reason: string) => void
}

class SceneBoundary extends Component<
  { onError: (reason: string) => void; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error) {
    this.props.onError(error.message || 'The 3D scene could not start')
  }

  render() {
    return this.state.failed ? null : this.props.children
  }
}

function useSceneVisible(element: HTMLElement | null): boolean {
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    if (!element) return
    let onScreen = true
    const update = () =>
      setVisible(
        onScreen &&
          document.visibilityState === 'visible' &&
          element.clientWidth > 0 &&
          element.clientHeight > 0
      )
    const observer = new IntersectionObserver((entries) => {
      onScreen = entries.some((entry) => entry.isIntersecting)
      update()
    })
    observer.observe(element)
    document.addEventListener('visibilitychange', update)
    return () => {
      observer.disconnect()
      document.removeEventListener('visibilitychange', update)
    }
  }, [element])
  return visible
}

export default function CosmosScene3D({
  index,
  sons,
  selectedWorldId,
  selectedStarId,
  highlightedRouteId,
  quality,
  reducedMotion,
  focus,
  galaxy,
  shape,
  onFailure,
  ...handlers
}: SceneProps) {
  const frameRef = useRef<FrameState>(createFrameState())
  const [labels] = useState(() => new Map<string, HTMLElement>())
  const [hover, setHover] = useState<Hover>(null)
  const [container, setContainer] = useState<HTMLDivElement | null>(null)
  const visible = useSceneVisible(container)
  const preset = QUALITY_PRESETS[quality]
  const { layout, routeBend } = useCosmosLayout(index.data)
  const detailStarId = useMemo(() => {
    if (selectedStarId !== undefined) return selectedStarId
    if (selectedWorldId === undefined) return undefined
    return layout.worlds.get(selectedWorldId)?.starId ?? undefined
  }, [layout, selectedStarId, selectedWorldId])
  const geometries = useMemo(() => createGeometries(preset), [preset])
  useEffect(() => () => disposeGeometries(geometries), [geometries])
  useEffect(() => {
    const frame = frameRef.current
    frame.reduced = reducedMotion
    frame.selectedWorld = selectedWorldId
    frame.selectedStar = selectedStarId
    frame.detailStar = detailStarId
    frame.highlightedRoute = highlightedRouteId
  }, [
    reducedMotion,
    selectedWorldId,
    selectedStarId,
    detailStarId,
    highlightedRouteId,
  ])
  const value = useMemo(
    () => ({ frameRef, layout, index, preset, routeBend, geometries, labels }),
    [layout, index, preset, routeBend, geometries, labels]
  )
  const starField = useMemo<CloudStar[]>(
    () =>
      index.data.stars.flatMap((star) => {
        const body = layout.stars.get(star.id)
        if (!body) return []
        if (detailStarId !== undefined && star.id !== detailStarId) return []
        const color = tokenColor(STAR_LOOK[star.star_type].token)
        return [
          {
            id: star.id,
            position: body.position,
            color: [color.r, color.g, color.b],
          },
        ]
      }),
    [index, layout, detailStarId]
  )
  const shownStars = useMemo(
    () => index.data.stars.filter((star) => star.id === detailStarId),
    [index, detailStarId]
  )
  const shownRoutes = useMemo(
    () =>
      index.data.routes.filter((route) => {
        if (detailStarId === undefined) return true
        return (
          layout.worlds.get(route.world_a_id)?.starId === detailStarId ||
          layout.worlds.get(route.world_b_id)?.starId === detailStarId
        )
      }),
    [index, layout, detailStarId]
  )
  const shownWorlds = useMemo(
    () =>
      index.worlds.filter((item) => {
        const body = layout.worlds.get(item.world.id)
        return (
          body !== undefined &&
          (body.starId === detailStarId || item.world.id === selectedWorldId)
        )
      }),
    [index, layout, detailStarId, selectedWorldId]
  )
  const starPositions = useMemo(
    () =>
      new Map(
        [...layout.stars.values()].map((star) => [
          star.id,
          new Vector3(...star.position),
        ])
      ),
    [layout]
  )
  const firstGod = useMemo(() => {
    const gods = new Map<number, (typeof index.data.foreign_gods)[number]>()
    for (const god of index.data.foreign_gods)
      if (god.contacted && god.status !== 'dead' && !gods.has(god.world_id))
        gods.set(god.world_id, god)
    return gods
  }, [index])
  const empty = index.data.stars.length === 0 && index.worlds.length === 0
  const failure = useRef(onFailure)
  useEffect(() => {
    failure.current = onFailure
  })
  const background = tokenString('--cosmos-void')
  return (
    <div
      ref={setContainer}
      className='relative h-full w-full overflow-hidden'
      style={{ background: 'var(--cosmos-void)', color: 'var(--cosmos-label)' }}
    >
      <SceneBoundary onError={(reason) => failure.current(reason)}>
        <ScenePointer
          frameRef={frameRef}
          index={index}
          foreignGodOf={(worldId) => firstGod.get(worldId)?.name}
          {...handlers}
          onHover={setHover}
        >
          <Canvas
            aria-label='Cosmos: stars, worlds and routes'
            tabIndex={0}
            dpr={[1, preset.pixelRatio]}
            gl={{
              antialias: false,
              powerPreference: 'high-performance',
              stencil: false,
            }}
            camera={{
              fov: CAMERA_FOV,
              near: CAMERA_NEAR,
              far: CAMERA_FAR,
              position: CAMERA_START,
            }}
            frameloop={!visible ? 'never' : reducedMotion ? 'demand' : 'always'}
            onCreated={({ gl }) => {
              if (!gl.capabilities.isWebGL2)
                failure.current('WebGL 2 is required')
              gl.toneMapping = NeutralToneMapping
              gl.toneMappingExposure = 1
              if (background) gl.setClearColor(background)
              gl.domElement.addEventListener('webglcontextlost', () =>
                failure.current('The WebGL context was lost')
              )
            }}
          >
            <SceneContext.Provider value={value}>
              <FrameDriver />
              <CameraRig
                focus={focus}
                empty={empty}
                galaxyReach={
                  galaxy && shape
                    ? ((galaxy.radius * shape.disc_reach_pct) / 100) *
                      GALAXY_FRAME
                    : undefined
                }
              />
              <SkyBackdrop />
              {galaxy && shape && (
                <group position={[0, GALAXY_DROP, 0]}>
                  <GalaxyParticles
                    galaxy={galaxy}
                    shape={shape}
                    count={Math.round(GALAXY_POINTS * preset.dust)}
                    attenuate={galaxy.radius * GALAXY_ATTENUATE}
                    light={GALAXY_LIGHT}
                  />
                  <CoreGlow galaxy={galaxy} shape={shape} scale={GALAXY_CORE} />
                  <ClockDriver />
                </group>
              )}
              <StarCloud stars={starField} />
              {index.data.stars.map((star) => {
                const body = layout.stars.get(star.id)
                if (!body) return null
                const hovered = hover?.kind === 'star' && hover.id === star.id
                if (star.id !== detailStarId && !hovered) return null
                return (
                  <Star3D
                    key={star.id}
                    star={star}
                    body={body}
                    hovered={hovered}
                  />
                )
              })}
              {index.worlds.map((item) => {
                const body = layout.worlds.get(item.world.id)
                if (!body) return null
                const selected = item.world.id === selectedWorldId
                if (!selected && body.starId !== detailStarId) return null
                const host = index.star(body.starId)
                const palette = index.palette(item.world.world_type)
                return (
                  <group key={item.world.id}>
                    <Orbit3D
                      body={body}
                      misty={isMisty(item)}
                      legend={item.world.discovery === 'legend'}
                      selected={selected}
                    />
                    {item.world.world_type === 'asteroid_belt' &&
                      body.kind === 'planet' && (
                        <AsteroidBelt
                          item={item}
                          body={body}
                          palette={palette}
                        />
                      )}
                    <World3D
                      item={item}
                      body={body}
                      palette={palette}
                      star={host}
                      starPosition={
                        body.starId !== null
                          ? starPositions.get(body.starId)
                          : undefined
                      }
                      god={firstGod.get(item.world.id)}
                      selected={selected}
                      hovered={
                        hover?.kind === 'world' && hover.id === item.world.id
                      }
                    />
                  </group>
                )
              })}
              {shownRoutes.map((route) => (
                <Route3D
                  key={route.id}
                  route={route}
                  hovered={hover?.kind === 'route' && hover.id === route.id}
                  highlighted={route.id === highlightedRouteId}
                />
              ))}
              {index.data.journeys.filter(isUnderway).map((journey) => {
                const route = index.route(journey.route_id)
                return route ? (
                  <Voyage3D
                    key={journey.id}
                    journey={journey}
                    route={route}
                    hovered={
                      hover?.kind === 'voyage' && hover.id === journey.id
                    }
                  />
                ) : null
              })}
              <LabelUpdater />
              {preset.bloom && <PostEffects3D samples={preset.samples} />}
            </SceneContext.Provider>
          </Canvas>
        </ScenePointer>
        <LabelOverlay
          index={index}
          shownWorlds={shownWorlds}
          shownStars={shownStars}
          labels={labels}
          selectedWorld={selectedWorldId}
        />
        <SonAvatars3D index={index} sons={sons} labels={labels} />
      </SceneBoundary>
      {empty && (
        <div className='pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center'>
          <Label variant='overline' className='text-inherit'>
            Cosmos
          </Label>
          <Text variant='prose' italic tone='inherit'>
            The void is still silent.
          </Text>
          <Text tone='inherit' className='opacity-70'>
            It will shine here when the first star ignites.
          </Text>
        </div>
      )}
      <div className='pointer-events-none absolute right-3 bottom-3 hidden max-w-sm md:block'>
        <Text variant='caption' tone='inherit' className='opacity-70'>
          Drag: rotate · right-drag: pan · wheel: zoom · double-click a world to
          descend to its map, a star to focus it
        </Text>
      </div>
    </div>
  )
}
