import { TriangleAlert } from 'lucide-react'
import { Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'

export function TermsNote({ terms }: { terms: string }) {
  return (
    <div
      role='note'
      className='flex min-w-0 items-center gap-3 rounded-md p-3 sealed-well'
    >
      <Medallion icon={TriangleAlert} tone='warning' size='sm' />
      <span className='flex min-w-0 flex-1 flex-col gap-0.5'>
        <Text as='span' weight='medium' tone='warning'>
          Mind the terms of the provider
        </Text>
        <Muted as='span' variant='caption'>
          {terms}
        </Muted>
      </span>
    </div>
  )
}
