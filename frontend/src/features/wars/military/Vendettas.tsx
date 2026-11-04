import { Flame, HeartCrack, Hourglass, Skull } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EmptyState, EntityLink, MiniStat, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { RecordPanel } from './RecordPanel'
import { FEUD_PARTY, FEUD_STATUS, nameOf, useFeuds } from './depth'
import { Panel, Tag } from './parts'

export function Vendettas({
  entityId,
  blocked,
}: {
  entityId: number | null
  blocked: string | null
}) {
  const query = useFeuds(entityId)
  const feuds = query.data
  if (!feuds) return <Muted variant='caption'>Counting the old grudges…</Muted>
  const burning = feuds.filter((feud) => feud.status === 'active').length
  return (
    <div data-surface='Vendettas' className='flex min-w-0 flex-col gap-3'>
      <Panel
        title='Vendettas'
        icon={Flame}
        tone='danger'
        count={burning}
        hint='Feuds burn hotter with honour and grief, cool with marriages, shared enemies, mediation and the generations'
      >
        {feuds.length === 0 ? (
          <EmptyState
            icon={Flame}
            title='No feuds'
            description='No house or people holds a blood grudge here.'
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-2'>
            {feuds.map((feud) => (
              <div
                key={feud.id}
                className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3'
              >
                <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  {feud.first && (
                    <EntityLink kind='entity' id={String(feud.first.id)}>
                      {feud.first.name}
                    </EntityLink>
                  )}
                  <Text as='span' variant='caption'>
                    against
                  </Text>
                  {feud.second && (
                    <EntityLink kind='entity' id={String(feud.second.id)}>
                      {feud.second.name}
                    </EntityLink>
                  )}
                  <Tag item={nameOf(FEUD_STATUS, feud.status)} />
                  <Tag item={nameOf(FEUD_PARTY, feud.party)} />
                  {feud.locked.length > 0 && (
                    <Badge size='sm' variant='outline'>
                      held
                    </Badge>
                  )}
                </div>
                <StatBar
                  label='Intensity'
                  value={feud.intensity}
                  max={100}
                  icon={Flame}
                  tone={feud.intensity >= 60 ? 'destructive' : 'warning'}
                />
                <StatBar
                  label='Grievance'
                  value={feud.grievance}
                  max={100}
                  icon={HeartCrack}
                  tone='warning'
                />
                <div className='grid min-w-0 grid-cols-2 gap-2 @lg/mil:grid-cols-3'>
                  <MiniStat
                    icon={Hourglass}
                    label='Generations'
                    value={feud.generations}
                    tone='info'
                  />
                  <MiniStat
                    icon={Skull}
                    label='Remembered grief'
                    value={feud.grief}
                    tone='danger'
                  />
                  <MiniStat
                    icon={Flame}
                    label='Since epoch'
                    value={feud.since_epoch}
                    tone='muted'
                  />
                </div>
                {(feud.cause || feud.last_action) && (
                  <Muted variant='caption'>
                    {feud.cause}
                    {feud.last_action
                      ? ` · last: ${feud.last_action.replaceAll('_', ' ')} in epoch ${feud.last_epoch}`
                      : ''}
                  </Muted>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>
      <RecordPanel
        kind='feud'
        scope={entityId}
        title='Feud records'
        tone='danger'
        blocked={blocked}
        choices={{ status: FEUD_STATUS, party: FEUD_PARTY }}
        hint='Start, stoke, hold or end a feud'
      />
    </div>
  )
}
