import { AFLOAT, GROUNDED, MARGINS, type Silhouette } from './silhouettes'

const SHEEN = 'fill-primary/5 stroke-none'
const BODY = 'stroke-primary/50'
const TRIM = 'fill-none stroke-primary/40'
const DARK = 'fill-muted stroke-border'

function crenels(x: number, y: number, w: number, step: number) {
  const count = Math.max(2, Math.floor(w / step))
  const width = w / (count * 2 - 1)
  return Array.from({ length: count }, (_, index) => (
    <rect
      key={index}
      x={x + index * width * 2}
      y={y - width}
      width={width}
      height={width}
      className={BODY}
    />
  ))
}

function wheels(x: number, y: number, w: number, radius: number) {
  const count = Math.max(2, Math.min(4, Math.round(w / 70)))
  return Array.from({ length: count }, (_, index) => {
    const cx = x + radius + ((w - radius * 2) * index) / (count - 1)
    return (
      <g key={index}>
        <circle cx={cx} cy={y} r={radius} className={DARK} />
        <circle cx={cx} cy={y} r={radius * 0.35} className={TRIM} />
      </g>
    )
  })
}

export type Paint = { surface: string; shadow: string }

export function Hull({
  shape,
  x,
  y,
  w,
  h,
  paint,
}: {
  shape: Silhouette
  x: number
  y: number
  w: number
  h: number
  paint: Paint
}) {
  const m = MARGINS[shape]
  const floor = y + h + m.bottom - 2
  return (
    <g aria-hidden='true'>
      {GROUNDED.has(shape) && (
        <>
          <ellipse
            cx={x + w / 2}
            cy={floor}
            rx={w / 2 + m.left}
            ry={4}
            className='fill-foreground/30 stroke-none'
            filter={`url(#${paint.shadow})`}
          />
          <line
            x1={x - m.left - 6}
            y1={floor}
            x2={x + w + m.right + 6}
            y2={floor}
            className='stroke-border'
            strokeWidth={1}
          />
        </>
      )}
      {AFLOAT.has(shape) && (
        <path
          d={waves(
            x - m.left - 4,
            x + w + m.right + 4,
            y + h + m.bottom * 0.15
          )}
          className='fill-info/15 stroke-info/50'
          strokeWidth={0.9}
        />
      )}
      <g fill={`url(#${paint.surface})`}>
        <Shape shape={shape} x={x} y={y} w={w} h={h} />
      </g>
    </g>
  )
}

function waves(from: number, to: number, level: number): string {
  const step = 9
  const count = Math.ceil((to - from) / step)
  const crest = Array.from(
    { length: count },
    () => `q ${step / 4} -2.4 ${step / 2} 0 t ${step / 2} 0`
  ).join(' ')
  return `M ${from} ${level} ${crest} V ${level + 10} H ${from} Z`
}

function Masts({ x, y, w }: { x: number; y: number; w: number }) {
  const m = MARGINS.sail
  return (
    <>
      {[0.32, 0.62].map((at, index) => {
        const foot = x + w * at
        const height = m.top - (index === 0 ? 4 : 10)
        return (
          <g key={at}>
            <path
              d={`M ${foot + 2} ${y - height + 6} Q ${foot + w * 0.16} ${y - height / 2} ${foot + 2} ${y - 4} Z`}
              className='fill-foreground/10 stroke-primary/50'
              strokeWidth={0.9}
            />
            <line
              x1={foot}
              y1={y}
              x2={foot}
              y2={y - height}
              className='stroke-primary/70'
              strokeWidth={1.6}
              strokeLinecap='round'
            />
            <line
              x1={foot - 6}
              y1={y - height + 5}
              x2={foot + 6}
              y2={y - height + 5}
              className='stroke-primary/50'
              strokeWidth={1}
            />
          </g>
        )
      })}
    </>
  )
}

function Shape({
  shape,
  x,
  y,
  w,
  h,
}: {
  shape: Silhouette
  x: number
  y: number
  w: number
  h: number
}) {
  const right = x + w
  const bottom = y + h
  const mid = y + h / 2
  const m = MARGINS[shape]
  switch (shape) {
    case 'sail':
    case 'ship': {
      const hull = `M ${right + m.right * 0.6} ${y} L ${right + m.right * 0.2} ${bottom - h * 0.25} Q ${right - w * 0.08} ${bottom + m.bottom} ${x + w * 0.3} ${bottom + m.bottom * 0.6} Q ${x} ${bottom} ${x - m.left} ${y + h * 0.18} L ${x - m.left * 0.3} ${y} Z`
      return (
        <g aria-hidden='true'>
          <path d={hull} className={BODY} strokeWidth={1.2} />
          <path d={hull} className={SHEEN} />
          <line
            x1={x - m.left * 0.3}
            y1={y}
            x2={right + m.right * 0.6}
            y2={y}
            className={TRIM}
            strokeWidth={1.5}
          />
          <line
            x1={x}
            y1={bottom - h * 0.12}
            x2={right}
            y2={bottom - h * 0.12}
            className={TRIM}
            strokeDasharray='4 3'
          />
          {shape === 'sail' && <Masts x={x} y={y} w={w} />}
        </g>
      )
    }
    case 'submarine':
      return (
        <g aria-hidden='true'>
          <rect
            x={x + w * 0.38}
            y={y - m.top}
            width={w * 0.18}
            height={m.top + 6}
            rx={4}
            className={BODY}
          />
          <rect
            x={x - m.left}
            y={y - 4}
            width={w + m.left + m.right}
            height={h + 8}
            rx={(h + 8) / 2}
            className={BODY}
            strokeWidth={1.2}
          />
          <rect
            x={x - m.left}
            y={y - 4}
            width={w + m.left + m.right}
            height={h + 8}
            rx={(h + 8) / 2}
            className={SHEEN}
          />
          <path
            d={`M ${right + m.right} ${mid} l 10 -10 l 0 20 Z`}
            className={DARK}
          />
        </g>
      )
    case 'wheeled':
    case 'tracked': {
      const body = (
        <>
          <rect
            x={x - m.left}
            y={y - m.top}
            width={w + m.left + m.right}
            height={h + m.top + 6}
            rx={8}
            className={BODY}
            strokeWidth={1.2}
          />
          <rect
            x={x - m.left}
            y={y - m.top}
            width={w + m.left + m.right}
            height={h + m.top + 6}
            rx={8}
            className={SHEEN}
          />
        </>
      )
      return shape === 'wheeled' ? (
        <g aria-hidden='true'>
          {body}
          {wheels(x, bottom + m.bottom * 0.45, w, m.bottom * 0.5)}
        </g>
      ) : (
        <g aria-hidden='true'>
          {body}
          <rect
            x={x - m.left * 0.6}
            y={bottom + 4}
            width={w + m.left * 1.2}
            height={m.bottom - 6}
            rx={(m.bottom - 6) / 2}
            className={DARK}
          />
          {wheels(
            x + 6,
            bottom + 4 + (m.bottom - 6) / 2,
            w - 12,
            (m.bottom - 10) / 2
          )}
        </g>
      )
    }
    case 'walker':
      return (
        <g aria-hidden='true'>
          <rect
            x={x - m.left}
            y={y - m.top}
            width={w + m.left + m.right}
            height={h + m.top + 6}
            rx={10}
            className={BODY}
            strokeWidth={1.2}
          />
          <rect
            x={x - m.left}
            y={y - m.top}
            width={w + m.left + m.right}
            height={h + m.top + 6}
            rx={10}
            className={SHEEN}
          />
          {[0.22, 0.78].map((at) => (
            <path
              key={at}
              d={`M ${x + w * at} ${bottom + 6} l -8 ${m.bottom * 0.5} l 8 ${m.bottom * 0.45} h 10`}
              className={TRIM}
              strokeWidth={4}
              strokeLinecap='round'
              strokeLinejoin='round'
            />
          ))}
        </g>
      )
    case 'beast':
      return (
        <g aria-hidden='true'>
          <ellipse
            cx={x + w / 2}
            cy={mid}
            rx={w / 2 + m.right}
            ry={h / 2 + m.top}
            className={BODY}
            strokeWidth={1.2}
          />
          <ellipse
            cx={x + w / 2}
            cy={mid}
            rx={w / 2 + m.right}
            ry={h / 2 + m.top}
            className={SHEEN}
          />
          <circle
            cx={x - m.left * 0.55}
            cy={y + h * 0.15}
            r={m.left * 0.5}
            className={BODY}
          />
          {[0.15, 0.35, 0.65, 0.85].map((at) => (
            <line
              key={at}
              x1={x + w * at}
              y1={bottom + m.top * 0.6}
              x2={x + w * at}
              y2={bottom + m.bottom}
              className={TRIM}
              strokeWidth={4}
              strokeLinecap='round'
            />
          ))}
        </g>
      )
    case 'envelope':
      return (
        <g aria-hidden='true'>
          <ellipse
            cx={x + w / 2}
            cy={y + h * 0.42}
            rx={w / 2 + m.left}
            ry={h * 0.42 + m.top}
            className={BODY}
            strokeWidth={1.2}
          />
          <ellipse
            cx={x + w / 2}
            cy={y + h * 0.42}
            rx={w / 2 + m.left}
            ry={h * 0.42 + m.top}
            className={SHEEN}
          />
          {[-0.3, 0, 0.3].map((at) => (
            <path
              key={at}
              d={`M ${x - m.left * 0.6} ${y + h * 0.42} Q ${x + w / 2} ${y + h * (0.42 + at)} ${right + m.right * 0.6} ${y + h * 0.42}`}
              className={TRIM}
            />
          ))}
          <rect
            x={x + w * 0.25}
            y={bottom - 4}
            width={w * 0.5}
            height={m.bottom + 4}
            rx={4}
            className={DARK}
          />
        </g>
      )
    case 'winged':
      return (
        <g aria-hidden='true'>
          <path
            d={`M ${x + w * 0.35} ${mid} L ${x + w * 0.62} ${y - m.top} L ${x + w * 0.74} ${y - m.top} L ${x + w * 0.62} ${mid} Z`}
            className={BODY}
          />
          <path
            d={`M ${x + w * 0.35} ${mid} L ${x + w * 0.62} ${bottom + m.bottom} L ${x + w * 0.74} ${bottom + m.bottom} L ${x + w * 0.62} ${mid} Z`}
            className={BODY}
          />
          <path
            d={`M ${x - m.left} ${mid} Q ${x - m.left * 0.6} ${y - 4} ${x + w * 0.1} ${y - 4} L ${right + m.right} ${y + h * 0.3} L ${right + m.right} ${bottom - h * 0.3} L ${x + w * 0.1} ${bottom + 4} Q ${x - m.left * 0.6} ${bottom + 4} ${x - m.left} ${mid} Z`}
            className={BODY}
            strokeWidth={1.2}
          />
          <path
            d={`M ${right} ${y + h * 0.3} L ${right + m.right} ${y - m.top * 0.5} L ${right + m.right} ${bottom + m.bottom * 0.5} L ${right} ${bottom - h * 0.3} Z`}
            className={DARK}
          />
        </g>
      )
    case 'starship':
      return (
        <g aria-hidden='true'>
          <path
            d={`M ${right} ${y} L ${right + m.right} ${y - m.top} L ${right + m.right} ${y} Z`}
            className={DARK}
          />
          <path
            d={`M ${right} ${bottom} L ${right + m.right} ${bottom + m.bottom} L ${right + m.right} ${bottom} Z`}
            className={DARK}
          />
          <path
            d={`M ${x - m.left} ${mid} L ${x - m.left * 0.3} ${y - m.top * 0.6} L ${right + m.right * 0.4} ${y - m.top * 0.6} L ${right + m.right * 0.4} ${bottom + m.bottom * 0.6} L ${x - m.left * 0.3} ${bottom + m.bottom * 0.6} Z`}
            className={BODY}
            strokeWidth={1.2}
          />
          <path
            d={`M ${x - m.left} ${mid} L ${x - m.left * 0.3} ${y - m.top * 0.6} L ${right + m.right * 0.4} ${y - m.top * 0.6} L ${right + m.right * 0.4} ${bottom + m.bottom * 0.6} L ${x - m.left * 0.3} ${bottom + m.bottom * 0.6} Z`}
            className={SHEEN}
          />
          {[0.3, 0.5, 0.7].map((at) => (
            <circle
              key={at}
              cx={right + m.right * 0.7}
              cy={y + h * at}
              r={3}
              className='fill-primary/60 stroke-none'
            />
          ))}
        </g>
      )
    case 'drill':
      return (
        <g aria-hidden='true'>
          <path
            d={`M ${x - 4} ${y - 4} L ${x - m.left} ${mid} L ${x - 4} ${bottom + 4} Z`}
            className={DARK}
          />
          {[0.3, 0.55, 0.8].map((at) => (
            <line
              key={at}
              x1={x - m.left * at}
              y1={mid - (h / 2 + 4) * (1 - at)}
              x2={x - m.left * at}
              y2={mid + (h / 2 + 4) * (1 - at)}
              className={TRIM}
            />
          ))}
          <rect
            x={x - 4}
            y={y - m.top}
            width={w + m.right + 4}
            height={h + m.top + m.bottom}
            rx={(h + m.top + m.bottom) / 3}
            className={BODY}
            strokeWidth={1.2}
          />
          <rect
            x={x - 4}
            y={y - m.top}
            width={w + m.right + 4}
            height={h + m.top + m.bottom}
            rx={(h + m.top + m.bottom) / 3}
            className={SHEEN}
          />
        </g>
      )
    case 'ring':
      return (
        <g aria-hidden='true'>
          <ellipse
            cx={x + w / 2}
            cy={mid}
            rx={w / 2 + m.left}
            ry={h / 2 + m.top}
            className={BODY}
            strokeWidth={6}
          />
          <ellipse
            cx={x + w / 2}
            cy={mid}
            rx={w / 2 + m.left}
            ry={h / 2 + m.top}
            className={TRIM}
            strokeWidth={1}
          />
        </g>
      )
    default: {
      const left = x - m.left
      const top = y - 6
      const width = w + m.left + m.right
      const height = h + 12 + m.bottom - 6
      const roof =
        shape === 'hall' ? (
          <path
            d={`M ${left - 6} ${top} L ${x + w / 2} ${top - m.top + 4} L ${left + width + 6} ${top} Z`}
            className={BODY}
            strokeWidth={1.2}
          />
        ) : shape === 'dome' ? (
          <path
            d={`M ${left + width * 0.12} ${top} A ${width * 0.38} ${m.top - 4} 0 0 1 ${left + width * 0.88} ${top} Z`}
            className={BODY}
            strokeWidth={1.2}
          />
        ) : shape === 'spire' ? (
          <path
            d={`M ${left + width * 0.2} ${top} L ${x + w / 2} ${top - m.top + 2} L ${left + width * 0.8} ${top} Z`}
            className={BODY}
            strokeWidth={1.2}
          />
        ) : (
          crenels(left, top, width, shape === 'tower' ? 14 : 18)
        )
      return (
        <g aria-hidden='true'>
          {roof}
          <rect
            x={left}
            y={top}
            width={width}
            height={height}
            rx={3}
            className={BODY}
            strokeWidth={1.2}
          />
          <rect
            x={left}
            y={top}
            width={width}
            height={height}
            rx={3}
            className={SHEEN}
          />
          <line
            x1={left}
            y1={top + height}
            x2={left + width}
            y2={top + height}
            className={TRIM}
            strokeWidth={2}
          />
        </g>
      )
    }
  }
}
