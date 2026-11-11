import { type ThreeEvent } from '@react-three/fiber'

export const TAP_SLOP = 4

export function onTap(act: (event: ThreeEvent<MouseEvent>) => void) {
  return (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    if (event.delta > TAP_SLOP) return
    act(event)
  }
}
