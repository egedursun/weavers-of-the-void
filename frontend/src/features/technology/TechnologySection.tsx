import { useState } from 'react'
import { Lock, Trash2, Unlock } from 'lucide-react'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { ForgeCard, Meter } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { type TechLevelView, useNodeTechnology } from './api'
import { FAMILIES, TECHNOLOGY_ICON } from './labels'

const SHOWN = 7
const MAX_LEVEL = 10

function FamilyRow({
  nodeId,
  row,
  blocked,
}: {
  nodeId: number
  row: TechLevelView
  blocked: string | null
}) {
  const named = FAMILIES[row.family]
  const release = useMadeAction(
    'technology:release',
    (_: void) => ({ node_id: nodeId, family: row.family }),
    'The level follows what is known again'
  )
  const strike = useMadeAction(
    'technology:delete',
    (_: void) => ({ node_id: nodeId, family: row.family }),
    'Its own level is struck'
  )
  return (
    <li className='flex min-w-0 flex-col gap-1'>
      <Meter
        label={`${named.label}${row.own ? '' : ' (from its people or world)'}`}
        value={row.level * MAX_LEVEL}
        tone='info'
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={row.held ? Unlock : Lock}
          label={row.held ? 'Release' : 'Not held'}
          busy={why(
            blocked ?? (row.held ? null : 'Only a held level can be released'),
            release.isPending
          )}
          onClick={() => release.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike its own level'
          busy={why(
            blocked ?? (row.own ? null : 'It has no level of its own here'),
            strike.isPending
          )}
          onClick={() => strike.mutate()}
        />
      </div>
    </li>
  )
}

export function TechnologySection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeTechnology(nodeId)
  const rows = useShowMore(query.data?.families ?? [], SHOWN, SHOWN)
  const [family, setFamily] = useState<string>('agriculture')
  const [level, setLevel] = useState('3')
  const setting = useMadeAction(
    'technology:set',
    (_: void) => ({
      node_id: nodeId,
      family: family as TechLevelView['family'],
      level: Math.min(MAX_LEVEL, Math.max(0, Number(level) || 0)),
      hold: true,
    }),
    'The level of technology is set and held'
  )
  const blocked = readOnlyReason
  return (
    <Section
      id='section-technology'
      title='Technology: how far it has come in each family'
      description='Each family of technology has its own level from 0 to 10, so a people can be far along in medicine and early in war; peoples move each family by what they know, and a world keeps the levels it was made with.'
      icon={TECHNOLOGY_ICON}
      tone='info'
    >
      <div
        data-surface='TechnologySection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its technology' />
        ) : query.isError ? (
          <EmptyState
            icon={TECHNOLOGY_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <ul className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
              {rows.visible.map((row) => (
                <FamilyRow
                  key={row.family}
                  nodeId={nodeId}
                  row={row}
                  blocked={blocked}
                />
              ))}
            </ul>
            <ShowMore state={rows} />
            <ForgeCard
              icon={TECHNOLOGY_ICON}
              tone='info'
              title='Set a level and hold it'
              note='A held level stays as you set it until you release it.'
              columns={2}
              action={
                <StepButton
                  icon={Lock}
                  label='Set and hold'
                  variant='default'
                  busy={why(blocked, setting.isPending)}
                  onClick={() => setting.mutate()}
                />
              }
            >
              <ChoiceField
                label='Family of technology'
                value={family}
                table={FAMILIES}
                blocked={blocked}
                onPick={setFamily}
              />
              <NumberField
                label='Level'
                value={level}
                min={0}
                max={MAX_LEVEL}
                onChange={setLevel}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
