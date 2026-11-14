import {
  Award,
  Church,
  Coins,
  Crown,
  Languages,
  Medal,
  TriangleAlert,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  IconStat,
  type KpiTone,
  Medallion,
  MiniStat,
  Section,
  LoadingBlock,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { RegisterList } from '@/features/entity/lore/RegisterParts'
import {
  type TongueAtlas as Atlas,
  useTongues,
} from '@/features/entity/lore/api'
import {
  REGISTERS,
  type RegisterKind,
} from '@/features/entity/lore/cultureLabels'

type Rank = Atlas['ranking'][number]

const PERCENT = 100
const SHADES = [
  'bg-muted/30',
  'bg-primary/10',
  'bg-primary/20',
  'bg-primary/35',
  'bg-primary/50',
  'bg-primary/70',
] as const
const PODIUM: { icon: LucideIcon; tone: KpiTone; label: string }[] = [
  { icon: Crown, tone: 'gold', label: 'Most esteemed' },
  { icon: Medal, tone: 'info', label: 'Second' },
  { icon: Award, tone: 'warning', label: 'Third' },
]

function shade(value: number): string {
  return SHADES[
    Math.min(
      SHADES.length - 1,
      Math.ceil((value / PERCENT) * (SHADES.length - 1))
    )
  ]
}

function RankToken({ index }: { index: number }) {
  const podium = PODIUM[index]
  if (podium)
    return <Medallion icon={podium.icon} tone={podium.tone} size='sm' />
  return (
    <span className='flex size-control-sm shrink-0 items-center justify-center rounded-full border bg-muted text-muted-foreground'>
      <Stat value={index + 1} />
    </span>
  )
}

function RankRow({ row, index }: { row: Rank; index: number }) {
  return (
    <li className='flex min-w-0 items-center gap-3 rounded-lg border bg-background px-2.5 py-2 @3xl/atlas:last:odd:col-span-2'>
      <RankToken index={index} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1'>
          <Text as='span' weight='semibold' className='min-w-0'>
            <EntityLink kind='entity' id={String(row.language.id)}>
              {row.language.name}
            </EntityLink>
          </Text>
          {row.lingua_franca && (
            <Badge size='sm' variant='default'>
              <Coins aria-hidden='true' />
              Lingua franca
            </Badge>
          )}
          {row.liturgical && (
            <Badge size='sm' variant='info'>
              <Church aria-hidden='true' />
              Tongue of worship
            </Badge>
          )}
          <span className='ml-auto flex shrink-0 items-center gap-2'>
            <IconStat
              icon={Users}
              label='Speaking peoples'
              value={row.speakers}
              tone='info'
            />
            <Stat value={row.prestige} unit={`/ ${PERCENT}`} />
          </span>
        </div>
        <Progress
          value={row.prestige}
          size='sm'
          tone={index === 0 ? 'default' : 'verdigris'}
          aria-label={`${row.language.name} prestige`}
        />
      </div>
    </li>
  )
}

function Ranking({ atlas }: { atlas: Atlas }) {
  const ranking = atlas.ranking
  const francas = ranking.filter((row) => row.lingua_franca).length
  const holy = ranking.filter((row) => row.liturgical).length
  const voices = ranking.reduce((sum, row) => sum + row.speakers, 0)
  if (ranking.length === 0)
    return (
      <EmptyState
        icon={Languages}
        title='No tongue is spoken yet'
        description='Tongues appear as peoples settle and speak.'
      />
    )
  return (
    <div className='@container/atlas flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 @3xl/atlas:grid-cols-4'>
        <MiniStat
          icon={Languages}
          label='Tongues'
          value={ranking.length}
          tone='gold'
        />
        <MiniStat
          icon={Coins}
          label='Lingua francas'
          value={francas}
          tone={francas > 0 ? 'gold' : 'muted'}
          hint='Tongues of the trade roads, learned by traders everywhere'
        />
        <MiniStat
          icon={Church}
          label='Tongues of worship'
          value={holy}
          tone={holy > 0 ? 'info' : 'muted'}
        />
        <MiniStat
          icon={Users}
          label='Speaking peoples'
          value={voices}
          tone='verdigris'
          hint='Every community counted once for each tongue it speaks'
        />
      </div>
      <ol
        data-surface='PrestigeRanking'
        className='grid min-w-0 grid-cols-1 gap-2 @3xl/atlas:grid-cols-2'
      >
        {ranking.map((row, index) => (
          <RankRow key={row.language.id} row={row} index={index} />
        ))}
      </ol>
    </div>
  )
}

function Heatmap({ atlas }: { atlas: Atlas }) {
  const ranking = atlas.ranking
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label>Understanding</Label>
        {SHADES.map((tint, index) => (
          <span key={tint} className='flex items-center gap-1'>
            <span
              aria-hidden='true'
              className={cn('size-icon-md rounded-sm border', tint)}
            />
            <Muted as='span' variant='caption'>
              {`${Math.round((index / (SHADES.length - 1)) * PERCENT)}%`}
            </Muted>
          </span>
        ))}
      </div>
      <div
        data-surface='IntelligibilityHeatmap'
        className='min-w-0 overflow-x-auto rounded-lg border bg-background'
      >
        <table className='border-separate border-spacing-0.5 p-1'>
          <thead>
            <tr>
              <th className='sticky left-0 bg-background' />
              {ranking.map((row, index) => (
                <th
                  key={row.language.id}
                  scope='col'
                  title={row.language.name}
                  className='size-control-sm text-center'
                >
                  <Muted as='span' variant='caption'>
                    {index + 1}
                  </Muted>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ranking.map((row, line) => (
              <tr key={row.language.id}>
                <th
                  scope='row'
                  className='sticky left-0 bg-background pr-2 text-left whitespace-nowrap'
                >
                  <Text as='span' variant='caption'>
                    <Muted as='span' variant='caption'>{`${line + 1} `}</Muted>
                    {row.language.name}
                  </Text>
                </th>
                {(atlas.matrix[line] ?? []).map((value, column) => {
                  const other = ranking[column]?.language.name ?? ''
                  const self = column === line
                  return (
                    <td
                      key={ranking[column]?.language.id ?? column}
                      title={`${row.language.name} → ${other}: ${value}%`}
                      aria-label={`${row.language.name} understands ${other}: ${value}%`}
                      className={cn(
                        'size-control-sm rounded-sm text-center',
                        self ? 'bg-muted' : shade(value)
                      )}
                    >
                      {!self && value > 0 && (
                        <Text as='span' variant='caption' weight='medium'>
                          {value}
                        </Text>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Muted variant='caption'>
        Columns follow the same numbers as the rows. Hover a cell for both
        names.
      </Muted>
    </div>
  )
}

function Registers({ atlas }: { atlas: Atlas }) {
  const kinds = Object.keys(REGISTERS) as RegisterKind[]
  return (
    <div data-surface='AtlasRegisters' className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {kinds.map((kind) => {
          const spec = REGISTERS[kind]
          const rows = atlas.registers.filter((row) => row.kind === kind)
          const tongues = new Set(rows.map((row) => row.language?.id))
          return (
            <IconStat
              key={kind}
              icon={spec.icon}
              tone={spec.tone}
              label={spec.label}
              value={rows.length}
              hint={`${plural(tongues.size, 'tongue', 'tongues')} · ${spec.hint ?? ''}`}
            />
          )
        })}
      </div>
      <RegisterList
        rows={atlas.registers}
        surface='AtlasRegisterList'
        showLanguage
      />
    </div>
  )
}

export function TongueAtlas({ worldId }: { worldId: number | null }) {
  const view = useTongues(worldId)
  if (worldId === null)
    return (
      <EmptyState
        icon={Languages}
        title='No world chosen'
        description='Choose a world to see how its tongues stand.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Section
        id='section-prestige'
        title='Prestige of tongues'
        description='Which tongue the powerful, the learned and the holy speak.'
        icon={Crown}
      >
        {view.isPending && <LoadingBlock label='Weighing the tongues' />}
        {view.isError && (
          <EmptyState
            icon={TriangleAlert}
            title='The tongues could not be weighed'
            description={view.error.message}
          />
        )}
        {view.data && <Ranking atlas={view.data} />}
      </Section>
      <Section
        id='section-intelligibility'
        title='Who understands whom'
        description='How much each tongue makes of every other; darker is closer.'
        icon={Languages}
        tone='verdigris'
      >
        {view.data && view.data.ranking.length > 0 && (
          <Heatmap atlas={view.data} />
        )}
      </Section>
      <Section
        id='section-registers'
        title='Court, liturgy, market and hearth'
        description='Which tongue each realm, faith and town uses for rule, prayer, trade and home.'
        icon={Church}
        tone='gold'
      >
        {view.data && <Registers atlas={view.data} />}
      </Section>
    </div>
  )
}
