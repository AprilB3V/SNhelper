import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type FocusState = {
  focusDate: string
  accumulatedSeconds: number
  startedAt: number | null
  running: boolean
  start: () => void
  pause: () => void
  sync: () => void
  getSeconds: () => number
}

const dateKey = () => new Date().toISOString().slice(0, 10)

const currentSeconds = (state: Pick<FocusState, 'focusDate' | 'accumulatedSeconds' | 'startedAt' | 'running'>) => {
  if (state.focusDate !== dateKey()) return 0
  return state.accumulatedSeconds + (state.running && state.startedAt ? Math.max(0, Math.floor((Date.now() - state.startedAt) / 1000)) : 0)
}

export const useFocusStore = create<FocusState>()(persist((set, get) => ({
  focusDate: dateKey(), accumulatedSeconds: 0, startedAt: null, running: false,
  start: () => set((state) => {
    const seconds = currentSeconds(state)
    return { focusDate: dateKey(), accumulatedSeconds: seconds, startedAt: Date.now(), running: true }
  }),
  pause: () => set((state) => ({ focusDate: dateKey(), accumulatedSeconds: currentSeconds(state), startedAt: null, running: false })),
  sync: () => set((state) => state.focusDate === dateKey() ? { accumulatedSeconds: currentSeconds(state), startedAt: state.running ? Date.now() : null } : { focusDate: dateKey(), accumulatedSeconds: 0, startedAt: null, running: false }),
  getSeconds: () => currentSeconds(get()),
}), { name: 'snhelper-focus-v1', version: 1 }))
