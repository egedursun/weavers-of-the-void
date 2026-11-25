import { toast } from 'sonner'

export const PROMPT_MAX_LENGTH = 2000
const COPIED = 'Copied'
const COPY_FAILED = "Couldn't copy; select the text and copy it."

function copiedBySelection(text: string): boolean {
  const field = document.createElement('textarea')
  field.value = text
  field.setAttribute('readonly', '')
  field.style.position = 'fixed'
  field.style.opacity = '0'
  document.body.append(field)
  field.select()
  try {
    return document.execCommand('copy')
  } catch {
    return false
  } finally {
    field.remove()
  }
}

async function copiedToClipboard(text: string): Promise<boolean> {
  if (window.isSecureContext && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      return copiedBySelection(text)
    }
  }
  return copiedBySelection(text)
}

export async function copyText(text: string): Promise<boolean> {
  const copied = await copiedToClipboard(text)
  if (copied) toast.success(COPIED)
  else toast.error(COPY_FAILED)
  return copied
}
