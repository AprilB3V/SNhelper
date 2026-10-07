import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ChatMessage, Conversation } from './types'

type ConversationsState = {
  conversations: Conversation[]
  activeId: string | null
  createConversation: (project: string, agent: string) => string
  selectConversation: (id: string) => void
  renameConversation: (id: string, title: string) => void
  deleteConversation: (id: string) => void
  saveMessages: (id: string, messages: ChatMessage[], agent: string) => void
}

const createId = () => typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `conversation-${Date.now()}-${Math.random().toString(36).slice(2)}`

export const useConversationStore = create<ConversationsState>()(persist((set) => ({
  conversations: [],
  activeId: null,
  createConversation: (project, agent) => {
    const id = createId()
    const conversation: Conversation = { id, title: '新对话', project, agent, messages: [], updatedAt: new Date().toISOString() }
    set((state) => ({ activeId: id, conversations: [conversation, ...state.conversations] }))
    return id
  },
  selectConversation: (activeId) => set({ activeId }),
  renameConversation: (id, title) => set((state) => ({ conversations: state.conversations.map((item) => item.id === id ? { ...item, title: title.trim() || '新对话' } : item) })),
  deleteConversation: (id) => set((state) => ({ conversations: state.conversations.filter((item) => item.id !== id), activeId: state.activeId === id ? null : state.activeId })),
  saveMessages: (id, messages, agent) => set((state) => ({ conversations: state.conversations.map((item) => item.id === id ? {
    ...item, messages, agent, updatedAt: new Date().toISOString(),
    title: item.title === '新对话' ? messages.find((message) => message.role === 'user')?.content.slice(0, 32) || item.title : item.title,
  } : item) })),
}), { name: 'snhelper-conversations-v1', version: 1 }))
