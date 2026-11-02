import { useState } from 'react'
import { Check, Gavel, Hourglass, X } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { EmptyState, EntityLink, Medallion, Section } from '@/components/domain'
import { SettingRow } from '@/components/domain/SettingsKit'
import { Label, Muted, Text } from '@/components/typography'
import { fixedCost } from '@/features/entity/actions/gate'
import { CostBadge } from '@/features/pantheon/ActionButton'
import { NamePicker } from '@/features/pantheon/NamePicker'
import { useCostText, useGodGate } from '@/features/pantheon/gate'
import {
  type OverrideTarget,
  OverrideVerdictDialog,
} from './OverrideVerdictDialog'
import { type LimboRecord, type VerdictChoice } from './api'

type LimboPanelProps = {
  limbo: LimboRecord[]
}

function LimboRow({
  record,
  cost,
  blocked,
  onChoose,
}: {
  record: LimboRecord
  cost: number | undefined
  blocked: string | null
  onChoose: (choice: VerdictChoice) => void
}) {
  return (
    <li
      data-limbo={record.entity_id}
      className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-warning/30 bg-warning/5 p-3'
    >
      <Medallion icon={Hourglass} tone='warning' size='sm' />
      <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
        <Text weight='medium' truncate={2}>
          <EntityLink kind='entity' id={String(record.entity_id)}>
            {record.name}
          </EntityLink>
        </Text>
        <Label
          truncate
        >{`Born in epoch ${formatInteger(record.born_epoch)}`}</Label>
        <Muted variant='caption'>
          {record.rationale ?? 'Fate gave no reason for its doubt.'}
        </Muted>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          variant='outline'
          size='sm'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => onChoose('accept')}
        >
          <Check />
          Accept
          <CostBadge cost={cost} />
        </Button>
        <Button
          variant='destructive'
          size='sm'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => onChoose('reject')}
        >
          <X />
          Reject
          <CostBadge cost={cost} />
        </Button>
      </div>
    </li>
  )
}

function OverruleAnyRecord({
  cost,
  blocked,
  onChoose,
}: {
  cost: number | undefined
  blocked: string | null
  onChoose: (target: OverrideTarget) => void
}) {
  const [picked, setPicked] = useState<{ id: string; name: string } | null>(
    null
  )
  const [choice, setChoice] = useState<VerdictChoice>('reject')
  const reason = blocked ?? (picked === null ? 'Pick a record first.' : null)
  return (
    <SettingRow
      icon={Gavel}
      tone='danger'
      label='Overrule any verdict'
      description='Accept or reject a record Fate has already judged.'
    >
      {(id) => (
        <>
          <div className='min-w-0 flex-1 basis-60'>
            <NamePicker
              id={id}
              value={picked?.id ?? null}
              kinds={['entity']}
              placeholder='Pick a record'
              onChange={(value, entry) =>
                setPicked(
                  value && entry ? { id: value, name: entry.name } : null
                )
              }
            />
          </div>
          <Select
            value={choice}
            onValueChange={(value) => setChoice(value as VerdictChoice)}
          >
            <SelectTrigger aria-label='Verdict' className='w-36'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value='accept'>Accept</SelectItem>
              <SelectItem value='reject'>Reject</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant='outline'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() =>
              picked &&
              onChoose({
                entityId: Number(picked.id),
                name: picked.name,
                choice,
              })
            }
          >
            <Gavel />
            Overrule
            <CostBadge cost={cost} />
          </Button>
        </>
      )}
    </SettingRow>
  )
}

export function LimboPanel({ limbo }: LimboPanelProps) {
  const { reason } = useGodGate()
  const costOf = useCostText()
  const [target, setTarget] = useState<OverrideTarget | null>(null)
  const cost = fixedCost(costOf('fate:override_verdict')?.cost) ?? undefined
  const blocked = reason({ cost })
  return (
    <Section
      title='Creations in limbo'
      description='Fate could neither accept nor reject these. Decide yourself, or re-judge them all above.'
      surface='card'
      level={3}
      icon={Hourglass}
      tone='warning'
    >
      {limbo.length === 0 ? (
        <EmptyState
          size='compact'
          icon={Hourglass}
          title='Nothing waits in limbo'
          description='Every creation of the past epochs has a verdict.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          {limbo.map((record) => (
            <LimboRow
              key={record.entity_id}
              record={record}
              cost={cost}
              blocked={blocked}
              onChoose={(choice) =>
                setTarget({
                  entityId: record.entity_id,
                  name: record.name,
                  choice,
                })
              }
            />
          ))}
        </ul>
      )}
      <OverruleAnyRecord cost={cost} blocked={blocked} onChoose={setTarget} />
      <OverrideVerdictDialog target={target} onClose={() => setTarget(null)} />
    </Section>
  )
}
