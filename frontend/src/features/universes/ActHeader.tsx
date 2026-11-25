import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import {
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Medallion } from '@/components/domain'
import { type UniverseSummary } from './types'

export type ActDialogProps = {
  universe: UniverseSummary
  onClose: () => void
}

export function ActHeader({
  icon,
  title,
  children,
}: {
  icon: LucideIcon
  title: string
  children: ReactNode
}) {
  return (
    <DialogHeader>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={icon} />
        <DialogTitle>{title}</DialogTitle>
      </div>
      <DialogDescription>{children}</DialogDescription>
    </DialogHeader>
  )
}
