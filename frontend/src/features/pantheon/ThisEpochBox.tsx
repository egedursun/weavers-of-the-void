import { type ReactNode, useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Bell,
  EyeOff,
  HandHeart,
  Hourglass,
  type LucideIcon,
  NotebookPen,
  Play,
  Sparkles,
  TriangleAlert,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { storedItem, storeItem, universeKey } from '@/lib/universeStorage'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import {
  type KpiTone,
  Medallion,
  PagedList,
  ServerLineList,
} from '@/components/domain'
import { Label, SectionTitle, Text } from '@/components/typography'
import { RevelationDialog } from '@/features/creator/RevelationDialog'
import { AwakenPeoplesControl } from './AwakenPeoplesControl'
import { OpportunityList } from './OpportunityList'
import { type WorldState, useCreatorHintLines, useOpportunities } from './api'
import { OPPORTUNITIES_HIDDEN_KEY } from './constants'
import { useRuleLookup } from './gate'
import { opportunitiesOf, withoutServerPhrased } from './opportunities'

function hiddenEpoch(): number {
  try {
    return Number(storedItem(universeKey(OPPORTUNITIES_HIDDEN_KEY)) ?? 0)
  } catch {
    return 0
  }
}

function storeHidden(epoch: number) {
  try {
    storeItem(universeKey(OPPORTUNITIES_HIDDEN_KEY), String(epoch))
  } catch {
    return
  }
}

function TodoRow({
  icon,
  tone,
  children,
  action,
}: {
  icon: LucideIcon
  tone: KpiTone
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <li className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <Medallion icon={icon} tone={tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>{children}</div>
      {action}
    </li>
  )
}

export function ThisEpochBox({ state }: { state: WorldState }) {
  const epoch = state.world?.epoch ?? 0
  const [hidden, setHidden] = useState(
    () => hiddenEpoch() === epoch && epoch > 0
  )
  const hints = useOpportunities()
  const creatorLines = useCreatorHintLines()
  const rule = useRuleLookup()
  const essence = state.creator?.essence ?? 0
  const local = hints.data
    ? opportunitiesOf(hints.data, rule('opportunities.rich_essence'))
    : []
  const items = creatorLines.data ? withoutServerPhrased(local) : local
  const serverLines = (creatorLines.data?.lines ?? []).map((line) => ({
    key: line.kind,
    text: line.text,
  }))
  const spends = [
    ['reveal', rule('costs.revelation')],
    ['summon a son', rule('costs.summon_son')],
    ['convene the council', rule('balance.council')],
    ['awaken peoples', rule('balance.awaken_peoples')],
  ] as const
  const known = spends.filter(([, cost]) => cost !== undefined)
  const affordable = known.filter(
    ([, cost]) => cost !== undefined && cost <= essence
  )
  const waiting = state.pending_son_ids.length
  if (hidden)
    return (
      <Button
        variant='outline'
        className='self-start'
        onClick={() => {
          storeHidden(0)
          setHidden(false)
        }}
      >
        <Play />
        {`This epoch: to-dos and opportunities (${items.length + serverLines.length})`}
      </Button>
    )
  return (
    <Card data-epoch-box>
      <CardHeader>
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
          <div className='flex min-w-0 flex-col gap-0.5'>
            <SectionTitle>{`Epoch ${epoch}`}</SectionTitle>
            <Label>To-dos and what you can do this epoch</Label>
          </div>
          <Button
            variant='ghost'
            size='sm'
            onClick={() => {
              storeHidden(epoch)
              setHidden(true)
            }}
          >
            <EyeOff />
            Hide for this epoch
          </Button>
        </div>
      </CardHeader>
      <CardContent className='grid min-w-0 grid-cols-1 gap-6 lg:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-3'>
          <Label variant='overline'>To do</Label>
          <ul className='flex min-w-0 flex-col gap-2'>
            {state.prayers_pending > 0 && (
              <TodoRow
                icon={HandHeart}
                tone='gold'
                action={
                  <Button variant='outline' size='sm' asChild>
                    <Link to='/prayers'>Answer</Link>
                  </Button>
                }
              >
                <Text>{`${plural(state.prayers_pending, 'prayer')} ${state.prayers_pending === 1 ? 'awaits' : 'await'} an answer.`}</Text>
              </TodoRow>
            )}
            {state.half_epoch?.started ? (
              <TodoRow
                icon={TriangleAlert}
                tone='warning'
                action={
                  <Button variant='outline' size='sm' asChild>
                    <Link to='/epoch'>Resume</Link>
                  </Button>
                }
              >
                <Text>{`Epoch ${state.half_epoch.epoch} was interrupted; it can be completed from where it stopped.`}</Text>
              </TodoRow>
            ) : waiting > 0 ? (
              <TodoRow icon={Hourglass} tone='info'>
                <Text>{`${plural(waiting, 'son')} ${waiting === 1 ? 'has' : 'have'} not acted this epoch yet. Open their cards, give orders, then complete the epoch.`}</Text>
              </TodoRow>
            ) : null}
            <TodoRow icon={Sparkles} tone='verdigris'>
              <Text>
                {affordable.length > 0
                  ? `${formatInteger(essence)} essence to spend`
                  : known.length > 0
                    ? `${formatInteger(essence)} essence; nothing affordable for now, it refills at the end of the epoch.`
                    : `${formatInteger(essence)} essence at hand.`}
              </Text>
              {known.length > 0 && (
                <PagedList
                  items={known}
                  initial={12}
                  noun={['entry', 'entries']}
                  as='div'
                  className='flex min-w-0 flex-wrap gap-1.5'
                  itemKey={([name]) => name}
                >
                  {([name, cost]) => (
                    <Badge
                      key={name}
                      size='sm'
                      variant={
                        cost !== undefined && cost <= essence
                          ? 'success'
                          : 'outline'
                      }
                    >
                      {`${name} · ${cost}`}
                    </Badge>
                  )}
                </PagedList>
              )}
            </TodoRow>
            {state.notifications_unread > 0 && (
              <TodoRow
                icon={Bell}
                tone='info'
                action={
                  <Button variant='outline' size='sm' asChild>
                    <Link to='/notifications'>Read</Link>
                  </Button>
                }
              >
                <Text>{`${plural(state.notifications_unread, 'unread notification')}.`}</Text>
              </TodoRow>
            )}
          </ul>
          <Separator />
          <div className='flex min-w-0 flex-wrap items-start gap-2'>
            <RevelationDialog />
            <Button variant='outline' asChild>
              <Link to='/ledger'>
                <NotebookPen />
                Action ledger
              </Link>
            </Button>
          </div>
          <AwakenPeoplesControl />
        </div>
        <div className='flex min-w-0 flex-col gap-3'>
          <Label variant='overline'>What you can do this epoch</Label>
          {hints.isError ? (
            <Text tone='muted'>
              The opportunity list could not be read right now.
            </Text>
          ) : (
            <>
              <ServerLineList lines={serverLines} emptyText='' />
              <OpportunityList
                items={items}
                quietWhenServerLines={serverLines.length > 0}
              />
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
