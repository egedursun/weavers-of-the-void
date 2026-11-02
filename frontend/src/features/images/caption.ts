const UUID_START = /^[0-9a-f]{8}-[0-9a-f]{4}-/i
const GENERIC_START =
  /^(gemini|chatgpt|dall|midjourney|img|image|dsc|photo|pxl|screenshot|screen shot|watermarked)[\s_-]/i
const MACHINE_STEM = /^[\w-]+_\w*\d{4,}\w*$/
const EXTENSION = /\.[a-z0-9]{2,5}$/i
const SEPARATORS = /[_]+/g

export function isMeaningfulCaption(
  caption: string | null | undefined
): boolean {
  if (!caption) return false
  const text = caption.trim()
  if (!text) return false
  return (
    !UUID_START.test(text) &&
    !GENERIC_START.test(text) &&
    !MACHINE_STEM.test(text)
  )
}

export function captionFromFileName(fileName: string): string | null {
  const stem = fileName.replace(EXTENSION, '').trim()
  if (!isMeaningfulCaption(stem)) return null
  return stem.replace(SEPARATORS, ' ').trim() || null
}
