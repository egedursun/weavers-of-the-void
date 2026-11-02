import { type ComponentProps, createElement } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TOOL_FALLBACK_ICON, toolIdIcon } from './toolIcons'

type ToolIconProps = {
  tool: string
  size?: 'sm' | 'md'
  className?: string
}

export function ToolIcon({ tool, size = 'sm', className }: ToolIconProps) {
  const props: ComponentProps<LucideIcon> & Record<`data-${string}`, string> = {
    'aria-hidden': true,
    'data-tool': tool,
    className: cn(
      'shrink-0',
      size === 'sm' ? 'size-icon-sm' : 'size-icon-md',
      className
    ),
  }
  return createElement(toolIdIcon(tool) ?? TOOL_FALLBACK_ICON, props)
}
