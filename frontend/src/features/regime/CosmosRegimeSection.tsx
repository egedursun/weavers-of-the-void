import { Crown, GraduationCap, Library, Swords } from 'lucide-react'
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
import { useCosmosRegime } from './api'
import {
  LEADERSHIP,
  LEGITIMACY_KINDS,
  REGIME_ICON,
  ROUTINISATION,
  SELECTORATES,
  STANCES,
} from './labels'

const SHOWN = 6

export function CosmosRegimeSection() {
  const query = useCosmosRegime()
  const { reason } = useGodGate()
  const blocked = reason()
  const data = query.data
  return (
    <Section
      id='section-cosmos-regime'
      title='How the realms are ruled and taught'
      description='Who chooses every ruler and how much goes to public goods, the great subjects who threaten their thrones, the freedom of every house of learning, the schools of thought and the latest examinations.'
      icon={REGIME_ICON}
      tone='gold'
    >
      <div
        data-surface='CosmosRegimePanel'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading how every realm is ruled' />
        ) : query.isError || !data ? (
          <EmptyState
            icon={REGIME_ICON}
            size='inline'
            title='This could not be read'
            description={query.error?.message ?? ''}
          />
        ) : (
          <>
            {blocked && <Muted variant='caption'>{blocked}</Muted>}
            <div className='@container/tiles min-w-0'>
              <div className='grid min-w-0 grid-cols-2 gap-2 @xl/tiles:grid-cols-4'>
                <KpiTile
                  label='Realms read'
                  value={data.realms.length}
                  icon={Crown}
                  tone='gold'
                />
                <KpiTile
                  label='Great subjects'
                  value={data.bases.length}
                  icon={Swords}
                  tone='danger'
                />
                <KpiTile
                  label='Houses of learning'
                  value={data.freedoms.length}
                  icon={Library}
                  tone='info'
                />
                <KpiTile
                  label='Schools of thought'
                  value={data.schools.length}
                  icon={GraduationCap}
                  tone='verdigris'
                />
              </div>
            </div>
            <Label variant='overline'>{`Realms by their rule (${data.realms.length})`}</Label>
            {data.realms.length === 0 ? (
              <Muted variant='caption'>
                No realm's rule has been read yet.
              </Muted>
            ) : (
              <PagedList
                items={data.realms}
                initial={SHOWN}
                noun={['realm', 'realms']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.polity.id}
              >
                {(item) => {
                  const selectorate = SELECTORATES[item.selectorate]
                  return (
                    <RecordRow
                      icon={selectorate.icon}
                      tone={selectorate.tone}
                      title={<Ref node={item.polity} />}
                      caption={`Chosen by ${selectorate.label.toLowerCase()}: ${item.coalition_size} of ${item.selectorate_size} in the winning circle`}
                    >
                      <div className='flex min-w-0 flex-wrap gap-2'>
                        <Chip icon={LEGITIMACY_KINDS[item.dominant].icon}>
                          {LEGITIMACY_KINDS[item.dominant].label}
                        </Chip>
                        <Chip icon={ROUTINISATION[item.routinisation].icon}>
                          {ROUTINISATION[item.routinisation].label}
                        </Chip>
                        <Chip icon={LEADERSHIP[item.leadership].icon}>
                          {LEADERSHIP[item.leadership].label}
                        </Chip>
                      </div>
                      <Meter
                        label='Spent on public goods'
                        value={item.public_share}
                        tone='success'
                      />
                      <Meter
                        label='Time horizon'
                        value={item.horizon}
                        tone='info'
                      />
                    </RecordRow>
                  )
                }}
              </PagedList>
            )}
            <Label variant='overline'>{`Great subjects by their threat (${data.bases.length})`}</Label>
            {data.bases.length === 0 ? (
              <Muted variant='caption'>
                No great subject has been weighed yet.
              </Muted>
            ) : (
              <PagedList
                items={data.bases}
                initial={SHOWN}
                noun={['subject', 'subjects']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.mortal.id}
              >
                {(item) => (
                  <RecordRow
                    icon={STANCES[item.stance].icon}
                    tone={STANCES[item.stance].tone}
                    title={<Ref node={item.mortal} />}
                    caption={`${STANCES[item.stance].label} in ${item.polity?.name ?? 'no realm'} · a power base of ${item.total}`}
                  >
                    <Meter
                      label='Threat to the throne'
                      value={item.threat}
                      tone='destructive'
                    />
                  </RecordRow>
                )}
              </PagedList>
            )}
            <Label variant='overline'>{`Houses of learning by their freedom (${data.freedoms.length})`}</Label>
            {data.freedoms.length === 0 ? (
              <Muted variant='caption'>
                No house of learning has been read yet.
              </Muted>
            ) : (
              <PagedList
                items={data.freedoms}
                initial={SHOWN}
                noun={['house', 'houses']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.structure.id}
              >
                {(item) => (
                  <RecordRow
                    icon={Library}
                    tone={item.suppressed ? 'danger' : 'success'}
                    title={<Ref node={item.structure} />}
                    caption={item.suppressed ? 'Suppressed' : 'Free'}
                  >
                    <Meter
                      label='Freedom of learning'
                      value={item.level}
                      tone={item.suppressed ? 'destructive' : 'success'}
                    />
                  </RecordRow>
                )}
              </PagedList>
            )}
            <Label variant='overline'>{`Schools of thought (${data.schools.length})`}</Label>
            {data.schools.length === 0 ? (
              <Muted variant='caption'>
                No school of thought has gathered yet.
              </Muted>
            ) : (
              <PagedList
                items={data.schools}
                initial={SHOWN}
                noun={['school', 'schools']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.id}
              >
                {(item) => (
                  <RecordRow
                    icon={GraduationCap}
                    tone={item.persecuted ? 'danger' : 'gold'}
                    title={item.name}
                    caption={`${item.disciples.length} in the line${item.founder ? `, founded by ${item.founder.name}` : ''}${item.rival ? `, rival of the ${item.rival.name}` : ''}`}
                  />
                )}
              </PagedList>
            )}
            <Label variant='overline'>{`Latest examinations (${data.sittings.length})`}</Label>
            {data.sittings.length === 0 ? (
              <Muted variant='caption'>
                No realm has held examinations yet.
              </Muted>
            ) : (
              <PagedList
                items={data.sittings}
                initial={SHOWN}
                noun={['sitting', 'sittings']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(item) => item.id}
              >
                {(item) => (
                  <RecordRow
                    icon={GraduationCap}
                    tone='info'
                    title={<Ref node={item.polity} />}
                    caption={`Epoch ${item.epoch}: ${item.passed} of ${item.candidates} passed at the mark of ${item.mark}`}
                  />
                )}
              </PagedList>
            )}
          </>
        )}
      </div>
    </Section>
  )
}
