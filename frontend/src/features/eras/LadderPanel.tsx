import { CircleCheck, Lock, Minus, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Medallion, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { why } from '@/features/dominion/model'
import { TECHNIQUE_WORDS } from '@/features/entity/affairs/labels'
import { type ErasNodeView, useEraAction } from './api'
import { CHANNELS, ERAS } from './labels'
import { signed } from './model'

type Row = ErasNodeView['techniques'][number]

function TechniqueTile({
  row,
  data,
  blocked,
}: {
  row: Row
  data: ErasNodeView
  blocked: string | null
}) {
  const keeper = data.keeper
  const setting = useEraAction(
    'research:technique',
    (held: boolean) => ({
      holder_id: keeper?.id ?? 0,
      technique: row.technique,
      held,
      secret: false,
    }),
    row.kept ? 'The technique is forgotten' : 'The technique is known'
  )
  const labels = Object.fromEntries(
    data.techniques.map((item) => [item.technique, item.label])
  )
  const missing = row.requires.filter(
    (item) => !data.techniques.find((other) => other.technique === item)?.held
  )
  const busy = why(
    blocked ??
      (keeper === null
        ? 'No town or people keeps knowledge for this thing'
        : null),
    setting.isPending
  )
  return (
    <li
      data-surface='EraTechnique'
      data-state={row.held ? 'known' : missing.length ? 'locked' : 'open'}
      className={cn(
        'flex h-full min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3',
        row.held && 'border-primary/50 bg-primary/8 ring-1 ring-primary/20',
        !row.held && missing.length > 0 && 'border-dashed bg-muted/20'
      )}
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion
          icon={
            row.held ? CircleCheck : missing.length ? Lock : ERAS[row.era].icon
          }
          tone={row.held ? 'gold' : missing.length ? 'muted' : 'info'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text
            as='span'
            weight='semibold'
            tone={row.held ? 'default' : 'muted'}
          >
            {row.label}
          </Text>
          <Muted variant='caption'>{row.effect}</Muted>
          {missing.length > 0 && (
            <Muted variant='caption'>
              {`Needs ${missing.map((item) => labels[item] ?? TECHNIQUE_WORDS[item]).join(', ')}`}
            </Muted>
          )}
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Paged items={row.effects} noun={['effect', 'effects']}>
          {(effect) => {
            const channel = CHANNELS[effect.channel]
            const Icon = channel.icon
            return (
              <Badge key={effect.channel} size='sm' variant='outline'>
                <Icon aria-hidden='true' />
                {`${channel.label} ${signed(effect.value, channel.unit)}`}
              </Badge>
            )
          }}
        </Paged>
        {row.programme && (
          <Badge size='sm' variant='warning'>
            Reached by a realm’s programme
          </Badge>
        )}
        {row.held && !row.kept && (
          <Badge size='sm' variant='secondary'>
            Known through its realm or home
          </Badge>
        )}
      </div>
      <div className='mt-auto flex min-w-0'>
        <Button
          size='sm'
          variant={
            row.kept ? 'outline' : missing.length ? 'secondary' : 'default'
          }
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate(!row.kept)}
        >
          {row.kept ? <Minus /> : <Plus />}
          {row.kept
            ? `Take it from ${keeper?.name ?? 'them'}`
            : `Teach it to ${keeper?.name ?? 'them'}`}
        </Button>
      </div>
    </li>
  )
}

export function LadderPanel({
  data,
  blocked,
}: {
  data: ErasNodeView
  blocked: string | null
}) {
  const eras = [...new Set(data.techniques.map((row) => row.era))]
  return (
    <div data-surface='LadderPanel' className='flex min-w-0 flex-col gap-6'>
      {eras.map((key) => {
        const era = ERAS[key]
        const rows = data.techniques.filter((row) => row.era === key)
        const known = rows.filter((row) => row.held).length
        return (
          <section
            key={key}
            aria-label={`${era.label} era techniques`}
            className='flex min-w-0 flex-col gap-3'
          >
            <div className='flex min-w-0 items-center gap-2.5'>
              <Medallion icon={era.icon} tone={era.tone} size='sm' />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Text as='span' weight='semibold'>
                  {`${era.label} era`}
                </Text>
                <Muted variant='caption'>{era.hint}</Muted>
              </div>
              <Badge
                size='sm'
                variant={known === rows.length ? 'default' : 'outline'}
              >
                {`${known} of ${rows.length} known`}
              </Badge>
            </div>
            <ul className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
              <Paged items={rows} as='li'>
                {(row) => (
                  <TechniqueTile
                    key={row.technique}
                    row={row}
                    data={data}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </ul>
          </section>
        )
      })}
    </div>
  )
}
