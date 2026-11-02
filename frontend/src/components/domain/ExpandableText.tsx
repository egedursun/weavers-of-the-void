import { type ReactNode, useEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  type TextTone,
  type TextVariant,
  textVariants,
  toneClass,
} from '@/components/typography/textStyles'

const CLAMP: Record<2 | 3 | 4 | 6, string> = {
  2: 'line-clamp-2',
  3: 'line-clamp-3',
  4: 'line-clamp-4',
  6: 'line-clamp-6',
}

type ExpandableTextProps = {
  children: ReactNode
  lines?: 2 | 3 | 4 | 6
  variant?: TextVariant
  tone?: TextTone
  italic?: boolean
}

export function ExpandableText({
  children,
  lines = 3,
  variant = 'body',
  tone = 'default',
  italic = false,
}: ExpandableTextProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [overflow, setOverflow] = useState(false)
  useEffect(() => {
    const element = ref.current
    if (!element || open) return
    const observer = new ResizeObserver(() =>
      setOverflow(element.scrollHeight > element.clientHeight + 1)
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [open, children])
  return (
    <div
      data-domain='expandable-text'
      className='flex min-w-0 flex-col items-start gap-0.5'
    >
      <div
        ref={ref}
        data-typography={variant}
        className={cn(
          textVariants({ variant }),
          toneClass[tone],
          'min-w-0 wrap-anywhere',
          italic && 'italic',
          !open && CLAMP[lines]
        )}
      >
        {children}
      </div>
      {(overflow || open) && (
        <Button
          variant='link'
          size='sm'
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className='h-auto px-0 has-[>svg]:px-0'
        >
          {open ? <ChevronUp /> : <ChevronDown />}
          {open ? 'Show less' : 'Read more'}
        </Button>
      )}
    </div>
  )
}
