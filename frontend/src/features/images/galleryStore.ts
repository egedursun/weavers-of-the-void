import { create } from 'zustand'

type GalleryState = {
  nodeId: number | null
  index: number | null
  open: (nodeId: number, index?: number) => void
  close: () => void
}

export const useGalleryStore = create<GalleryState>((set) => ({
  nodeId: null,
  index: null,
  open: (nodeId, index = 0) => set({ nodeId, index }),
  close: () => set({ nodeId: null, index: null }),
}))
