import { type ReactNode } from 'react'
import { Muted, Text } from '@/components/typography'

type OrderBlockProps = {
  title: string
  description: string
  children: ReactNode
}

export function OrderBlock({ title, description, children }: OrderBlockProps) {
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 flex-col gap-0.5'>
        <Text weight='medium'>{title}</Text>
        <Muted variant='caption'>{description}</Muted>
      </div>
      {children}
    </div>
  )
}

export function OrderFields({ children }: { children: ReactNode }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
      {children}
    </div>
  )
}
