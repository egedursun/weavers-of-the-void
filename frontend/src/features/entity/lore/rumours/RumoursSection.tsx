import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  Ear,
  Flame,
  Lock,
  Megaphone,
  MessageSquareOff,
  MessagesSquare,
  Send,
  Shield,
  Unlock,
  Waypoints,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  KpiTile,
  Section,
  StatBar,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../../api/keys'
import { AdjustBlock, AdjustPanel, NamedChip, Who } from '../LoreFields'
import { KPI_GRID, PERCENT, busyOf } from '../model'
import { RumourTellings } from './RumourTellings'
import {
  CHANNELS,
  type Rumour,
  averageTruth,
  clampTruth,
  truthBar,
  truthTone,
  truthWord,
} from './rumourModel'

const COMMUNITIES = [
  'settlement',
  'people',
  'cult',
  'faction',
  'polity',
] as const
const SUBJECTS = [...COMMUNITIES, 'mortal', 'army'] as const
const DEFAULT_TRUTH = 80

const rumourKeys = {
  board: (id: number) => [...loreKeys.entity(id), 'rumours'] as const,
}

function useRumours(id: number) {
  return useQuery({
    queryKey: rumourKeys.board(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/rumours', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

function RumourCard({
  communityId,
  rumour,
  blocked,
}: {
  communityId: number
  rumour: Rumour
  blocked: string | null
}) {
  const [truth, setTruth] = useState(String(rumour.fidelity))
  const [elsewhere, setElsewhere] = useState<number | null>(null)
  const invalidate = [rumourKeys.board(communityId)]
  const edit = useGodAction<{ fidelity: number | null; release: boolean }>({
    run: ({ fidelity, release }) =>
      unwrap(
        api.POST('/api/actions/rumour:edit', {
          body: { rumour_id: rumour.id, fidelity, release },
        })
      ),
    invalidate,
  })
  const silence = useGodAction<boolean>({
    run: (everywhere) =>
      unwrap(
        api.POST('/api/actions/rumour:suppress', {
          body: { rumour_id: rumour.id, everywhere },
        })
      ),
    invalidate,
  })
  const pass = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rumour:plant', {
          body: {
            community_id: elsewhere ?? 0,
            incident_id: rumour.incident_id,
            fidelity: rumour.fidelity,
            text: '',
            atrocity: false,
          },
        })
      ),
    invalidate,
  })
  const busy = busyOf(
    blocked,
    edit.isPending,
    silence.isPending,
    pass.isPending
  )
  const channel = CHANNELS[rumour.channel]
  const held = rumour.locked.includes('fidelity')
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <NamedChip spec={channel} />
        {rumour.atrocity && (
          <Badge variant='destructive'>
            <Flame aria-hidden='true' />
            An atrocity
          </Badge>
        )}
        {rumour.alarm && (
          <Badge variant='outline'>
            <Shield aria-hidden='true' />
            War news
          </Badge>
        )}
        {rumour.planted && (
          <Badge variant='outline'>
            <Megaphone aria-hidden='true' />
            Whispered
          </Badge>
        )}
        {held && (
          <Badge variant='default'>
            <Lock aria-hidden='true' />
            Held
          </Badge>
        )}
      </div>
      <Text>{rumour.text}</Text>
      <RumourTellings
        rumourId={rumour.id}
        distortions={rumour.distortions ?? []}
        blocked={blocked}
        invalidate={invalidate}
      />
      <StatBar
        label={`${truthWord(rumour.fidelity)} (${rumour.fidelity}%)`}
        value={rumour.fidelity}
        max={PERCENT}
        tone={truthBar(rumour.fidelity)}
      />
      <div className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1'>
        <Muted variant='caption'>{`Happened in age ${rumour.happened_epoch}, heard in age ${rumour.heard_epoch}${rumour.lingered > 0 ? `, told for ${rumour.lingered} ${rumour.lingered === 1 ? 'age' : 'ages'}` : ''}`}</Muted>
        <Muted variant='caption'>{`${plural(rumour.hops, 'telling', 'tellings')} away`}</Muted>
        <Muted variant='caption'>{`${plural(rumour.carriers, 'community', 'communities')} speak of it`}</Muted>
        {rumour.source && (
          <Muted variant='caption'>
            {'From '}
            <Who item={rumour.source} />
          </Muted>
        )}
        {rumour.legend && (
          <span className='flex items-center gap-1'>
            <BookOpen aria-hidden='true' className='size-icon-xs' />
            <Muted variant='caption'>
              {'Now a legend: '}
              <Who item={rumour.legend} />
            </Muted>
          </span>
        )}
      </div>
      <AdjustPanel
        surface='RumourAdjust'
        title='Shape this rumour'
        note='Set how true it runs and hold it there, let it fade again, carry it to another people, or silence it.'
      >
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
          <AdjustBlock title='How true it runs' icon={Ear}>
            <div className='flex min-w-0 flex-wrap items-end gap-2'>
              <div className='flex min-w-0 flex-col gap-1'>
                <Label>Truth (0–100)</Label>
                <Input
                  type='number'
                  min={0}
                  max={PERCENT}
                  className='w-24'
                  aria-label='Truth of the rumour'
                  value={truth}
                  onChange={(event) => setTruth(event.target.value)}
                />
              </div>
              <Button
                size='sm'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  edit.mutate({
                    fidelity: clampTruth(Number(truth) || 0),
                    release: false,
                  })
                }
              >
                <Lock />
                Hold it there
              </Button>
              {held && (
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => edit.mutate({ fidelity: null, release: true })}
                >
                  <Unlock />
                  Let it fade
                </Button>
              )}
            </div>
          </AdjustBlock>
          <AdjustBlock title='Carry it elsewhere' icon={Waypoints}>
            <EntityPicker
              types={[...COMMUNITIES]}
              value={elsewhere}
              onChange={setElsewhere}
              placeholder='Choose who should hear it…'
            />
            <Button
              size='sm'
              variant='outline'
              className='self-start'
              disabled={busy !== null || elsewhere === null}
              disabledReason={
                busy ?? (elsewhere === null ? 'Choose who hears it' : undefined)
              }
              onClick={() => pass.mutate()}
            >
              <Send />
              Whisper it there
            </Button>
          </AdjustBlock>
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => silence.mutate(false)}
          >
            <MessageSquareOff />
            Silence it here
          </Button>
          <Button
            size='sm'
            variant='destructive'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => silence.mutate(true)}
          >
            <MessageSquareOff />
            Silence it everywhere
          </Button>
        </div>
      </AdjustPanel>
    </li>
  )
}

function PlantRumour({
  communityId,
  blocked,
}: {
  communityId: number
  blocked: string | null
}) {
  const [subject, setSubject] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [truth, setTruth] = useState(String(DEFAULT_TRUTH))
  const [atrocity, setAtrocity] = useState(false)
  const plant = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rumour:plant', {
          body: {
            community_id: communityId,
            subject_id: subject,
            text: text.trim(),
            fidelity: clampTruth(Number(truth) || 0),
            atrocity,
          },
        })
      ),
    invalidate: [rumourKeys.board(communityId)],
    onDone: () => setText(''),
  })
  const busy = busyOf(
    blocked ??
      (subject === null ? 'Choose whom it is about' : null) ??
      (text.trim() ? null : 'Say what the rumour tells'),
    plant.isPending
  )
  return (
    <AdjustPanel
      surface='PlantRumour'
      title='Whisper a rumour'
      note='Plant a tale of your own among these people. It spreads like any other word, garbling as it goes; a tale of atrocity turns hearts against the one it names.'
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Whom it is about</Label>
          <EntityPicker
            types={[...SUBJECTS]}
            value={subject}
            onChange={setSubject}
            placeholder='Choose the one it names…'
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>How true it runs (0–100)</Label>
          <Input
            type='number'
            min={0}
            max={PERCENT}
            aria-label='Truth of the new rumour'
            value={truth}
            onChange={(event) => setTruth(event.target.value)}
          />
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-1'>
        <Label>What it tells</Label>
        <Textarea
          aria-label='What the rumour tells'
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
      </div>
      <label className='flex min-w-0 items-center gap-2'>
        <Switch
          checked={atrocity}
          aria-label='A tale of atrocity'
          onCheckedChange={setAtrocity}
        />
        <Text as='span'>A tale of atrocity</Text>
      </label>
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => plant.mutate()}
      >
        <Megaphone />
        Whisper it
      </Button>
    </AdjustPanel>
  )
}

export function RumoursSection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const board = useRumours(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const rumours = board.data?.rumours ?? []
  const atrocities = rumours.filter((item) => item.atrocity).length
  const alarms = rumours.filter((item) => item.alarm).length
  const truth = averageTruth(rumours)
  return (
    <Section
      id='section-rumours'
      title='What they have heard'
      description='Word of the world reaches them by road, pilgrimage, traveller and spy, losing truth with every telling.'
      icon={MessagesSquare}
      tone='info'
    >
      <div
        data-surface='RumoursSection'
        className='@container/lore flex min-w-0 flex-col gap-4'
      >
        <div className={KPI_GRID}>
          <KpiTile
            label='Rumours heard'
            value={rumours.length}
            icon={MessagesSquare}
            tone='info'
          />
          <KpiTile
            label='How true, on average'
            value={truth}
            icon={Ear}
            tone={truthTone(truth)}
            meter={{ value: truth, max: PERCENT, label: 'average truth' }}
          />
          <KpiTile
            label='Atrocities heard of'
            value={atrocities}
            icon={Flame}
            tone={atrocities > 0 ? 'danger' : 'muted'}
          />
          <KpiTile
            label='War news'
            value={alarms}
            icon={Shield}
            tone={alarms > 0 ? 'warning' : 'muted'}
          />
        </div>
        {board.isError && (
          <EmptyState
            icon={MessagesSquare}
            title='The talk could not be heard'
            description={board.error.message}
          />
        )}
        {board.isSuccess && rumours.length === 0 && (
          <EmptyState
            icon={Ear}
            title='No word has reached them'
            description='Nothing of note has been heard here yet. Rumours arrive as the world turns, or you can whisper one below.'
          />
        )}
        {rumours.length > 0 && (
          <ul data-surface='RumourList' className='flex min-w-0 flex-col gap-2'>
            <Paged items={rumours} as='li'>
              {(item) => (
                <RumourCard
                  key={item.id}
                  communityId={communityId}
                  rumour={item}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <PlantRumour communityId={communityId} blocked={blocked} />
      </div>
    </Section>
  )
}
