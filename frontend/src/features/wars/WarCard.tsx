import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  CalendarDays,
  Castle,
  Crosshair,
  Crown,
  Flag,
  Flame,
  Maximize2,
  Shield,
  Swords,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { DivergingBar } from '@/features/pantheon/DivergingBar'
import { ArmiesList, BattlesList, Ref, SiegesList } from './WarsTables'
import { type WarSummary } from './api'

const SCORE_SCALE_MIN = 5

function humanize(value: string): string {
  const text = value.replaceAll('_', ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function SideColumn({
  title,
  sides,
  victorId,
  tone,
}: {
  title: string
  sides: WarSummary['sides']
  victorId: number | null
  tone: 'attacker' | 'defender'
}) {
  return (
    <div
      className={cn(
        'flex min-w-0 flex-1 flex-col gap-2 rounded-lg border p-3',
        tone === 'attacker'
          ? 'border-destructive/30 bg-destructive/5'
          : 'border-info/30 bg-info/5'
      )}
    >
      <Label variant='overline'>{title}</Label>
      {sides.length === 0 ? (
        <Muted variant='caption'>No one stands here.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-1'>
          {sides.map((side) => (
            <li
              key={side.entity?.id ?? side.joined_epoch}
              className='flex min-w-0 items-center gap-1.5'
            >
              {side.entity?.id === victorId ? (
                <Crown
                  aria-label='Victor'
                  className='size-icon-xs shrink-0 text-primary'
                />
              ) : (
                <Shield
                  aria-hidden='true'
                  className={cn(
                    'size-icon-xs shrink-0',
                    tone === 'attacker' ? 'text-destructive' : 'text-info'
                  )}
                />
              )}
              <span className='min-w-0 truncate'>
                <Ref node={side.entity} />
              </span>
              {side.left_epoch !== null && (
                <Muted as='span' variant='caption'>
                  {`left ${side.left_epoch}`}
                </Muted>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function WarCard({
  war,
  focused = false,
}: {
  war: WarSummary
  focused?: boolean
}) {
  const [tab, setTab] = useState('battles')
  const ongoing = war.status !== 'ended'
  const attackers = war.sides.filter((side) => side.side === 'attacker')
  const defenders = war.sides.filter((side) => side.side === 'defender')
  const victorId = war.victor?.id ?? null
  return (
    <article
      data-war={war.id}
      className={cn(
        'flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-5 text-card-foreground',
        ongoing && 'border-destructive/40'
      )}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={ongoing ? Flame : Flag}
          tone={ongoing ? 'danger' : 'muted'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <Text as='span' weight='semibold' truncate>
            <Ref node={war.event} />
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant={ongoing ? 'destructive' : 'outline'}>
              {ongoing ? <Flame /> : <Flag />}
              {humanize(war.status)}
            </Badge>
            <Badge size='sm' variant='outline'>
              {humanize(war.cause)}
            </Badge>
            {war.ending && (
              <Badge size='sm' variant='info'>
                {`Ended in ${war.ending.replaceAll('_', ' ')}`}
              </Badge>
            )}
            <Badge size='sm' variant='outline'>
              <CalendarDays />
              {war.ended_epoch !== null
                ? `Epoch ${war.started_epoch}–${war.ended_epoch}`
                : `Since epoch ${war.started_epoch}`}
            </Badge>
            <Badge size='sm' variant='outline'>
              <Crosshair />
              {`${war.battles} ${war.battles === 1 ? 'battle' : 'battles'}`}
            </Badge>
            {war.violence !== null && (
              <Badge size='sm' variant='warning'>
                <Flame />
                {`Violence ${war.violence}`}
              </Badge>
            )}
          </div>
          {war.cause_text && (
            <Muted variant='caption' truncate={2}>
              {war.cause_text}
            </Muted>
          )}
        </div>
        {!focused && (
          <Button variant='ghost' size='sm' asChild>
            <Link to='/wars' search={{ war: war.id }}>
              <Maximize2 />
              Open
            </Link>
          </Button>
        )}
      </div>
      <div className='flex min-w-0 flex-col items-stretch gap-2 md:flex-row md:items-center'>
        <SideColumn
          title='Attackers'
          sides={attackers}
          victorId={victorId}
          tone='attacker'
        />
        <span className='flex shrink-0 items-center justify-center'>
          <Medallion icon={Swords} tone='gold' size='sm' />
        </span>
        <SideColumn
          title='Defenders'
          sides={defenders}
          victorId={victorId}
          tone='defender'
        />
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Muted variant='caption'>Defenders lead</Muted>
          <Label>{`Momentum ${war.score > 0 ? '+' : ''}${war.score}`}</Label>
          <Muted variant='caption'>Attackers lead</Muted>
        </div>
        <DivergingBar
          value={war.score}
          label='War momentum'
          scale={Math.max(SCORE_SCALE_MIN, Math.abs(war.score))}
        />
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList aria-label='War details'>
          <TabsTrigger value='battles'>
            <Swords />
            Battles
          </TabsTrigger>
          <TabsTrigger value='armies'>
            <Shield />
            Armies
          </TabsTrigger>
          <TabsTrigger value='sieges'>
            <Castle />
            Sieges
          </TabsTrigger>
        </TabsList>
        <TabsContent value='battles'>
          {tab === 'battles' && <BattlesList warId={war.id} />}
        </TabsContent>
        <TabsContent value='armies'>
          {tab === 'armies' && <ArmiesList warId={war.id} />}
        </TabsContent>
        <TabsContent value='sieges'>
          {tab === 'sieges' && <SiegesList warId={war.id} />}
        </TabsContent>
      </Tabs>
    </article>
  )
}
