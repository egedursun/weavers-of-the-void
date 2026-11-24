import {
  type KeyboardEvent,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { Crosshair, Heart, Maximize, Minus, Plus, Star } from 'lucide-react'
import { cn, getDisplayNameInitials } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { INK_FILLS } from '@/features/collective/inks'
import { UNION_FORMS, UNION_PURPOSES } from '@/features/cycles/unionLabels'
import { mediaUrl } from '@/features/images/media'
import { clip } from '@/features/languages/treeLayout'
import { ROLE_ICONS } from '../../mind/labels'
import { type ArmsInk, type FamilyTree } from '../api'
import { KIN_KINDS, MARRIAGE_ENDS } from '../labels'
import {
  type FamilyLayout,
  type PartnerMark,
  type PlacedCard,
} from './familyLayout'
import { kinCircle } from './kinship'
import { CARE_LOOK, ENDED_DASH, PARTNER_LOOK, generationWord } from './looks'

const PORTRAIT_RADIUS = 27
const PORTRAIT_INSET = 14
const TEXT_LEFT = PORTRAIT_INSET * 2 + PORTRAIT_RADIUS * 2 - 4
const NAME_LIMIT = 16
const KIN_LIMIT = 30
const COMPACT_LIMIT = 9
const COMPACT_SCALE = 1.7
const ROLE_SIZE = 16
const KNOT_RADIUS = 12
const KNOT_ICON = 14
const STAR_RADIUS = 13
const COVER_WIDTH = 160
const START_ZOOM = 0.78
const MAX_ZOOM = 1.8
const FIT_MARGIN = 1.04
const ZOOM_STEP = 1.25
const DRAG_SLOP = 4
const PAN_STEP = 80
const DIM = 0.28
const HOVER_DIM = 0.55
const CARE_REST = 0.4
const DEAD = 0.82
const ROW_LABEL_X = 18
const MINI_STROKE = 4

type Camera = { cx: number; cy: number; scale: number }
type Size = { width: number; height: number }

function activate(event: KeyboardEvent, run: () => void) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    run()
  }
}

function lifeWord(card: PlacedCard): string {
  const person = card.person
  if (person.living) return `Born epoch ${person.birth_epoch} · living`
  return person.end_epoch === null
    ? `Born epoch ${person.birth_epoch} · dead`
    : `Epoch ${person.birth_epoch}–${person.end_epoch}`
}

function knotTitle(mark: PartnerMark, names: Map<number, string>): string {
  const pair = `${names.get(mark.first) ?? ''} and ${names.get(mark.second) ?? ''}`
  if (mark.union) {
    const union = mark.union
    const ended =
      union.end_epoch === null
        ? ''
        : ` · ended in epoch ${union.end_epoch}${union.cause_end ? ` by ${MARRIAGE_ENDS[union.cause_end].label.toLowerCase()}` : ''}`
    return `${pair} · wed in epoch ${union.start_epoch}${union.forced ? ', by force' : ''} · ${UNION_FORMS[union.form].label.toLowerCase()} · ${UNION_PURPOSES[union.purpose].label.toLowerCase()}${ended}`
  }
  return `${pair} · ${PARTNER_LOOK[mark.kind].label.toLowerCase()} since epoch ${mark.tie?.epoch ?? 0}`
}

function knotIcon(mark: PartnerMark) {
  if (mark.union?.cause_end && !mark.widowed)
    return MARRIAGE_ENDS[mark.union.cause_end].icon
  if (mark.kind === 'concubine_of') return KIN_KINDS.concubine_of.icon
  if (mark.kind === 'betrothed_to') return KIN_KINDS.betrothed_to.icon
  return Heart
}

function TreeCard({
  card,
  box,
  kin,
  ink,
  root,
  selected,
  dimmed,
  compact,
  onSelect,
  onFocus,
}: {
  card: PlacedCard
  box: { width: number; height: number }
  kin: string
  ink: ArmsInk | null
  root: boolean
  selected: boolean
  dimmed: number | null
  compact: boolean
  onSelect: (id: number) => void
  onFocus: (id: number) => void
}) {
  const person = card.person
  const middle = box.height / 2
  const cx = PORTRAIT_INSET + PORTRAIT_RADIUS
  const clipId = `family-portrait-${person.id}`
  const role = person.role ? ROLE_ICONS[person.role] : undefined
  const RoleIcon = role?.icon
  return (
    <g
      transform={`translate(${card.x} ${card.y})`}
      role='button'
      tabIndex={0}
      aria-pressed={selected}
      aria-label={`${person.name}, ${kin}`}
      data-person={person.id}
      opacity={dimmed ?? (person.living ? 1 : DEAD)}
      className='group cursor-pointer transition-opacity duration-300 outline-none'
      onClick={() => onSelect(person.id)}
      onFocus={() => onFocus(person.id)}
      onKeyDown={(event) => activate(event, () => onSelect(person.id))}
    >
      <title>{`${person.name}${person.title ? `, ${person.title}` : ''} · ${kin}`}</title>
      <rect
        width={box.width}
        height={box.height}
        rx={16}
        strokeWidth={root || selected ? 2.5 : 1.25}
        strokeDasharray={person.blood ? undefined : '6 4'}
        className={cn(
          person.living ? 'fill-card' : 'fill-muted',
          selected
            ? 'stroke-primary'
            : root
              ? 'stroke-gild dark:stroke-gild-hi'
              : 'stroke-gild/55 hover:stroke-gild'
        )}
      />
      <rect
        x={-4}
        y={-4}
        width={box.width + 8}
        height={box.height + 8}
        rx={20}
        fill='none'
        strokeWidth={2.5}
        className='stroke-ring opacity-0 group-focus-visible:opacity-100'
      />
      {ink && (
        <rect
          x={0}
          y={14}
          width={6}
          height={box.height - 28}
          rx={3}
          className={INK_FILLS[ink]}
        />
      )}
      <clipPath id={clipId}>
        <circle cx={cx} cy={middle} r={PORTRAIT_RADIUS} />
      </clipPath>
      {person.cover ? (
        <image
          href={mediaUrl(person.cover, COVER_WIDTH)}
          x={cx - PORTRAIT_RADIUS}
          y={middle - PORTRAIT_RADIUS}
          width={PORTRAIT_RADIUS * 2}
          height={PORTRAIT_RADIUS * 2}
          preserveAspectRatio='xMidYMid slice'
          clipPath={`url(#${clipId})`}
          className={person.living ? undefined : 'grayscale'}
        />
      ) : (
        <>
          <circle
            cx={cx}
            cy={middle}
            r={PORTRAIT_RADIUS}
            className='fill-secondary'
          />
          <text
            x={cx}
            y={middle + 6}
            textAnchor='middle'
            fontSize={17}
            className='fill-primary font-display'
          >
            {getDisplayNameInitials(person.name)}
          </text>
        </>
      )}
      <circle
        cx={cx}
        cy={middle}
        r={PORTRAIT_RADIUS}
        fill='none'
        strokeWidth={root ? 2.5 : 1.5}
        className={root ? 'stroke-gild dark:stroke-gild-hi' : 'stroke-gild/70'}
      />
      {compact ? (
        <text
          x={TEXT_LEFT}
          y={middle + 9}
          fontSize={24}
          fontWeight={600}
          className='fill-foreground font-display'
        >
          {`${person.living ? '' : '† '}${clip(person.name, COMPACT_LIMIT)}`}
        </text>
      ) : (
        <>
          <text
            x={TEXT_LEFT}
            y={30}
            fontSize={15}
            fontWeight={600}
            className='fill-foreground font-display'
          >
            {`${person.living ? '' : '† '}${clip(person.name, NAME_LIMIT)}`}
          </text>
          <text
            x={TEXT_LEFT}
            y={50}
            fontSize={11}
            fontWeight={600}
            className='fill-primary'
          >
            {clip(kin, KIN_LIMIT)}
          </text>
          <text
            x={TEXT_LEFT}
            y={68}
            fontSize={11}
            className='fill-muted-foreground'
          >
            {lifeWord(card)}
          </text>
          {RoleIcon && (
            <RoleIcon
              x={box.width - ROLE_SIZE - 12}
              y={10}
              width={ROLE_SIZE}
              height={ROLE_SIZE}
              className='text-gild'
              aria-label={role.label}
            />
          )}
        </>
      )}
      {root && (
        <g transform={`translate(${box.width / 2} 0)`}>
          <circle
            r={STAR_RADIUS}
            className='fill-card stroke-gild'
            strokeWidth={2}
          />
          <Star
            x={-8}
            y={-8}
            width={16}
            height={16}
            className='fill-gild text-gild'
            aria-hidden='true'
          />
        </g>
      )}
    </g>
  )
}

function fitCamera(layout: FamilyLayout, size: Size): Camera {
  const scale =
    Math.max(layout.width / size.width, layout.height / size.height) *
    FIT_MARGIN
  return { cx: layout.width / 2, cy: layout.height / 2, scale }
}

export function FamilyTreeCanvas({
  tree,
  layout,
  inks,
  selected,
  centred,
  onSelect,
  wheel = 'held',
  className,
}: {
  tree: FamilyTree
  layout: FamilyLayout
  inks: Map<number, ArmsInk | null>
  selected: number | null
  centred: { id: number; turn: number } | null
  onSelect: (id: number) => void
  wheel?: 'free' | 'held'
  className?: string
}) {
  const frame = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const [size, setSize] = useState<Size | null>(null)
  const [stored, setStored] = useState<Camera | null>(null)
  const [turn, setTurn] = useState(0)
  const [drawn, setDrawn] = useState(layout)
  if (drawn !== layout) {
    setDrawn(layout)
    setStored(null)
  }
  const [hovered, setHovered] = useState<number | null>(null)
  const drag = useRef<{
    x: number
    y: number
    camera: Camera
    moved: boolean
  } | null>(null)
  const dragged = useRef(false)
  const names = useMemo(
    () => new Map(tree.people.map((person) => [person.id, person.name])),
    [tree]
  )
  const focus = hovered ?? selected
  const line = useMemo(
    () => (focus === null ? null : kinCircle(tree, focus)),
    [tree, focus]
  )
  useLayoutEffect(() => {
    const element = frame.current
    if (!element) return
    const measure = () => {
      const rect = element.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0)
        setSize({ width: rect.width, height: rect.height })
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  const fit = size ? fitCamera(layout, size) : null
  const focusOn = (id: number, scale: number): Camera | null => {
    const card = layout.cards.get(id)
    return card
      ? {
          cx: card.x + layout.card.width / 2,
          cy: card.y + layout.card.height / 2,
          scale,
        }
      : null
  }
  const camera = stored ?? (size ? focusOn(tree.root, 1 / START_ZOOM) : null)
  const setCamera = (next: Camera | null | ((current: Camera) => Camera)) =>
    setStored((current) => {
      if (typeof next !== 'function') return next ?? current
      const base = current ?? camera
      return base ? next(base) : current
    })
  if (centred && centred.turn !== turn) {
    setTurn(centred.turn)
    setStored(focusOn(centred.id, camera?.scale ?? 1 / START_ZOOM))
  }
  const centreOn = (id: number, scale: number) => setCamera(focusOn(id, scale))
  const clampScale = (scale: number) =>
    Math.min(Math.max(scale, 1 / MAX_ZOOM), (fit?.scale ?? scale) * ZOOM_STEP)
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const onWheel = (event: WheelEvent) => {
      if (wheel === 'held' && !event.ctrlKey && !event.metaKey) return
      event.preventDefault()
      const rect = svg.getBoundingClientRect()
      const factor = event.deltaY > 0 ? ZOOM_STEP : 1 / ZOOM_STEP
      setCamera((current) => {
        const scale = clampScale(current.scale * factor)
        const px =
          current.cx +
          (event.clientX - rect.left - rect.width / 2) * current.scale
        const py =
          current.cy +
          (event.clientY - rect.top - rect.height / 2) * current.scale
        return {
          cx: px - (px - current.cx) * (scale / current.scale),
          cy: py - (py - current.cy) * (scale / current.scale),
          scale,
        }
      })
    }
    svg.addEventListener('wheel', onWheel, { passive: false })
    return () => svg.removeEventListener('wheel', onWheel)
  })
  const zoom = (factor: number) =>
    setCamera((current) => ({
      ...current,
      scale: clampScale(current.scale * factor),
    }))
  const pan = (dx: number, dy: number) =>
    setCamera((current) => ({
      ...current,
      cx: current.cx + dx * current.scale,
      cy: current.cy + dy * current.scale,
    }))
  const view =
    camera && size
      ? {
          x: camera.cx - (size.width * camera.scale) / 2,
          y: camera.cy - (size.height * camera.scale) / 2,
          width: size.width * camera.scale,
          height: size.height * camera.scale,
        }
      : { x: 0, y: 0, width: layout.width, height: layout.height }
  const unit = camera?.scale ?? 1
  const fade = hovered !== null ? HOVER_DIM : DIM
  const bringIntoView = (id: number) => {
    const card = layout.cards.get(id)
    if (!card || !camera) return
    const inside =
      card.x >= view.x &&
      card.y >= view.y &&
      card.x + layout.card.width <= view.x + view.width &&
      card.y + layout.card.height <= view.y + view.height
    if (!inside) centreOn(id, camera.scale)
  }
  const lit = (ids: number[]) =>
    line === null || ids.every((id) => line.has(id))
  const touched = (ids: number[]) =>
    line === null || ids.some((id) => line.has(id))
  const carried = (parents: number[], children: number[]) =>
    line === null || (touched(parents) && touched(children))
  const miniScale = Math.max(layout.width, layout.height) / (MINI_STROKE * 100)
  return (
    <div
      ref={frame}
      className={cn(
        'scene-frame relative min-w-0 overflow-hidden bg-card',
        className
      )}
    >
      <svg
        ref={svgRef}
        role='group'
        aria-label={`Family tree of ${names.get(tree.root) ?? ''}`}
        tabIndex={0}
        viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`}
        className='block h-full w-full cursor-grab touch-none outline-none select-none active:cursor-grabbing'
        onKeyDown={(event) => {
          const moves: Record<string, [number, number]> = {
            ArrowLeft: [-PAN_STEP, 0],
            ArrowRight: [PAN_STEP, 0],
            ArrowUp: [0, -PAN_STEP],
            ArrowDown: [0, PAN_STEP],
          }
          const move = moves[event.key]
          if (move && event.target === event.currentTarget) {
            event.preventDefault()
            pan(move[0], move[1])
          }
          if (event.key === '+' || event.key === '=') zoom(1 / ZOOM_STEP)
          if (event.key === '-') zoom(ZOOM_STEP)
        }}
        onPointerDown={(event) => {
          if (!camera) return
          drag.current = {
            x: event.clientX,
            y: event.clientY,
            camera,
            moved: false,
          }
        }}
        onPointerMove={(event) => {
          const start = drag.current
          if (!start) return
          const dx = event.clientX - start.x
          const dy = event.clientY - start.y
          if (!start.moved && Math.hypot(dx, dy) < DRAG_SLOP) return
          if (!start.moved)
            event.currentTarget.setPointerCapture(event.pointerId)
          start.moved = true
          setCamera({
            ...start.camera,
            cx: start.camera.cx - dx * start.camera.scale,
            cy: start.camera.cy - dy * start.camera.scale,
          })
        }}
        onPointerUp={() => {
          dragged.current = drag.current?.moved === true
          drag.current = null
        }}
        onClickCapture={(event) => {
          if (!dragged.current) return
          dragged.current = false
          event.stopPropagation()
          event.preventDefault()
        }}
      >
        {layout.rows.map((row, index) => (
          <g key={row.generation}>
            <rect
              x={-layout.width}
              y={row.y - 38}
              width={layout.width * 3}
              height={layout.card.height + 76}
              className={index % 2 === 0 ? 'fill-muted/25' : 'fill-transparent'}
            />
            <text
              x={view.x + ROW_LABEL_X * unit}
              y={row.y - 12}
              fontSize={12 * unit}
              letterSpacing={1.5 * unit}
              strokeWidth={5 * unit}
              paintOrder='stroke'
              strokeLinejoin='round'
              className='fill-muted-foreground stroke-card font-display uppercase'
            >
              {generationWord(row.generation)}
            </text>
          </g>
        ))}
        {layout.families.map((family) => (
          <path
            key={family.key}
            d={family.path}
            fill='none'
            strokeWidth={
              carried(family.parents, family.children) && line ? 3 : 2
            }
            strokeLinecap='round'
            strokeLinejoin='round'
            opacity={carried(family.parents, family.children) ? 1 : fade}
            className={cn(
              'transition-opacity duration-300',
              line && carried(family.parents, family.children)
                ? 'stroke-primary'
                : 'stroke-gild/80'
            )}
          >
            <title>{`${family.parents.map((id) => names.get(id)).join(' and ')} → ${family.children.map((id) => names.get(id)).join(', ')}`}</title>
          </path>
        ))}
        {layout.care.map((care) => {
          const look = CARE_LOOK[care.kind]
          return (
            <path
              key={care.key}
              d={care.path}
              fill='none'
              strokeWidth={2}
              strokeDasharray={look.dash}
              strokeLinecap='round'
              opacity={
                line === null
                  ? CARE_REST
                  : touched([care.tie.source_id, care.tie.target_id])
                    ? 1
                    : fade * CARE_REST
              }
              className={look.stroke}
            >
              <title>{`${names.get(care.tie.source_id)} · ${look.label.toLowerCase()} · ${names.get(care.tie.target_id)}`}</title>
            </path>
          )
        })}
        {layout.partners.map((mark) => {
          const look = PARTNER_LOOK[mark.kind]
          const Icon = knotIcon(mark)
          const shown = lit([mark.first]) || lit([mark.second])
          const held =
            mark.kind === 'spouse_of' &&
            !mark.ended &&
            layout.cards.get(mark.first)?.y === layout.cards.get(mark.second)?.y
          return (
            <g key={mark.key} opacity={shown ? 1 : fade}>
              {held && (
                <path
                  d={mark.path}
                  fill='none'
                  strokeWidth={6}
                  className={
                    mark.widowed
                      ? 'stroke-muted-foreground/60'
                      : 'stroke-gild/70'
                  }
                />
              )}
              <path
                d={mark.path}
                fill='none'
                strokeWidth={held ? 2 : 2.25}
                strokeDasharray={mark.ended ? ENDED_DASH : look.dash}
                strokeLinecap='round'
                className={
                  held
                    ? 'stroke-card'
                    : mark.ended
                      ? 'stroke-muted-foreground'
                      : look.stroke
                }
              />
              <g transform={`translate(${mark.knot.x} ${mark.knot.y})`}>
                <title>{knotTitle(mark, names)}</title>
                <circle
                  r={KNOT_RADIUS}
                  strokeWidth={1.5}
                  className={cn(
                    'fill-card',
                    mark.ended ? 'stroke-muted-foreground' : look.stroke
                  )}
                />
                <Icon
                  x={-KNOT_ICON / 2}
                  y={-KNOT_ICON / 2}
                  width={KNOT_ICON}
                  height={KNOT_ICON}
                  aria-hidden='true'
                  className={
                    mark.ended || mark.widowed
                      ? 'text-muted-foreground'
                      : mark.kind === 'spouse_of'
                        ? 'text-destructive'
                        : 'text-foreground'
                  }
                />
              </g>
            </g>
          )
        })}
        {[...layout.cards.values()].map((card) => (
          <g
            key={card.person.id}
            onPointerEnter={() => setHovered(card.person.id)}
            onPointerLeave={() => setHovered(null)}
          >
            <TreeCard
              card={card}
              box={layout.card}
              kin={card.person.relation}
              ink={
                card.person.house_id === null
                  ? null
                  : (inks.get(card.person.house_id) ?? null)
              }
              root={card.person.id === tree.root}
              selected={card.person.id === selected}
              dimmed={line !== null && !line.has(card.person.id) ? fade : null}
              compact={unit > COMPACT_SCALE}
              onSelect={onSelect}
              onFocus={bringIntoView}
            />
          </g>
        ))}
      </svg>
      <div className='absolute top-3 right-3 flex flex-col gap-1.5'>
        <Button
          size='icon-sm'
          variant='outline'
          aria-label='Zoom in'
          disabled={!camera || camera.scale <= 1 / MAX_ZOOM}
          disabledReason='This is as close as the tree comes.'
          onClick={() => zoom(1 / ZOOM_STEP)}
        >
          <Plus />
        </Button>
        <Button
          size='icon-sm'
          variant='outline'
          aria-label='Zoom out'
          disabled={!camera || !fit || camera.scale >= fit.scale * ZOOM_STEP}
          disabledReason='The whole tree is already in view.'
          onClick={() => zoom(ZOOM_STEP)}
        >
          <Minus />
        </Button>
        <Button
          size='icon-sm'
          variant='outline'
          aria-label='Show the whole tree'
          disabled={!fit}
          disabledReason='The tree is still being measured.'
          onClick={() => fit && setCamera(fit)}
        >
          <Maximize />
        </Button>
        <Button
          size='icon-sm'
          variant='outline'
          aria-label='Back to this mortal'
          onClick={() => centreOn(tree.root, 1 / START_ZOOM)}
        >
          <Crosshair />
        </Button>
      </div>
      <svg
        role='img'
        aria-label='Overview of the whole tree'
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        preserveAspectRatio='xMidYMid meet'
        className='absolute right-3 bottom-3 h-24 w-56 cursor-pointer rounded-md border surface-framed border-gild/60 bg-card/85 shadow-md max-sm:hidden'
        onClick={(event) => {
          const rect = event.currentTarget.getBoundingClientRect()
          const ratio = Math.max(
            layout.width / rect.width,
            layout.height / rect.height
          )
          const x =
            (event.clientX -
              rect.left -
              (rect.width - layout.width / ratio) / 2) *
            ratio
          const y =
            (event.clientY -
              rect.top -
              (rect.height - layout.height / ratio) / 2) *
            ratio
          setCamera((current) => ({ ...current, cx: x, cy: y }))
        }}
      >
        {[...layout.cards.values()].map((card) => {
          const ink =
            card.person.house_id === null
              ? null
              : (inks.get(card.person.house_id) ?? null)
          return (
            <rect
              key={card.person.id}
              x={card.x}
              y={card.y}
              width={layout.card.width}
              height={layout.card.height}
              rx={18}
              className={
                card.person.id === tree.root
                  ? 'fill-gild-hi'
                  : card.person.id === selected
                    ? 'fill-primary'
                    : ink
                      ? INK_FILLS[ink]
                      : 'fill-muted-foreground'
              }
            />
          )
        })}
        <rect
          x={view.x}
          y={view.y}
          width={view.width}
          height={view.height}
          fill='none'
          strokeWidth={miniScale * MINI_STROKE}
          className='stroke-primary'
        />
      </svg>
    </div>
  )
}
