import { useId, useState } from 'react'
import { type LucideIcon, Sparkles } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button, type ButtonProps } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { ConfirmDialog, RuleInfo } from '@/components/domain'
import { Muted } from '@/components/typography'

export type ConfirmSpec = {
  title: string
  description: string
  word?: string | null
  confirmLabel?: string
}

type ActionButtonProps = {
  label: string
  icon?: LucideIcon
  cost?: number
  gain?: number
  costText?: string
  rule?: string
  blocked?: string | null
  pending?: boolean
  confirm?: ConfirmSpec
  onRun: () => void
  variant?: ButtonProps['variant']
  size?: ButtonProps['size']
  type?: 'button' | 'submit'
}

export function CostBadge({ cost, gain }: { cost?: number; gain?: number }) {
  if (gain !== undefined && gain > 0)
    return (
      <Badge size='sm' variant='success' aria-label={`gain ${gain} essence`}>
        <Sparkles />
        {`+${formatInteger(gain)}`}
      </Badge>
    )
  if (cost === undefined || cost <= 0) return null
  return (
    <Badge size='sm' variant='secondary' aria-label={`costs ${cost} essence`}>
      <Sparkles />
      {formatInteger(cost)}
    </Badge>
  )
}

export function ActionButton({
  label,
  icon: Icon,
  cost,
  gain,
  costText,
  rule,
  blocked,
  pending = false,
  confirm,
  onRun,
  variant = 'outline',
  size = 'default',
  type = 'button',
}: ActionButtonProps) {
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState('')
  const wordId = useId()
  const word = confirm?.word ?? null
  const reason = blocked ?? (pending ? 'Working on it.' : null)
  const start = () => {
    if (confirm) {
      setTyped('')
      setOpen(true)
      return
    }
    onRun()
  }
  const control = (
    <Button
      type={confirm ? 'button' : type}
      variant={variant}
      size={size}
      disabled={reason !== null}
      disabledReason={reason ?? undefined}
      aria-busy={pending || undefined}
      title={costText}
      onClick={type === 'submit' && !confirm ? undefined : start}
    >
      {Icon && <Icon />}
      {label}
      <CostBadge cost={cost} gain={gain} />
    </Button>
  )
  return (
    <>
      {rule ? (
        <span className='inline-flex min-w-0 items-center gap-1'>
          {control}
          <RuleInfo rule={rule} label='The cost' />
        </span>
      ) : (
        control
      )}
      {confirm && (
        <ConfirmDialog
          open={open}
          onOpenChange={setOpen}
          title={confirm.title}
          desc={confirm.description}
          destructive={variant === 'destructive'}
          confirmText={confirm.confirmLabel ?? label}
          disabled={word !== null && typed.trim() !== word}
          isLoading={pending}
          handleConfirm={() => {
            setOpen(false)
            onRun()
          }}
        >
          {word && (
            <div className='flex min-w-0 flex-col gap-2'>
              <FieldLabel
                htmlFor={wordId}
              >{`Type ${word} to confirm`}</FieldLabel>
              <Input
                id={wordId}
                value={typed}
                autoComplete='off'
                onChange={(event) => setTyped(event.target.value)}
              />
              <Muted variant='caption'>This cannot be taken back.</Muted>
            </div>
          )}
        </ConfirmDialog>
      )}
    </>
  )
}
