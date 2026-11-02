import { useLayoutEffect, useRef } from 'react'

export function Spacer({ height }: { height: number }) {
  const element = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    if (element.current) element.current.style.height = `${height}px`
  }, [height])
  return <div ref={element} aria-hidden='true' className='shrink-0' />
}
