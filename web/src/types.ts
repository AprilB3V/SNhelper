export type Agent = { id: string; name: string; role: string; color: string }
export type Project = { id: string; name: string; color?: string }
export type Task = { id: string; title: string; done: boolean; duration: number; project?: string }
export type SearchResult = { id: string; content: string; tags: string[]; score: number; createdAt?: string }
export type CaptureNote = { id: string; content: string; tags: string[]; createdAt: string; updatedAt?: string }
export type ChatMessage = { id: string; role: 'user' | 'assistant'; content: string; agent?: string; timestamp: string }
export type Conversation = { id: string; title: string; project: string; agent: string; messages: ChatMessage[]; updatedAt: string }
export type Health = { status: string; agents: Agent[] }
