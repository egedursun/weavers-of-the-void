import { type LucideIcon } from 'lucide-react'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useCosmicCatalogue } from './api'
import { useCosmicGate } from './useCosmicAction'

type Confirmation = {
  title: string
  description: string
  confirmText: string
}

type CosmicActionButtonProps = {
  actionId: string
  label: string
  onRun: () => void
  pending?: boolean
  cost?: number
  icon?: LucideIcon
  variant?: 'default' | 'outline' | 'secondary' | 'destructive' | 'ghost'
  size?: 'sm' | 'default'
  blockedReason?: string
  confirm?: Confirmation
}

export function CosmicActionButton({
  actionId,
  label,
  onRun,
  pending = false,
  cost,
  icon,
  variant = 'outline',
  size = 'default',
  blockedReason,
  confirm,
}: CosmicActionButtonProps) {
  const gate = useCosmicGate()
  const { data: catalogue } = useCosmicCatalogue()
  const entry = catalogue?.find((item) => item.id === actionId)
  const word = entry?.confirmation ?? null
  const reason = blockedReason ?? gate.reasonFor(cost) ?? null
  const dialog =
    confirm || word
      ? {
          title: confirm?.title ?? entry?.title ?? label,
          description:
            confirm?.description ?? `This costs ${entry?.cost ?? 'nothing'}.`,
          word,
          confirmLabel: confirm?.confirmText,
        }
      : undefined
  return (
    <ActionButton
      label={label}
      icon={icon}
      cost={cost}
      costText={entry ? `${entry.title}: ${entry.cost}` : undefined}
      blocked={reason}
      pending={pending}
      confirm={dialog}
      onRun={onRun}
      variant={variant}
      size={size}
    />
  )
}
