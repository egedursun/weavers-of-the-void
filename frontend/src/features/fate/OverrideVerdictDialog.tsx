import { useId, useState } from 'react'
import { formatInteger } from '@/lib/format'
import { Label as FieldLabel } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog } from '@/components/domain'
import { Muted } from '@/components/typography'
import { fixedCost } from '@/features/entity/actions/gate'
import { useCostText, useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type VerdictChoice, fateKeys, overrideVerdict } from './api'

export const RATIONALE_MAX = 400

export type OverrideTarget = {
  entityId: number
  name: string
  choice: VerdictChoice
}

type OverrideVerdictDialogProps = {
  target: OverrideTarget | null
  onClose: () => void
}

export function OverrideVerdictDialog({
  target,
  onClose,
}: OverrideVerdictDialogProps) {
  const fieldId = useId()
  const costOf = useCostText()
  const { reason } = useGodGate()
  const [rationale, setRationale] = useState('')
  const action = useGodAction({
    run: overrideVerdict,
    invalidate: [fateKeys.controls],
    onDone: () => {
      setRationale('')
      onClose()
    },
  })
  const cost = fixedCost(costOf('fate:override_verdict')?.cost)
  const blocked = reason({ cost: cost ?? undefined })
  const accept = target?.choice === 'accept'
  const costLine =
    cost !== null && cost > 0
      ? ` Overruling Fate costs ${formatInteger(cost)} essence.`
      : ''
  return (
    <ConfirmDialog
      open={target !== null}
      onOpenChange={(open) => {
        if (!open) {
          setRationale('')
          onClose()
        }
      }}
      title={
        target
          ? accept
            ? `Accept ${target.name} into the canon?`
            : `Reject ${target.name}?`
          : ''
      }
      desc={`${
        accept
          ? 'Fate’s doubt is set aside and the record stays in the canon for good.'
          : 'The record leaves the canon and everything it brought is rolled back.'
      }${costLine}`}
      destructive={!accept}
      confirmText={accept ? 'Accept' : 'Reject'}
      disabled={blocked !== null}
      isLoading={action.isPending}
      handleConfirm={() =>
        target &&
        action.mutate({
          entityId: target.entityId,
          choice: target.choice,
          rationale,
        })
      }
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <FieldLabel htmlFor={fieldId}>Your reason</FieldLabel>
        <Textarea
          id={fieldId}
          value={rationale}
          maxLength={RATIONALE_MAX}
          placeholder='Overruled by the Creator.'
          onChange={(event) => setRationale(event.target.value)}
        />
        <Muted variant='caption'>
          {blocked ??
            'Kept with the verdict. Leave it empty and the Creator simply overrules.'}
        </Muted>
      </div>
    </ConfirmDialog>
  )
}
