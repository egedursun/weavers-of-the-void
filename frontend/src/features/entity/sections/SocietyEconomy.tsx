import { formatDecimal, formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Section, Paged } from '@/components/domain'
import { Label, Muted, Stat } from '@/components/typography'
import { humanize } from '../actions/schema'
import { RULE, useRuleLookup } from '../api/rules'
import { type EntityDetail } from '../api/types'
import { PERCENT_MAX } from '../constants'

const CLASS_ORDER = [
  'scribe',
  'professional',
  'official',
  'artisan',
  'worker',
  'priest',
  'merchant',
  'warrior',
  'farmer',
  'noble',
  'monastic',
  'citizen',
  'outcast',
  'unemployed',
  'serf_or_slave',
]
const HALF = 50

function priceBand(price: number, scarcity?: number, plenty?: number): string {
  if (scarcity !== undefined && price >= scarcity) return 'expensive'
  if (plenty !== undefined && price <= plenty) return 'cheap'
  return 'normal'
}

function ordered(keys: string[]): string[] {
  return [...keys].sort((left, right) => {
    const a = CLASS_ORDER.indexOf(left)
    const b = CLASS_ORDER.indexOf(right)
    return (a < 0 ? CLASS_ORDER.length : a) - (b < 0 ? CLASS_ORDER.length : b)
  })
}

export function SocietyEconomy({ detail }: { detail: EntityDetail }) {
  const society = detail.insight.society
  const rule = useRuleLookup()
  if (!society) return null
  const scarcity = rule(RULE.priceScarcity)
  const plenty = rule(RULE.pricePlenty)
  const classes = ordered(
    Array.from(
      new Set([
        ...Object.keys(society.shares),
        ...Object.keys(society.satisfaction),
      ])
    )
  )
  const contentment = Object.values(society.satisfaction)
  const unhappiest =
    society.unhappiest &&
    contentment.some(
      (value) => value > (society.satisfaction[society.unhappiest ?? ''] ?? 0)
    )
      ? society.unhappiest
      : null
  return (
    <Section
      id='section-society'
      title='Society and economy'
      description='Who does the work, how content each class is, and what the stores hold.'
    >
      {(society.uprising_risk || society.bankruptcy_risk || unhappiest) && (
        <div className='flex min-w-0 flex-wrap gap-2'>
          {society.uprising_risk && (
            <Badge variant='destructive'>An uprising is near</Badge>
          )}
          {society.bankruptcy_risk && (
            <Badge variant='warning'>The treasury may fail</Badge>
          )}
          {unhappiest && (
            <Badge variant='outline'>{`Least content: ${humanize(unhappiest)}`}</Badge>
          )}
        </div>
      )}
      {classes.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-3'>
          {classes.map((name) => {
            const share = society.shares[name] ?? 0
            const content = society.satisfaction[name]
            return (
              <li
                key={name}
                className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 sm:gap-4'
              >
                <div className='flex min-w-0 flex-col gap-1'>
                  <div className='flex min-w-0 items-center gap-2'>
                    <Label className='flex-1' truncate>
                      {humanize(name)}
                    </Label>
                    <Stat
                      value={`${formatDecimal(share, 1)}%`}
                      tone={share > 0 ? 'inherit' : 'muted'}
                    />
                  </div>
                  <Progress
                    value={Math.min(PERCENT_MAX, share)}
                    size='sm'
                    aria-label={`${humanize(name)} share`}
                  />
                </div>
                {content !== undefined && (
                  <div className='flex min-w-0 flex-col gap-1'>
                    <div className='flex min-w-0 items-center gap-2'>
                      <Label className='flex-1'>Contentment</Label>
                      <Stat value={content} />
                    </div>
                    <Progress
                      value={content}
                      size='sm'
                      tone={
                        content >= HALF
                          ? 'success'
                          : unhappiest === name
                            ? 'destructive'
                            : 'warning'
                      }
                      aria-label={`${humanize(name)} contentment`}
                    />
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
      {Object.keys(society.stocks).length > 0 && (
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Paged items={Object.entries(society.stocks)}>
            {([good, amount]) => {
              const price = society.prices[good]
              return (
                <Badge
                  key={good}
                  variant='outline'
                  title={
                    price !== undefined
                      ? `Price ×${formatDecimal(price / PERCENT_MAX)}`
                      : undefined
                  }
                >
                  {`${humanize(good)} ${formatInteger(amount)}${price !== undefined ? ` · ${priceBand(price, scarcity, plenty)}` : ''}`}
                </Badge>
              )
            }}
          </Paged>
        </div>
      )}
      <Muted variant='caption'>
        A class whose contentment falls too low may revolt.
      </Muted>
    </Section>
  )
}
