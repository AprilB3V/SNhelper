import { create } from 'zustand'
import type { Project } from './types'

type AppState = {
  projects: Project[]
  currentProject: Project
  theme: 'dark' | 'light'
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project) => void
  toggleTheme: () => void
}

const defaultProject: Project = { id: 'all', name: '全部项目', color: '#d2a55e' }

export const useAppStore = create<AppState>((set) => ({
  projects: [defaultProject],
  currentProject: defaultProject,
  theme: 'dark',
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (currentProject) => set({ currentProject }),
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
}))
