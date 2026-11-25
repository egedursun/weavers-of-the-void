import * as React from 'react'
import { Tooltip, TooltipContent, TooltipTrigger } from './tooltip'

export function Refusal({
  reason,
  children,
}: {
  reason: string | null
  children: React.ReactElement
}) {
  if (reason === null) return children
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          aria-description={reason}
          data-slot='refusal'
          className='inline-flex max-w-full min-w-0 cursor-not-allowed'
        >
          {children}
        </span>
      </TooltipTrigger>
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  )
}
