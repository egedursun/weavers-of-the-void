import { type RefObject, useRef } from 'react'

export type LabelElements = RefObject<Map<string, HTMLElement>>

export function useLabelElements(): LabelElements {
  return useRef(new Map<string, HTMLElement>())
}
