import {
  createElement,
  useRef,
  useState,
  type HTMLAttributes,
  type ReactNode,
} from 'react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { type Truncate, truncationClass } from './textStyles'

export type TextTag =
  | 'p'
  | 'span'
  | 'div'
  | 'h1'
  | 'h2'
  | 'h3'
  | 'h4'
  | 'dt'
  | 'dd'
  | 'li'
  | 'label'
  | 'legend'
  | 'figcaption'
  | 'blockquote'
  | 'strong'
  | 'em'
  | 'time'

type TruncatableProps = HTMLAttributes<HTMLElement> & {
  as: TextTag
  truncate?: Truncate
  htmlFor?: string
  dateTime?: string
  children?: ReactNode
}

function isOverflowing(element: HTMLElement | null): boolean {
  if (!element) return false
  return (
    element.scrollWidth > element.clientWidth + 1 ||
    element.scrollHeight > element.clientHeight + 1
  )
}

export function Truncatable({
  as,
  truncate,
  className,
  children,
  ...props
}: TruncatableProps) {
  const ref = useRef<HTMLElement>(null)
  const [open, setOpen] = useState(false)
  const classes = cn(truncationClass(truncate), className)
  if (!truncate)
    return createElement(as, { ...props, className: classes }, children)
  return (
    <Tooltip
      open={open}
      onOpenChange={(next) => setOpen(next && isOverflowing(ref.current))}
    >
      <TooltipTrigger asChild>
        {createElement(
          as,
          {
            ...props,
            ref,
            className: classes,
            'data-truncate': String(truncate === true ? 1 : truncate),
          },
          children
        )}
      </TooltipTrigger>
      <TooltipContent>{children}</TooltipContent>
    </Tooltip>
  )
}
