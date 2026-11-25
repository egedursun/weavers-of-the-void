import { useId, useState } from 'react'
import { Merge, ShieldAlert, Undo2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { entityTypeValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { ConfirmDialog, FormRow, FieldTile } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { type EntityContext } from '../actions/context'
import { optionsFor } from '../actions/pickers'
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
    writes: [{ lever: 'canon:set' }],
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
    writes: [{ lever: 'record:merge' }],
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
        <Button
          act={[canon, merge]}
          variant='ghost'
          className='self-start text-destructive'
        >
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
              act={canon}
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
              act={canon}
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
            {`If two records are truly the same, the chosen ${wordOf(entityTypeValues, ctx.type).toLowerCase()} gives its bonds, contents, lexicon and images to ${entity.name} and is marked merged. This cannot be taken back.`}
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
                placeholder={`Choose a ${wordOf(entityTypeValues, ctx.type).toLowerCase()}`}
                emptyText='No such record of the same kind.'
                aria-label='Record to merge'
              />
            )}
          </FormRow>
          <Button
            act={merge}
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
        act={canon}
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
        act={merge}
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
        <FieldTile id={wordId} label={`Type ${MERGE_WORD} to confirm`}>
          <Input
            id={wordId}
            value={typed}
            autoComplete='off'
            onChange={(event) => setTyped(event.target.value)}
          />
          <Muted variant='caption'>This cannot be taken back.</Muted>
        </FieldTile>
      </ConfirmDialog>
    </Collapsible>
  )
}
