import { Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { copyText } from '@/features/images/copyText'

type CopyButtonProps = {
  text: string
  label?: string
}

export function CopyButton({ text, label = 'Copy' }: CopyButtonProps) {
  return (
    <Button
      type='button'
      variant='ghost'
      size='icon-sm'
      aria-label={label}
      disabled={text === ''}
      disabledReason='Nothing to copy'
      onClick={() => void copyText(text)}
    >
      <Copy />
    </Button>
  )
}
