import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { type ActProp } from '@/api/mutation'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type ActKind,
  type CultureMind,
  type Ethic,
  type EthicalStance,
  type HonourModel,
  useCultureMind,
} from '../mind/api'
import { ETHICS_ICON, HONOUR_ICON, STANCES } from '../mind/cultureLabels'
import { named } from '../mind/labels'
import { ControlPanel, MindCard, MindPicker } from '../mind/parts'

const WORKING = 'Working on it.'
const BY_MODEL = 'by_model'

type DuelEnd = components['schemas']['DuelEnd']

function EthicRow({
  item,
  stances,
  blocked,
  onStance,
  act,
}: {
  item: Ethic
  stances: Record<string, string>
  blocked: string | null
  onStance: (stance: EthicalStance) => void
  act?: ActProp
}) {
  const spec = named(STANCES, item.stance)
  return (
    <div className='flex min-w-0 items-end gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <Medallion icon={spec.icon} size='sm' tone={spec.tone} />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text weight='semibold' truncate>
          {item.label}
        </Text>
        <Muted variant='caption'>{`Since epoch ${item.since_epoch}${item.held ? ' · held' : ''}`}</Muted>
      </div>
      <div className='w-40 min-w-0'>
        <MindPicker
          act={act}
          label='Stance'
          value={item.stance}
          table={stances}
          blocked={blocked}
          onPick={(value) => onStance(value as EthicalStance)}
        />
      </div>
    </div>
  )
}

function Ladder({ view }: { view: CultureMind }) {
  const { reason } = useGodGate()
  const stance = useGodAction({
    writes: [{ lever: 'ethics:set' }],
    run: ({ act, next }: { act: ActKind; next: EthicalStance }) =>
      unwrap(
        api.POST('/api/actions/ethics:set', {
          body: {
            holder_id: view.ethics_holder?.id ?? view.node_id,
            act,
            stance: next,
            hold: true,
          },
        })
      ),
  })
  const honour = useGodAction({
    writes: [{ lever: 'ethics:honour' }],
    run: ({ model, ending }: { model: HonourModel; ending: DuelEnd | null }) =>
      unwrap(
        api.POST('/api/actions/ethics:honour', {
          body: {
            holder_id: view.ethics_holder?.id ?? view.node_id,
            model,
            duel_end: ending,
            hold: true,
          },
        })
      ),
  })
  const blocked =
    reason() ??
    (!view.ethics_own
      ? 'These are the ethics of their people; change them there.'
      : stance.isPending || honour.isPending
        ? WORKING
        : null)
  const stances = Object.fromEntries(
    view.stances.map((item) => [item.key, item.label])
  )
  const models = Object.fromEntries(
    view.honour_models.map((item) => [item.key, item.label])
  )
  const endings: Record<string, string> = {
    [BY_MODEL]: 'As the honour model has it',
    ...Object.fromEntries(view.duel_ends.map((item) => [item.key, item.label])),
  }
  const inForce = view.duel_ends.find(
    (item) => item.key === view.duel_end_in_force
  )
  return (
    <>
      <MindCard
        title='Right and wrong'
        icon={ETHICS_ICON}
        hint='How these people judge each act, from required to unthinkable. Witnesses judge by it, and it sets renown, guilt, a ruler’s legitimacy and the call for harsher laws.'
        wide
      >
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/eth:grid-cols-2'>
          <Paged items={view.ethics} initial={8} noun={['act', 'acts']}>
            {(item) => (
              <EthicRow
                act={stance}
                key={item.act}
                item={item}
                stances={stances}
                blocked={blocked}
                onStance={(next) => stance.mutate({ act: item.act, next })}
              />
            )}
          </Paged>
        </div>
      </MindCard>
      {view.honour_model && (
        <ControlPanel
          title='Honour and shame'
          note='Dignity puts law over insult; honour makes a shame to one a shame to the household that seeks restoration; face makes public shame weigh more than private guilt.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/eth:grid-cols-2'>
            <MindPicker
              act={honour}
              label='Honour model'
              value={view.honour_model}
              table={models}
              blocked={blocked}
              onPick={(value) =>
                honour.mutate({
                  model: value as HonourModel,
                  ending: view.duel_end,
                })
              }
            />
            <div className='flex min-w-0 flex-col justify-end gap-1'>
              <Label>Now</Label>
              <Text>{view.honour_label}</Text>
              {view.honour_held && <Muted variant='caption'>Held by you</Muted>}
            </div>
            <MindPicker
              act={honour}
              label='Duels end'
              value={view.duel_end ?? BY_MODEL}
              table={endings}
              blocked={blocked}
              onPick={(value) =>
                honour.mutate({
                  model: view.honour_model ?? 'dignity',
                  ending: value === BY_MODEL ? null : (value as DuelEnd),
                })
              }
            />
            <div className='flex min-w-0 flex-col justify-end gap-1'>
              <Label>A duel of honour or a ritual duel ends</Label>
              <Text>{inForce?.label ?? 'As the honour model has it'}</Text>
              {view.duel_end_held && (
                <Muted variant='caption'>Held by you</Muted>
              )}
            </div>
          </div>
        </ControlPanel>
      )}
    </>
  )
}

export function EthicsSection({ nodeId }: { nodeId: number }) {
  const query = useCultureMind(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section id='section-ethics' title='Ethics' icon={ETHICS_ICON}>
        <EmptyState
          icon={ETHICS_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view || !view.has_ethics) return null
  const counts = (stances: string[]) =>
    view.ethics.filter((item) => stances.includes(item.stance)).length
  return (
    <Section
      id='section-ethics'
      title='Ethics'
      description='Peoples and cults hold ethics; mortals, settlements and factions live by those of their people. They follow beliefs slowly and can split a people when its notables disagree.'
      icon={ETHICS_ICON}
    >
      <div className='@container/eth flex min-w-0 flex-col gap-4'>
        {!view.ethics_own && view.ethics_holder && (
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Muted variant='caption'>Living by the ethics of</Muted>
            <EntityLink
              kind='entity'
              id={String(view.ethics_holder.id)}
              showIcon
            >
              {view.ethics_holder.name}
            </EntityLink>
          </div>
        )}
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/eth:grid-cols-3'>
          <KpiTile
            label='Held right'
            value={counts(['required', 'admirable'])}
            icon={named(STANCES, 'admirable').icon}
            tone='success'
          />
          <KpiTile
            label='Held wrong'
            value={counts(['shameful', 'unthinkable'])}
            icon={named(STANCES, 'unthinkable').icon}
            tone='danger'
          />
          <KpiTile
            label='Honour model'
            value={view.honour_label ?? 'None'}
            icon={HONOUR_ICON}
            tone='gold'
          />
        </div>
        {view.ethics.length === 0 ? (
          <EmptyState
            icon={ETHICS_ICON}
            title='No ethics yet'
            description='The next epoch reads these people’s ethics from their beliefs.'
          />
        ) : (
          <>
            <PagedList
              items={view.stances}
              initial={12}
              noun={['entry', 'entries']}
              as='div'
              className='flex min-w-0 flex-wrap gap-1.5'
              itemKey={(item) => item.key}
            >
              {(item) => (
                <Badge key={item.key} variant='outline'>
                  {`${item.label}: ${counts([item.key])}`}
                </Badge>
              )}
            </PagedList>
            <Ladder view={view} />
          </>
        )}
      </div>
    </Section>
  )
}
