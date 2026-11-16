import { useId, useState } from 'react'
import { Merge, ShieldAlert, Undo2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { ConfirmDialog, FormRow } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { type EntityContext } from '../actions/context'
import { optionsFor } from '../actions/pickers'
import { humanize } from '../actions/schema'
import { usePickerData } from '../actions/usePickerData'
import { useLoreMutation } from '../api/mutations'
import { MERGE_WORD } from '../constants'

export function DangerZone({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  const data = usePickerData()
  const wordId = useId()
  const [confirmCanon, setConfirmCanon] = useState(false)
  const [other, setOther] = useState<number | null>(null)
  const [merging, setMerging] = useState(false)
  const [typed, setTyped] = useState('')
  const entity = ctx.entity
  const rejected = entity.status === 'rejected'
  const canon = useLoreMutation({
    run: (status: 'canon' | 'rejected') =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/canon', {
          params: { path: { entity_id: entity.id } },
          body: { status },
        })
      ),
    success: 'Canon updated',
  })
  const merge = useLoreMutation({
    run: (otherId: number) =>
      unwrap(
        api.POST('/api/entities/{entity_id}/merge', {
          params: { path: { entity_id: entity.id } },
          body: { other_id: otherId, confirm: MERGE_WORD },
        })
      ),
    onDone: () => {
      setOther(null)
      setTyped('')
    },
  })
  const options = optionsFor(
    {
      source: 'entity',
      sameType: true,
      statuses: ['canon', 'dead', 'destroyed', 'rejected'],
    },
    ctx,
    data
  )
  const otherName =
    options.find((option) => option.value === String(other))?.label ??
    'the other record'
  const blocked =
    readOnlyReason ??
    (canon.isPending || merge.isPending ? 'Working on it.' : null)
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-destructive/40 bg-card p-4'>
      <CollapsibleTrigger asChild>
        <Button variant='ghost' className='self-start text-destructive'>
          <ShieldAlert />
          Dangerous operations
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-4'>
        {rejected ? (
          <div className='flex min-w-0 flex-col gap-2'>
            <Text>
              Fate rejected this record. You can break Fate and take it into
              canon.
            </Text>
            <Button
              variant='outline'
              className='self-start'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => canon.mutate('canon')}
            >
              <Undo2 />
              Break Fate, take into canon
            </Button>
          </div>
        ) : (
          <div className='flex min-w-0 flex-col gap-2'>
            <Text>
              Strike it from canon: it is hidden as if Fate had rejected it.
            </Text>
            <Button
              variant='destructive'
              className='self-start'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => setConfirmCanon(true)}
            >
              <ShieldAlert />
              Delete from canon
            </Button>
          </div>
        )}
        <div className='flex min-w-0 flex-col gap-3'>
          <Text>
            {`If two records are truly the same, the chosen ${humanize(ctx.type).toLowerCase()} gives its bonds, contents, lexicon and images to ${entity.name} and is marked merged. This cannot be taken back.`}
          </Text>
          <FormRow label='Merge into this'>
            {(id) => (
              <RecordCombobox
                id={id}
                options={options}
                value={other === null ? null : String(other)}
                onChange={(value) =>
                  setOther(value === null ? null : Number(value))
                }
                placeholder={`Choose a ${humanize(ctx.type).toLowerCase()}`}
                emptyText='No such record of the same kind.'
                aria-label='Record to merge'
              />
            )}
          </FormRow>
          <Button
            variant='destructive'
            className='self-start'
            disabled={blocked !== null || other === null}
            disabledReason={blocked ?? 'Choose the record to merge first.'}
            onClick={() => {
              setTyped('')
              setMerging(true)
            }}
          >
            <Merge />
            Merge
          </Button>
        </div>
      </CollapsibleContent>
      <ConfirmDialog
        open={confirmCanon}
        onOpenChange={setConfirmCanon}
        title={`Delete ${entity.name} from canon?`}
        desc='Agents will treat it as if it never happened. You can restore it later from here.'
        destructive
        confirmText='Delete from canon'
        isLoading={canon.isPending}
        handleConfirm={() => {
          setConfirmCanon(false)
          canon.mutate('rejected')
        }}
      />
      <ConfirmDialog
        open={merging}
        onOpenChange={setMerging}
        title={`Merge ${otherName} into ${entity.name}?`}
        desc='Everything it holds moves here. This cannot be taken back.'
        destructive
        confirmText='Merge'
        disabled={typed.trim() !== MERGE_WORD}
        isLoading={merge.isPending}
        handleConfirm={() => {
          setMerging(false)
          if (other !== null) merge.mutate(other)
        }}
      >
        <div className='flex min-w-0 flex-col gap-2'>
          <FieldLabel
            htmlFor={wordId}
          >{`Type ${MERGE_WORD} to confirm`}</FieldLabel>
          <Input
            id={wordId}
            value={typed}
            autoComplete='off'
            onChange={(event) => setTyped(event.target.value)}
          />
          <Muted variant='caption'>This cannot be taken back.</Muted>
        </div>
      </ConfirmDialog>
    </Collapsible>
  )
}
