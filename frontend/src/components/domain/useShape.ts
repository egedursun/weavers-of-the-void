import { useState } from 'react'

export type Shape = { name: string; title: string; description: string }

const BLANK: Shape = { name: '', title: '', description: '' }

export function useShape() {
  const [shape, setShape] = useState<Shape>(BLANK)
  return {
    shape,
    setShape,
    reset: () => setShape(BLANK),
    body: {
      name: shape.name.trim() || null,
      title: shape.title.trim() || null,
      description: shape.description.trim() || null,
    },
  }
}
