import {
  type PointerEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import { Hand, Repeat2 } from 'lucide-react'
import { ParticleField, tokenColor } from '@/lib/particles'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { Button } from '@/components/ui/button'
import { RarityIcon } from '@/components/domain'
import { LoreCard } from './LoreCard'
import { PackFace, CardReverse } from './PackArt'
import { type CharacterCard } from './api'
import { FRAME_ICON, frameOf, materialOf, tierLabel } from './cardModel'
import {
  PACK_RATIO,
  PRISM_TOKENS,
  type PackPhase,
  type Point,
  REVEAL_TOKEN,
  SPIN_TIME,
  STAGING,
  STRIP_ZONE,
  TEAR_AT,
  TEAR_FINISH,
  jagged,
  pathOf,
  polygonOf,
  serration,
} from './packModel'

const INSPECT_ART_WIDTH = 960
const PACK_MAX_WIDTH = 300
const STAGE_SHARE = 0.7
const STAGE_HEIGHTS = 2.75
const CARD_HEIGHT_SHARE = 0.7
const CARD_WIDTH_SHARE = 0.84
const CARD_CENTER = 0.44
const DRAG_START = 6
const DRAG_GAIN = 1.1

type Geometry = {
  width: number
  height: number
  tear: Point[]
  stripHeight: number
}

type Drag = { x: number; start: number; moved: boolean; strip: boolean }

function wait(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms))
}

function settle(animation: Animation) {
  return animation.finished.then(
    () => undefined,
    () => undefined
  )
}

function jolt(node: HTMLElement, strength: number, duration: number) {
  const frames: Keyframe[] = []
  for (let index = 0; index < 8; index += 1) {
    const fade = 1 - index / 8
    const x = (Math.random() - 0.5) * strength * 2 * fade
    const y = (Math.random() - 0.5) * strength * 2 * fade
    frames.push({
      transform: `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`,
    })
  }
  frames.push({ transform: 'none' })
  node.animate(frames, { duration, easing: 'linear' })
}

type PackOpeningProps = {
  card: CharacterCard
  onRevealed: () => void
  children?: ReactNode
}

export function PackOpening({ card, onRevealed, children }: PackOpeningProps) {
  const reduced = useReducedMotion()
  const material = materialOf(card)
  const staging = STAGING[material]
  const [phase, setPhaseState] = useState<PackPhase>('sealed')
  const [flipped, setFlipped] = useState(false)
  const [geometry, setGeometry] = useState<Geometry | null>(null)
  const phaseRef = useRef<PackPhase>('sealed')
  const progress = useRef(0)
  const measured = useRef(0)
  const drag = useRef<Drag | null>(null)
  const field = useRef<ParticleField | null>(null)
  const alive = useRef(true)
  const revealedOnce = useRef(false)
  const stage = useRef<HTMLDivElement>(null)
  const floatNode = useRef<HTMLDivElement>(null)
  const tiltNode = useRef<HTMLDivElement>(null)
  const pack = useRef<HTMLDivElement>(null)
  const bodyNode = useRef<HTMLDivElement>(null)
  const stripNode = useRef<HTMLDivElement>(null)
  const peelNode = useRef<HTMLDivElement>(null)
  const mover = useRef<HTMLDivElement>(null)
  const flipNode = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const tearGlow = useRef<SVGPathElement>(null)
  const tearEdge = useRef<SVGPathElement>(null)
  const tearEdgeLow = useRef<SVGPathElement>(null)
  const perforation = useRef<SVGPathElement>(null)
  const bob = useRef<Animation | null>(null)

  const D = useCallback(
    (ms: number) => (reduced ? Math.min(ms, 240) : ms),
    [reduced]
  )

  const setPhase = useCallback((next: PackPhase) => {
    phaseRef.current = next
    setPhaseState(next)
  }, [])

  const palette = useCallback(() => {
    if (material === 'mythic')
      return PRISM_TOKENS.map((name) => tokenColor(name))
    const accent = tokenColor(REVEAL_TOKEN[material])
    return [accent, accent, tokenColor('--gild-hi'), 'white']
  }, [material])

  useLayoutEffect(() => {
    const node = stage.current
    if (!node) return
    node.style.setProperty('--reveal', `var(${REVEAL_TOKEN[material]})`)
    const measure = () => {
      const box = node.getBoundingClientRect()
      const width = Math.min(
        PACK_MAX_WIDTH,
        box.width * STAGE_SHARE,
        box.height / STAGE_HEIGHTS
      )
      node.style.setProperty('--pack-w', `${width}px`)
      field.current?.resize()
      if (
        Math.abs(width - measured.current) < 0.5 ||
        phaseRef.current !== 'sealed'
      )
        return
      measured.current = width
      const height = width * PACK_RATIO
      const tear = jagged(width, height * TEAR_AT)
      const stripHeight = Math.max(...tear.map(([, y]) => y)) + 2
      setGeometry({ width, height, tear, stripHeight })
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [material])

  useEffect(() => {
    alive.current = true
    if (canvas.current) field.current = new ParticleField(canvas.current)
    return () => {
      alive.current = false
      field.current?.dispose()
      field.current = null
    }
  }, [])

  useEffect(() => {
    const node = floatNode.current
    if (!node || reduced) return
    bob.current = node.animate(
      [{ transform: 'translateY(-5px)' }, { transform: 'translateY(5px)' }],
      {
        duration: 2600,
        iterations: Infinity,
        direction: 'alternate',
        easing: 'ease-in-out',
      }
    )
    return () => bob.current?.cancel()
  }, [reduced])

  useEffect(() => {
    if (!geometry) return
    const strip = stripNode.current
    const body = bodyNode.current
    if (!strip || !body) return
    const { width, height, tear, stripHeight } = geometry
    const depth = height * 0.011
    const front = [
      ...serration(width, 0, depth, false),
      ...tear.slice().reverse(),
    ]
    const back = front.map(([x, y]): Point => [x, stripHeight - y])
    strip.style.setProperty('--strip-h', `${stripHeight}px`)
    strip
      .querySelectorAll<HTMLElement>('[data-face="front"]')
      .forEach((face) => face.style.setProperty('clip-path', polygonOf(front)))
    strip
      .querySelectorAll<HTMLElement>('[data-face="back"]')
      .forEach((face) => face.style.setProperty('clip-path', polygonOf(back)))
    body.style.setProperty(
      'clip-path',
      polygonOf([...tear, ...serration(width, height, depth, true).reverse()])
    )
    peelNode.current?.style.setProperty(
      'transform-origin',
      `${width}px ${tear[tear.length - 1][1]}px`
    )
    const line = pathOf(tear)
    tearGlow.current?.setAttribute('d', line)
    tearEdge.current?.setAttribute('d', line)
    tearEdgeLow.current?.setAttribute('d', pathOf(tear, 1.4))
    perforation.current?.setAttribute(
      'd',
      `M0 ${height * TEAR_AT}L${width} ${height * TEAR_AT}`
    )
    for (const path of [
      tearGlow.current,
      tearEdge.current,
      tearEdgeLow.current,
    ]) {
      if (!path) continue
      const length = path.getTotalLength()
      path.style.setProperty('stroke-dasharray', `${length}`)
      path.style.setProperty(
        'stroke-dashoffset',
        `${length * (1 - progress.current)}`
      )
    }
  }, [geometry])

  const pointOnTear = useCallback(
    (amount: number) => {
      const path = tearEdge.current
      const node = pack.current
      const host = stage.current
      if (!path || !node || !host || !geometry) return null
      const point = path.getPointAtLength(path.getTotalLength() * amount)
      const box = node.getBoundingClientRect()
      const frame = host.getBoundingClientRect()
      return {
        x: box.left - frame.left + (point.x / geometry.width) * box.width,
        y: box.top - frame.top + (point.y / geometry.height) * box.height,
      }
    },
    [geometry]
  )

  const setTear = useCallback(
    (next: number) => {
      const previous = progress.current
      const amount = Math.max(previous, Math.min(1, next))
      progress.current = amount
      for (const path of [
        tearGlow.current,
        tearEdge.current,
        tearEdgeLow.current,
      ])
        path?.style.setProperty(
          'stroke-dashoffset',
          `${path.getTotalLength() * (1 - amount)}`
        )
      tearGlow.current?.style.setProperty(
        'opacity',
        String(Math.min(1, amount * 3))
      )
      perforation.current?.style.setProperty(
        'opacity',
        String(Math.max(0, 0.55 - amount * 3))
      )
      peelNode.current?.style.setProperty(
        'transform',
        `rotate(${-amount * 3.4}deg) translateY(${-amount * 2.5}px)`
      )
      const delta = amount - previous
      if (delta <= 0 || reduced) return
      const point = pointOnTear(amount)
      if (point)
        field.current?.emit(point.x, point.y, {
          count: Math.ceil(delta * 90),
          colors: ['white', tokenColor('--gild-hi')],
          kinds: ['spark', 'spark', 'flake'],
          angle: -Math.PI / 2,
          spread: 1.3,
          speed: [1, 4.2],
          size: [1.2, 2.6],
          life: [18, 40],
          gravity: 0.16,
        })
      const shake = Math.min(2.4, delta * 60)
      pack.current?.animate(
        [
          {
            transform: `translate(${(Math.random() - 0.5) * shake}px, ${(Math.random() - 0.5) * shake}px)`,
          },
          { transform: 'none' },
        ],
        { duration: 90, composite: 'add' }
      )
    },
    [pointOnTear, reduced]
  )

  const popStrip = useCallback(() => {
    const strip = stripNode.current
    if (!strip || !geometry) return
    if (reduced) {
      strip.animate([{ opacity: 1 }, { opacity: 0 }], {
        duration: 200,
        fill: 'forwards',
      })
      return
    }
    const { width, height } = geometry
    const motion = { x: 0, y: -3, rz: -3.4, rx: 0, opacity: 1, frame: 0 }
    const speed = { x: width * 0.011, y: -height * 0.021, rz: 2.6, rx: 11 }
    const gravity = height * 0.00155
    const step = () => {
      if (!alive.current) return
      motion.frame += 1
      speed.y += gravity
      motion.x += speed.x
      motion.y += speed.y
      motion.rz += speed.rz
      motion.rx += speed.rx
      speed.rz *= 0.985
      if (motion.frame > 34) motion.opacity = Math.max(0, motion.opacity - 0.05)
      strip.style.setProperty(
        'transform',
        `translate(${motion.x}px, ${motion.y}px) rotateZ(${motion.rz}deg) rotateX(${motion.rx}deg)`
      )
      strip.style.setProperty('opacity', String(motion.opacity))
      if (motion.opacity > 0 && motion.y < height) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [geometry, reduced])

  const reveal = useCallback(async () => {
    const host = stage.current
    const card = mover.current
    const flip = flipNode.current
    if (!host || !card || !flip || !geometry || phaseRef.current === 'opening')
      return
    setPhase('opening')
    bob.current?.pause()
    if (floatNode.current)
      floatNode.current.animate(
        [
          { transform: getComputedStyle(floatNode.current).transform },
          { transform: 'none' },
        ],
        { duration: 300, fill: 'forwards', easing: 'ease-out' }
      )
    tiltNode.current?.style.setProperty('--tilt-x', '0deg')
    tiltNode.current?.style.setProperty('--tilt-y', '0deg')
    const colors = palette()
    const opening = pointOnTear(0.5)
    popStrip()
    host.animate([{ '--shaft': 0 } as Keyframe, { '--shaft': 1 } as Keyframe], {
      duration: D(380),
      fill: 'forwards',
      easing: 'ease-out',
    })
    if (opening && !reduced)
      for (let index = 0; index < 6; index += 1)
        field.current?.emit(
          opening.x + (Math.random() - 0.5) * geometry.width * 0.8,
          opening.y,
          {
            count: 5,
            colors: ['white', tokenColor('--gild-hi'), tokenColor('--gild')],
            kinds: ['flake', 'spark'],
            angle: -Math.PI / 2,
            spread: 0.55,
            speed: [2.5, 6.5],
            size: [1.4, 3],
            life: [50, 90],
            gravity: 0.09,
          }
        )
    await wait(D(240))
    if (!alive.current) return
    const cardBox = card.getBoundingClientRect()
    const frame = host.getBoundingClientRect()
    const rise = cardBox.height * 0.6
    const scale = Math.min(
      (frame.height * CARD_HEIGHT_SHARE) / cardBox.height,
      (frame.width * CARD_WIDTH_SHARE) / cardBox.width
    )
    const dx = frame.left + frame.width / 2 - (cardBox.left + cardBox.width / 2)
    const dy =
      frame.top +
      frame.height * CARD_CENTER -
      (cardBox.top + cardBox.height / 2)
    const raised = `translate(0, ${-rise}px) scale(1)`
    const resting = `translate(${dx}px, ${dy}px) scale(${scale})`
    const rising = card.animate(
      [{ transform: 'translate(0, 0) scale(1)' }, { transform: raised }],
      {
        duration: D(1000),
        easing: 'cubic-bezier(.22,.72,.18,1)',
        fill: 'forwards',
      }
    )
    await wait(D(420))
    if (!alive.current) return
    bodyNode.current?.parentElement?.animate(
      [
        { transform: 'none', opacity: 1, filter: 'blur(0px)' },
        {
          transform: `translateY(${geometry.height * 0.32}px) rotateX(-14deg) scale(.96)`,
          opacity: 0,
          filter: 'blur(3px)',
        },
      ],
      {
        duration: D(760),
        easing: 'cubic-bezier(.55,0,.75,.2)',
        fill: 'forwards',
      }
    )
    host.animate(
      [
        { '--shaft': 1, '--dim': 0 } as Keyframe,
        { '--shaft': 0, '--dim': 1 } as Keyframe,
      ],
      { duration: D(900), fill: 'forwards', easing: 'ease-in-out' }
    )
    await settle(rising)
    if (!alive.current) return
    await settle(
      card.animate([{ transform: raised }, { transform: resting }], {
        duration: D(900),
        easing: 'cubic-bezier(.3,.9,.25,1)',
        fill: 'forwards',
      })
    )
    if (!alive.current) return
    const center = { x: frame.width / 2, y: frame.height * CARD_CENTER }
    if (!reduced && staging.pulses > 0) {
      host.style.setProperty('--charge', '1')
      if (staging.gather)
        field.current?.gather(center.x, center.y, {
          count: staging.gather,
          colors,
          distance: Math.max(frame.width, frame.height) * 0.5,
        })
      host.animate(
        [{ '--halo': 0 } as Keyframe, { '--halo': 0.45 } as Keyframe],
        {
          duration: D(420 * staging.pulses),
          fill: 'forwards',
        }
      )
      for (let beat = 0; beat < staging.pulses; beat += 1) {
        const lift = 1.035 + beat * 0.012
        await settle(
          card.animate(
            [
              { transform: resting },
              { transform: `${resting} scale(${lift})`, offset: 0.35 },
              { transform: resting },
            ],
            { duration: D(440 - beat * 60), easing: 'cubic-bezier(.3,0,.3,1)' }
          )
        )
        if (!alive.current) return
        if (staging.shake) jolt(host, staging.shake * 0.35 * (beat + 1), D(160))
      }
    }
    const spinTime = D(SPIN_TIME[staging.spin] ?? 900)
    const spinning = flip.animate(
      [
        { transform: 'rotateY(0deg)' },
        { transform: `rotateY(${staging.spin}deg)` },
      ],
      {
        duration: spinTime,
        easing:
          staging.spin > 180
            ? 'cubic-bezier(.12,.62,.12,1)'
            : 'cubic-bezier(.45,0,.2,1)',
        fill: 'forwards',
      }
    )
    card.animate(
      [
        { transform: resting },
        { transform: `${resting} scale(1.06)`, offset: 0.5 },
        { transform: resting },
      ],
      { duration: spinTime, easing: 'ease-in-out' }
    )
    await wait(spinTime * (staging.spin > 180 ? 0.58 : 0.5))
    if (!alive.current) return
    host.style.setProperty('--charge', '0')
    host.animate(
      [
        { '--flash': 0 } as Keyframe,
        { '--flash': 1, offset: 0.18 } as Keyframe,
        { '--flash': 0 } as Keyframe,
      ],
      { duration: D(700), easing: 'ease-out' }
    )
    host.animate([{ '--ring': 0 } as Keyframe, { '--ring': 1 } as Keyframe], {
      duration: D(1000),
      easing: 'cubic-bezier(.1,.7,.3,1)',
      fill: 'forwards',
    })
    host.animate(
      [
        { '--rays': 0, '--halo': 0.45 } as Keyframe,
        { '--rays': staging.rays, '--halo': 1 } as Keyframe,
      ],
      { duration: D(900), easing: 'ease-out', fill: 'forwards' }
    )
    if (staging.shake && !reduced) jolt(host, staging.shake, D(420))
    if (!reduced) {
      field.current?.emit(center.x, center.y, {
        count: staging.burst,
        colors,
        kinds: ['star', 'spark', 'spark', 'mote'],
        speed: [2, 10 + staging.pulses * 2.4],
        size: [1.2, 3.6],
        life: [45, 110],
        gravity: 0.05,
        drag: 0.955,
        radius: 30,
      })
      field.current?.emit(center.x, center.y, {
        count: Math.round(staging.burst * 0.3),
        colors: [tokenColor('--gild-hi'), tokenColor('--gild')],
        kinds: ['flake'],
        speed: [3, 9],
        size: [1.6, 3.4],
        life: [70, 130],
        gravity: 0.12,
        drag: 0.97,
      })
    }
    setPhase('revealed')
    if (!revealedOnce.current) {
      revealedOnce.current = true
      onRevealed()
    }
    await settle(spinning)
    if (!alive.current || reduced) return
    card.animate(
      [
        { transform: `${resting} translateY(-0.6%) rotate(-0.5deg)` },
        { transform: `${resting} translateY(0.6%) rotate(0.5deg)` },
      ],
      {
        duration: 3200,
        iterations: Infinity,
        direction: 'alternate',
        easing: 'ease-in-out',
      }
    )
  }, [
    D,
    geometry,
    onRevealed,
    palette,
    pointOnTear,
    popStrip,
    reduced,
    setPhase,
    staging,
  ])

  const finishTear = useCallback(() => {
    if (phaseRef.current === 'opening' || phaseRef.current === 'revealed')
      return
    setPhase('tearing')
    const start = progress.current
    const duration = D(Math.max(160, (1 - start) * 620))
    const began = performance.now()
    const step = (now: number) => {
      if (!alive.current) return
      const t = Math.min(1, (now - began) / duration)
      const eased = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2
      setTear(start + (1 - start) * eased)
      if (t < 1) requestAnimationFrame(step)
      else void reveal()
    }
    requestAnimationFrame(step)
  }, [D, reveal, setPhase, setTear])

  const sealed = phase === 'sealed' || phase === 'tearing'

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (!sealed || event.button !== 0) return
    const box = event.currentTarget.getBoundingClientRect()
    drag.current = {
      x: event.clientX,
      start: progress.current,
      moved: false,
      strip: (event.clientY - box.top) / box.height < STRIP_ZONE,
    }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const current = drag.current
    if (!current || !geometry) return
    const travel = event.clientX - current.x
    if (Math.abs(travel) > DRAG_START) current.moved = true
    if (!current.strip || travel <= 0) return
    if (phaseRef.current === 'sealed') setPhase('tearing')
    setTear(current.start + (travel / geometry.width) * DRAG_GAIN)
    if (progress.current < 1) return
    drag.current = null
    void reveal()
  }

  const onPointerUp = () => {
    const current = drag.current
    drag.current = null
    if (!current) return
    if (!current.moved || progress.current >= TEAR_FINISH) finishTear()
  }

  const onStageMove = (event: PointerEvent<HTMLDivElement>) => {
    const node = tiltNode.current
    if (!node || !sealed || reduced || event.pointerType === 'touch') return
    const box = node.getBoundingClientRect()
    const x = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width))
    const y = Math.min(1, Math.max(0, (event.clientY - box.top) / box.height))
    node.setAttribute('data-tilting', '')
    node.style.setProperty('--tilt-x', `${(x - 0.5) * 16}deg`)
    node.style.setProperty('--tilt-y', `${(0.5 - y) * 12}deg`)
    node.style.setProperty('--holo-x', `${x * 100}%`)
    node.style.setProperty('--holo-y', `${y * 100}%`)
  }

  const onStageLeave = () => {
    const node = tiltNode.current
    if (!node) return
    node.removeAttribute('data-tilting')
    node.style.setProperty('--tilt-x', '0deg')
    node.style.setProperty('--tilt-y', '0deg')
  }

  const Icon = FRAME_ICON[frameOf(card)]

  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div
        ref={stage}
        className='pack-stage'
        data-phase={phase}
        data-material={material}
        onPointerMove={onStageMove}
        onPointerLeave={onStageLeave}
      >
        <span className='pack-backdrop' />
        <span className='pack-rays' />
        <span className='pack-halo' />
        <span className='pack-floor' />
        <div ref={floatNode} className='pack-float'>
          <div ref={tiltNode} className='pack-tilt'>
            <div
              ref={pack}
              className='pack'
              role='button'
              tabIndex={sealed ? 0 : -1}
              aria-label='Sealed card pack. Swipe across the top seal to tear it open, or press to open it.'
              aria-disabled={!sealed || undefined}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerUp}
              onKeyDown={(event) => {
                if (event.key !== 'Enter' && event.key !== ' ') return
                event.preventDefault()
                finishTear()
              }}
            >
              <span className='pack-mouth' />
              <div ref={mover} className='pack-card'>
                <div ref={flipNode} className='pack-card-flip'>
                  <div className='pack-card-side' data-side='reverse'>
                    <CardReverse />
                  </div>
                  <div
                    className='pack-card-side'
                    data-side='front'
                    aria-hidden={phase !== 'revealed' || undefined}
                  >
                    <LoreCard
                      card={card}
                      flipped={flipped}
                      tilt={phase === 'revealed'}
                      artWidth={INSPECT_ART_WIDTH}
                    />
                  </div>
                </div>
              </div>
              <div className='pack-body-shadow'>
                <div ref={bodyNode} className='pack-body'>
                  <PackFace />
                </div>
              </div>
              <span className='pack-shaft' />
              <div ref={stripNode} className='pack-strip'>
                <div ref={peelNode} className='pack-strip-peel'>
                  <div className='pack-strip-face' data-face='front'>
                    <PackFace />
                  </div>
                  <div className='pack-strip-face' data-face='back' />
                </div>
              </div>
              <svg
                className='pack-tear'
                viewBox={
                  geometry
                    ? `0 0 ${geometry.width} ${geometry.height}`
                    : '0 0 1 1'
                }
                aria-hidden='true'
              >
                <path ref={perforation} className='pack-tear-perforation' />
                <path ref={tearGlow} className='pack-tear-glow' />
                <path ref={tearEdgeLow} className='pack-tear-edge' />
                <path ref={tearEdge} className='pack-tear-edge' />
              </svg>
              <span className='pack-guide' aria-hidden='true'>
                <span className='pack-guide-spark' />
              </span>
            </div>
          </div>
        </div>
        <span className='pack-ring' />
        <span className='pack-flash' />
        <canvas ref={canvas} className='pack-fx' aria-hidden='true' />
        <div className='pack-hint' aria-hidden={!sealed || undefined}>
          <Hand aria-hidden='true' />
          <span>Swipe across the seal to tear it open, or tap the pack</span>
        </div>
        <div className='pack-banner' aria-live='polite'>
          {phase === 'revealed' && (
            <>
              <span className='pack-banner-medallion'>
                {card.rarity ? (
                  <RarityIcon rarity={card.rarity} />
                ) : (
                  <Icon aria-hidden='true' />
                )}
              </span>
              <span className='pack-banner-text'>
                <span className='pack-banner-tier'>{tierLabel(card)}</span>
                <span className='pack-banner-name'>
                  {`${card.name} joins your binder`}
                </span>
              </span>
            </>
          )}
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-center gap-2'>
        {sealed ? (
          <Button onClick={finishTear}>
            <Hand />
            Open the pack
          </Button>
        ) : (
          <Button
            variant='outline'
            onClick={() => setFlipped((value) => !value)}
            disabled={phase !== 'revealed'}
            disabledReason='The pack is still opening.'
          >
            <Repeat2 />
            {flipped ? 'Show the front' : 'Turn over'}
          </Button>
        )}
        {children}
      </div>
    </div>
  )
}
