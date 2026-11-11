import { Activity, Gauge, Gift, Repeat, Route, Users } from 'lucide-react'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Chip, Meter, RecordRow } from '@/features/cosmography/parts'
import { Ref } from '@/features/gatherings/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { CircuitCard, CircuitForge, GiftCard } from './GiftLedger'
import { ConfederationCard } from './NomadPanel'
import { PlanCard } from './PlanPanel'
import { FrontierMap } from './SolidarityPanel'
import { SecularCycleChart } from './StressPanel'
import { useCosmosCycles } from './api'
import { CYCLES_ICON, PHASES } from './labels'
import { SPAN } from './model'

export function CosmosCyclesSection() {
  const query = useCosmosCycles()
  const { reason } = useGodGate()
  const blocked = reason()
  const data = query.data
  return (
    <Section
      id='section-cosmos-cycles'
      title='The cycles of the realms'
      description='Every realm’s political stress through its secular cycle, the solidarity of every people and realm against its frontiers, the ceremonial circuits and confederations that bind distant communities, every long plan and the whole gift ledger.'
      icon={CYCLES_ICON}
      tone='verdigris'
    >
      <div
        data-surface='CosmosCyclesPanel'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the cycles of every realm' />
        ) : query.isError || !data ? (
          <EmptyState
            icon={CYCLES_ICON}
            size='inline'
            title='This could not be read'
            description={query.error?.message ?? 'No answer came back'}
          />
        ) : (
          <>
            <div className='@container/tiles min-w-0'>
              <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
                <KpiTile
                  label='Realms in crisis'
                  value={
                    data.realms.filter((item) => item.phase === 'crisis').length
                  }
                  icon={Activity}
                  tone='danger'
                />
                <KpiTile
                  label='Long plans'
                  value={data.plans.length}
                  icon={Route}
                  tone='gold'
                />
                <KpiTile
                  label='Gifts on the ledger'
                  value={data.gifts.length}
                  icon={Gift}
                  tone='info'
                />
                <KpiTile
                  label='Confederations'
                  value={data.confederations.length}
                  icon={Users}
                  tone='verdigris'
                />
              </div>
            </div>
            <Label variant='overline'>{`Realms by their stress (${data.realms.length})`}</Label>
            {data.realms.length === 0 ? (
              <Muted variant='caption'>No realm has been read yet.</Muted>
            ) : (
              <PagedList
                items={data.realms}
                initial={3}
                noun={['realm', 'realms']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.polity.id}
              >
                {(item) => {
                  const phase = PHASES[item.phase]
                  return (
                    <RecordRow
                      icon={phase.icon}
                      tone={phase.tone}
                      title={<Ref node={item.polity} />}
                      caption={`${phase.label} · challenge index ${item.challenge}`}
                    >
                      <Meter
                        label='Political stress'
                        value={item.psi}
                        max={SPAN}
                        tone={item.psi >= 55 ? 'destructive' : 'warning'}
                        icon={Gauge}
                      />
                      <SecularCycleChart
                        readings={item.readings}
                        title={`The secular cycle of ${item.polity.name}`}
                      />
                    </RecordRow>
                  )
                }}
              </PagedList>
            )}
            <FrontierMap frontiers={data.frontiers} />
            <Label variant='overline'>{`Ceremonial circuits (${data.circuits.length})`}</Label>
            {data.circuits.length === 0 ? (
              <Muted variant='caption'>No circuit turns yet.</Muted>
            ) : (
              <PagedList
                items={data.circuits}
                initial={3}
                noun={['circuit', 'circuits']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.id}
              >
                {(item) => <CircuitCard row={item} blocked={blocked} />}
              </PagedList>
            )}
            <CircuitForge firstStop={null} blocked={blocked} />
            <Label variant='overline'>{`Confederations (${data.confederations.length})`}</Label>
            {data.confederations.length === 0 ? (
              <Muted variant='caption'>
                No camps have gathered under one leader.
              </Muted>
            ) : (
              <PagedList
                items={data.confederations}
                initial={3}
                noun={['confederation', 'confederations']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.id}
              >
                {(item) => <ConfederationCard row={item} blocked={blocked} />}
              </PagedList>
            )}
            <Label variant='overline'>{`Long plans (${data.plans.length})`}</Label>
            {data.plans.length === 0 ? (
              <Muted variant='caption'>No long plan is under way.</Muted>
            ) : (
              <PagedList
                items={data.plans}
                initial={3}
                noun={['plan', 'plans']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.id}
              >
                {(item) => <PlanCard row={item} blocked={blocked} />}
              </PagedList>
            )}
            <Label variant='overline'>{`The gift ledger (${data.gifts.length})`}</Label>
            {data.gifts.length === 0 ? (
              <Muted variant='caption'>No gift has passed yet.</Muted>
            ) : (
              <PagedList
                items={data.gifts}
                initial={4}
                noun={['gift', 'gifts']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.id}
              >
                {(item) => (
                  <GiftCard nodeId={null} row={item} blocked={blocked} />
                )}
              </PagedList>
            )}
            <Chip icon={Repeat}>
              Gifts given in the world bind their receivers to answer
            </Chip>
          </>
        )}
      </div>
    </Section>
  )
}
