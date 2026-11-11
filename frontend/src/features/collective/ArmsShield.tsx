import type { components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'

type Schema = components['schemas']
type Tincture = Schema['Tincture']

const SHIELD = 'M10 8H110V62C110 94 86 112 60 124C34 112 10 94 10 62Z'

const FILLS: Record<Tincture, string> = {
  gold: 'fill-tincture-gold',
  silver: 'fill-tincture-silver',
  red: 'fill-tincture-red',
  blue: 'fill-tincture-blue',
  green: 'fill-tincture-green',
  black: 'fill-tincture-black',
  purple: 'fill-tincture-purple',
  orange: 'fill-tincture-orange',
}

const STROKES: Record<Tincture, string> = {
  gold: 'stroke-tincture-gold',
  silver: 'stroke-tincture-silver',
  red: 'stroke-tincture-red',
  blue: 'stroke-tincture-blue',
  green: 'stroke-tincture-green',
  black: 'stroke-tincture-black',
  purple: 'stroke-tincture-purple',
  orange: 'stroke-tincture-orange',
}

const DIVISIONS: Record<Schema['HeraldicDivision'], string> = {
  plain: '',
  per_pale: 'M60 8H110V62C110 94 86 112 60 124Z',
  per_fess: 'M10 62H110C110 94 86 112 60 124C34 112 10 94 10 62Z',
  per_bend: 'M10 8L110 124V62C110 94 86 112 60 124C40 115 22 101 14 82Z',
  quarterly: 'M60 8H110V62H60ZM10 62H60V124C34 112 10 94 10 62Z',
  chevron: 'M10 96L60 46L110 96V78L60 28L10 78Z',
  bordure:
    'M10 8H110V62C110 94 86 112 60 124C34 112 10 94 10 62ZM20 18V62C20 88 40 104 60 113C80 104 100 88 100 62V18Z',
}

const CHARGES: Record<Schema['HeraldicCharge'], string> = {
  none: '',
  beast: 'M38 84L44 58L56 50L72 52L80 44L86 50L82 60L84 84H76L74 70H52L48 84Z',
  bird: 'M60 46L66 58L88 52L72 66L76 86L60 74L44 86L48 66L32 52L54 58Z',
  tree: 'M57 92V74H44L60 34L76 74H63V92Z',
  tower: 'M44 92V50H48V42H54V50H66V42H72V50H76V92H66V78H54V92Z',
  sword: 'M58 30H62V78H72V82H62V94H58V82H48V78H58Z',
  crown: 'M40 82L36 50L50 64L60 44L70 64L84 50L80 82Z',
  star: 'M60 36L66 56H86L70 68L76 88L60 76L44 88L50 68L34 56H54Z',
  sun: 'M60 44A18 18 0 1 0 60.1 44ZM60 30V38M60 82V90M30 62H38M82 62H90M39 41L45 47M75 77L81 83M81 41L75 47M45 77L39 83',
  moon: 'M66 38A24 24 0 1 0 66 86A18 18 0 1 1 66 38Z',
  eye: 'M34 62C46 46 74 46 86 62C74 78 46 78 34 62ZM60 54A8 8 0 1 0 60.1 54Z',
  hand: 'M48 92V62L42 50L46 48L52 58V38H56V58H58V34H62V58H64V36H68V58H70V42H74V70L68 92Z',
  wheel:
    'M60 40A22 22 0 1 0 60.1 40ZM60 48A14 14 0 1 1 59.9 48ZM58 40H62V84H58ZM38 60H82V64H38Z',
  wave: 'M30 58C40 48 50 68 60 58C70 48 80 68 90 58V66C80 76 70 56 60 66C50 76 40 56 30 66ZM30 74C40 64 50 84 60 74C70 64 80 84 90 74V82C80 92 70 72 60 82C50 92 40 72 30 82Z',
  flame:
    'M60 92C46 92 40 80 44 68C48 58 56 54 54 40C64 48 70 58 68 66C72 62 74 56 72 50C80 58 82 72 76 82C72 88 66 92 60 92Z',
  key: 'M56 30A10 10 0 1 0 64 30A10 10 0 1 0 56 30ZM58 46H62V90H58ZM62 78H72V82H62ZM62 70H70V74H62Z',
}

const SIZES = {
  sm: 'size-portrait-md',
  md: 'size-portrait-lg',
  lg: 'size-portrait-xl',
} as const

export function ArmsShield({
  field,
  division,
  second,
  charge,
  chargeTincture,
  label,
  size = 'md',
}: {
  field: Tincture
  division: Schema['HeraldicDivision']
  second: Tincture | null
  charge: Schema['HeraldicCharge']
  chargeTincture: Tincture | null
  label: string
  size?: keyof typeof SIZES
}) {
  const parted = DIVISIONS[division]
  const glyph = CHARGES[charge]
  const ink = chargeTincture ?? 'black'
  return (
    <svg
      viewBox='0 0 120 132'
      role='img'
      aria-label={label}
      className={cn('shrink-0 drop-shadow-sm', SIZES[size])}
    >
      <path d={SHIELD} className={FILLS[field]} />
      {parted && (
        <path
          d={parted}
          fillRule={division === 'bordure' ? 'evenodd' : undefined}
          className={FILLS[second ?? field]}
        />
      )}
      {glyph && (
        <path
          d={glyph}
          fillRule='evenodd'
          strokeWidth={charge === 'sun' ? 4 : 0}
          strokeLinecap='round'
          className={cn(FILLS[ink], STROKES[ink])}
        />
      )}
      <path
        d={SHIELD}
        fill='none'
        strokeWidth={3}
        className='stroke-tincture-line'
      />
    </svg>
  )
}
