import { toast } from 'sonner'

export const PROMPT_MAX_LENGTH = 2000
const COPIED = 'Copied'
const COPY_FAILED = "Couldn't copy; select the text and copy it."

export async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(COPIED)
  } catch {
    toast.error(COPY_FAILED)
  }
}
