import { useId, useState } from 'react'
import { REASON_MAX, giveReason } from '@/api/actReason'
import { type ActProp, refusalOf } from '@/api/mutation'
import { cn } from '@/lib/utils'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Muted } from '@/components/typography'
import { FieldTile } from './FieldTile'

type ConfirmDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: React.ReactNode
  disabled?: boolean
  desc: React.JSX.Element | string
  cancelBtnText?: string
  confirmText?: React.ReactNode
  destructive?: boolean
  isLoading?: boolean
  className?: string
  children?: React.ReactNode
  act?: ActProp
} & (
  | { form: string; handleConfirm?: undefined }
  | { form?: undefined; handleConfirm: () => void }
)

function ReasonField({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <div data-slot='act-reason' className='flex min-w-0 flex-col gap-1.5'>
      <FieldTile id={id} label='Why (optional)'>
        <Textarea
          id={id}
          value={value}
          maxLength={REASON_MAX}
          rows={2}
          onChange={(event) => onChange(event.target.value)}
        />
      </FieldTile>
      <Muted variant='caption'>
        {`Kept in the ledger beside your name. ${value.length}/${REASON_MAX}`}
      </Muted>
    </div>
  )
}

export function ConfirmDialog(props: ConfirmDialogProps) {
  const {
    title,
    desc,
    children,
    className,
    confirmText,
    cancelBtnText,
    destructive,
    isLoading,
    disabled = false,
    form,
    handleConfirm,
    act,
    ...actions
  } = props
  const [reason, setReason] = useState('')
  const asks = act !== undefined && act !== null && refusalOf(act) === null
  return (
    <AlertDialog {...actions}>
      <AlertDialogContent className={cn(className && className)}>
        <AlertDialogHeader className='text-start'>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div>{desc}</div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        {children}
        {asks && <ReasonField value={reason} onChange={setReason} />}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>
            {cancelBtnText ?? 'Cancel'}
          </AlertDialogCancel>
          <Button
            type={form ? 'submit' : 'button'}
            form={form}
            act={act}
            onClick={() => {
              if (asks) giveReason(reason)
              handleConfirm?.()
            }}
            variant={destructive ? 'destructive' : 'default'}
            disabled={disabled || isLoading}
          >
            {confirmText ?? 'Continue'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
