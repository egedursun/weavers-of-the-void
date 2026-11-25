import { CircleAlert, CircleCheck, type LucideIcon } from 'lucide-react'
import { type AttachmentStatus } from './types'

export const ATTACHMENT_STATUS_LOOK: Record<
  AttachmentStatus,
  { label: string; icon: LucideIcon; variant: 'success' | 'info' | 'warning' }
> = {
  stored: { label: 'Stored', icon: CircleCheck, variant: 'info' },
  converted: { label: 'Read into text', icon: CircleCheck, variant: 'success' },
  indexed: { label: 'Searchable', icon: CircleCheck, variant: 'success' },
  unreadable: {
    label: 'Cannot be read',
    icon: CircleAlert,
    variant: 'warning',
  },
}
