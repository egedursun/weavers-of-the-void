import { useState } from 'react'
import { Landmark, UserCheck, UserMinus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, PagedList } from '@/components/domain'
import { Label } from '@/components/typography'
import {
  Chip,
  Facts,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { GOD_KINDS, why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { Ref } from '@/features/gatherings/parts'
import { type OfficeView, useArcanaAction, useCosmicOffices } from './api'
import { OFFICES, OFFICE_CHOICES, table } from './labels'

type Values = Record<string, number | string | boolean | null>

function OfficeCard({
  office,
  holderId,
  blocked,
}: {
  office: OfficeView
  holderId: number
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(holderId)
  const appoint = useArcanaAction(
    'cosmic_office:appoint',
    (_: void) => ({ office: office.office, holder_id: holder ?? 0 }),
    'The office is given'
  )
  const edit = useArcanaAction(
    'cosmic_office:edit',
    (vars: { values: Values; release: string[] }) => ({
      office: office.office,
      ...vars,
    }),
    'The office is set'
  )
  const vacate = useArcanaAction(
    'cosmic_office:vacate',
    (_: void) => ({ office: office.office }),
    'The office stands empty'
  )
  const busy = why(blocked, appoint.isPending, edit.isPending, vacate.isPending)
  const spec = OFFICES[office.office]
  const choice = OFFICE_CHOICES[office.chosen_by]
  return (
    <RecordRow
      icon={spec.icon}
      tone={office.holder ? spec.tone : 'muted'}
      title={spec.label}
      caption={
        office.holder
          ? `${choice.label}${office.since_epoch !== null ? ` in epoch ${office.since_epoch}` : ''}`
          : 'Empty and neglected'
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null || office.holder === null}
          disabledReason={
            busy ?? (office.holder === null ? 'No one holds it' : undefined)
          }
          onClick={() => vacate.mutate()}
        >
          <UserMinus />
          Empty it
        </Button>
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <Meter label='Duty fulfilled' value={office.duty} tone='success' />
        <Meter label='Neglect' value={office.neglect} tone='destructive' />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={choice.icon}>{choice.label}</Chip>
      </div>
      <Facts
        items={[
          ['Holder', <Ref key='holder' node={office.holder} empty='no god' />],
        ]}
      />
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Give it to'
          value={holder}
          onChange={setHolder}
          blocked={busy}
          kinds={GOD_KINDS}
        />
        <Button
          size='sm'
          disabled={busy !== null || holder === null}
          disabledReason={
            busy ?? (holder === null ? 'Choose a god first' : undefined)
          }
          onClick={() => appoint.mutate()}
        >
          <UserCheck />
          Appoint
        </Button>
      </div>
      <RecordEditor
        title='Reshape the office'
        note='Neglect weakens the rites of the office and brings its world effects; duty keeps them at bay.'
        fields={[
          {
            key: 'chosen_by',
            label: 'How it was given',
            kind: 'pick',
            table: table(OFFICE_CHOICES),
          },
          {
            key: 'since_epoch',
            label: 'Held since epoch',
            kind: 'number',
            min: 0,
          },
          {
            key: 'neglect',
            label: 'Neglect',
            kind: 'number',
            min: 0,
            max: 100,
          },
          { key: 'duty', label: 'Duty', kind: 'number', min: 0, max: 100 },
        ]}
        locked={office.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

export function CosmicOfficesPanel({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const query = useCosmicOffices()
  return (
    <div
      data-surface='CosmicOfficesPanel'
      className='flex min-w-0 flex-col gap-2'
    >
      <Label variant='overline'>Cosmic offices</Label>
      {query.isPending ? (
        <LoadingBlock label='Reading the offices' />
      ) : query.isError ? (
        <EmptyState
          icon={Landmark}
          size='inline'
          title='The offices could not be read'
          description={query.error.message}
        />
      ) : (
        <PagedList
          items={query.data}
          initial={3}
          noun={['office', 'offices']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.office}
        >
          {(row) => (
            <OfficeCard office={row} holderId={holderId} blocked={blocked} />
          )}
        </PagedList>
      )}
    </div>
  )
}
