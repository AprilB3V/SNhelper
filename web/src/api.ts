import type { Agent, CaptureNote, Health, Project, SearchResult, Task } from './types'

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8000'
export type CallMode = 'mock' | 'fastapi-rest' | 'fastapi-sse'
const CALL_MODE_KEY = 'snhelper-call-mode'
const MODEL_BASE_URL_KEY = 'snhelper-model-base-url'
const MODEL_API_KEY_KEY = 'snhelper-model-api-key'
const MODEL_NAME_KEY = 'snhelper-model-name'
const isCallMode = (value: string | null | undefined): value is CallMode => value === 'mock' || value === 'fastapi-rest' || value === 'fastapi-sse'
export const getCallMode = (): CallMode => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(CALL_MODE_KEY)
    if (isCallMode(saved)) return saved
  }
  const configured = import.meta.env.VITE_CALL_MODE as string | undefined
  if (isCallMode(configured)) return configured
  return (import.meta.env.VITE_MOCK_MODE as string | undefined) === 'false' ? 'fastapi-rest' : 'mock'
}
export const setCallMode = (mode: CallMode) => { if (typeof window !== 'undefined') localStorage.setItem(CALL_MODE_KEY, mode) }
export const isMockMode = () => getCallMode() === 'mock'
export const MOCK_MODE = isMockMode()
const getApiUrl = () => typeof window !== 'undefined' ? (localStorage.getItem('snhelper-api-url') ?? API_URL).replace(/\/$/, '') : API_URL
const getApiKey = () => typeof window !== 'undefined' ? (localStorage.getItem('snhelper-api-key') ?? '').trim() : ''
export type ModelConfig = { baseUrl: string; apiKey: string; model: string }
export const getModelConfig = (): ModelConfig => typeof window !== 'undefined' ? {
  baseUrl: (localStorage.getItem(MODEL_BASE_URL_KEY) ?? '').trim(),
  apiKey: (localStorage.getItem(MODEL_API_KEY_KEY) ?? '').trim(),
  model: (localStorage.getItem(MODEL_NAME_KEY) ?? 'gpt-4o-mini').trim(),
} : { baseUrl: '', apiKey: '', model: 'gpt-4o-mini' }
export const setModelConfig = (config: ModelConfig) => {
  if (typeof window === 'undefined') return
  if (config.baseUrl.trim()) localStorage.setItem(MODEL_BASE_URL_KEY, config.baseUrl.trim()); else localStorage.removeItem(MODEL_BASE_URL_KEY)
  if (config.apiKey.trim()) localStorage.setItem(MODEL_API_KEY_KEY, config.apiKey.trim()); else localStorage.removeItem(MODEL_API_KEY_KEY)
  localStorage.setItem(MODEL_NAME_KEY, config.model.trim() || 'gpt-4o-mini')
}
const getAuthHeaders = (): Record<string, string> => { const apiKey = getApiKey(); return apiKey ? { Authorization: `Bearer ${apiKey}` } : {} }
const readMock = <T,>(key: string, fallback: T): T => { if (typeof window === 'undefined') return fallback; try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) as T : fallback } catch { return fallback } }
const writeMock = (key: string, value: unknown) => { if (typeof window !== 'undefined') localStorage.setItem(key, JSON.stringify(value)) }
const mockSearchTerms = (query: string) => {
  const terms: string[] = query.toLowerCase().match(/[a-z0-9_]{2,}/g) ?? []
  const chinese: string[] = query.match(/[\u4e00-\u9fff]{2,}/g) ?? []
  chinese.forEach((segment) => { for (let index = 0; index < segment.length - 1; index += 1) terms.push(segment.slice(index, index + 2)) })
  return Array.from(new Set(terms))
}
const mockMatches = (item: SearchResult, query: string) => {
  if (!query.trim()) return true
  const haystack = `${item.content} ${item.tags.join(' ')}`.toLowerCase()
  return mockSearchTerms(query).some((term) => haystack.includes(term))
}

const mockAgents: Agent[] = [
  { id: 'orchestrator', name: 'Orchestrator', role: '总调度器', color: '#d2a55e' },
  { id: 'archivist', name: 'Archivist', role: '知识库管家', color: '#72c6c5' },
  { id: 'enforcer', name: 'Enforcer', role: '执行督导', color: '#f0806b' },
  { id: 'strategist', name: 'Strategist', role: '战略参谋', color: '#a9b7f0' },
  { id: 'simulator', name: 'Simulator', role: '社交沙盘', color: '#d19ce3' },
]

let mockProjects: Project[] = [
  { id: 'all', name: '全部项目', color: '#d2a55e' },
  { id: 'grad', name: '考研攻坚', color: '#72c6c5' },
  { id: 'startup', name: 'Side Project', color: '#f0806b' },
  { id: 'life', name: '个人生活', color: '#a9b7f0' },
]
let mockTasks: Task[] = [
  { id: 't1', title: '完成 LangGraph 路由器的异常分支测试', done: false, duration: 45, project: 'startup' },
  { id: 't2', title: '整理 3 篇强化学习论文的核心假设', done: false, duration: 30, project: 'grad' },
  { id: 't3', title: '给导师发本周实验进度同步', done: true, duration: 15, project: 'grad' },
  { id: 't4', title: '跑一遍今天的英语真题听力', done: false, duration: 30, project: 'grad' },
]
let mockCaptures: CaptureNote[] = readMock<CaptureNote[]>('snhelper-captures-v1', [
  { id: 'c1', content: 'Agent 系统应该在我忘记上下文时，主动把决策依据带回来。', tags: ['灵感', '产品'], createdAt: '今天 09:42' },
  { id: 'c2', content: '两周内找到 3 个愿意付费的真实用户，否则停止增加功能。', tags: ['创业', '验证'], createdAt: '昨天 18:10' },
])
let mockSearch: SearchResult[] = readMock<SearchResult[]>('snhelper-memories-v1', [
  { id: 'm1', content: '把 Agent 系统做成第二大脑，而不是另一个聊天机器人。判断标准是：它是否能在我忘记上下文时，主动把决策依据带回来。', tags: ['产品', '认知外骨骼'], score: 0.96, createdAt: '今天 09:42' },
  { id: 'm2', content: '创业方向的第一性问题：如果不能在两周内找到 3 个愿意付费的真实用户，就先停止增加功能。', tags: ['创业', '验证'], score: 0.88, createdAt: '昨天 18:10' },
  { id: 'm3', content: '复盘：深度工作开始前先写下“这 45 分钟结束时，桌面上应该出现什么新东西”。', tags: ['方法论', '执行'], score: 0.81, createdAt: '10 月 04 日' },
])

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export class ApiError extends Error { constructor(public status: number, message: string) { super(message); this.name = 'ApiError' } }

async function request<T>(path: string, options: RequestInit = {}, retry = 1): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 20000)
  const forwardAbort = () => controller.abort()
  options.signal?.addEventListener('abort', forwardAbort, { once: true })
  try {
    const response = await fetch(`${getApiUrl()}${path}`, { ...options, signal: controller.signal, headers: { 'Content-Type': 'application/json', ...getAuthHeaders(), ...(options.headers ?? {}) } })
    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      if (retry > 0 && response.status >= 500 && options.method !== 'POST' && options.method !== 'PATCH' && options.method !== 'DELETE') { await wait(350); return request<T>(path, options, retry - 1) }
      throw new ApiError(response.status, detail || `API ${response.status}`)
    }
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError(408, '请求超时或已取消')
    if (retry > 0 && options.method !== 'POST' && options.method !== 'PATCH' && options.method !== 'DELETE') { await wait(350); return request<T>(path, options, retry - 1) }
    throw error
  } finally {
    window.clearTimeout(timeout)
    options.signal?.removeEventListener('abort', forwardAbort)
  }
}

export async function getHealth(): Promise<Health> { if (isMockMode()) { await wait(220); return { status: 'ok', agents: mockAgents } } return request<Health>('/health') }
export async function getProjects(): Promise<Project[]> { if (isMockMode()) { await wait(120); return mockProjects } return request<Project[]>('/projects') }
export async function createProject(name: string): Promise<Project> { if (isMockMode()) { const project = { id: `project-${Date.now()}`, name, color: '#d2a55e' }; mockProjects = [...mockProjects, project]; return project } return request<Project>('/projects', { method: 'POST', body: JSON.stringify({ name }) }) }
export async function updateProject(id: string, name: string): Promise<Project> { if (isMockMode()) { const project = mockProjects.find((item) => item.id === id); if (!project) throw new Error('项目不存在'); project.name = name; return project } return request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify({ name }) }) }
export async function deleteProject(id: string): Promise<void> { if (isMockMode()) { mockProjects = mockProjects.filter((project) => project.id !== id && project.id !== 'all'); return } await request(`/projects/${id}`, { method: 'DELETE' }) }

export async function getTasks(date: string): Promise<Task[]> { if (isMockMode()) { await wait(160); return [...mockTasks] } return request<Task[]>(`/tasks?date=${encodeURIComponent(date)}`) }
export async function completeTask(id: string): Promise<void> { if (isMockMode()) { mockTasks = mockTasks.map((task) => task.id === id ? { ...task, done: !task.done } : task); return } await request(`/tasks/${id}/complete`, { method: 'POST' }) }
export async function addTask(title: string, duration: number, project?: string): Promise<Task> { if (isMockMode()) { const task = { id: `t-${Date.now()}`, title, duration, done: false, project }; mockTasks = [task, ...mockTasks]; return task } return request<Task>('/tasks', { method: 'POST', body: JSON.stringify({ title, duration, project }) }) }
export async function updateTask(id: string, values: Partial<Pick<Task, 'title' | 'duration' | 'project'>>): Promise<Task> { if (isMockMode()) { const task = mockTasks.find((item) => item.id === id); if (!task) throw new Error('任务不存在'); Object.assign(task, values); return task } return request<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(values) }) }
export async function deleteTask(id: string): Promise<void> { if (isMockMode()) { mockTasks = mockTasks.filter((task) => task.id !== id); return } await request(`/tasks/${id}`, { method: 'DELETE' }) }

export async function capture(content: string, tags: string[]): Promise<{ success: boolean; id?: string }> { if (isMockMode()) { const note = { id: `c-${Date.now()}`, content, tags, createdAt: '刚刚' }; mockCaptures = [note, ...mockCaptures]; mockSearch = [{ id: note.id, content, tags, score: 1, createdAt: '刚刚' }, ...mockSearch]; writeMock('snhelper-captures-v1', mockCaptures); writeMock('snhelper-memories-v1', mockSearch); await wait(180); return { success: true, id: note.id } } return request('/capture', { method: 'POST', body: JSON.stringify({ content, tags }) }) }
export async function getCaptures(): Promise<CaptureNote[]> { if (isMockMode()) return [...mockCaptures] ; return request<CaptureNote[]>('/captures') }
export async function updateCapture(id: string, content: string, tags: string[]): Promise<CaptureNote> { if (isMockMode()) { const note = mockCaptures.find((item) => item.id === id); if (!note) throw new Error('速记不存在'); Object.assign(note, { content, tags, updatedAt: '刚刚' }); const memory = mockSearch.find((item) => item.id === id); if (memory) Object.assign(memory, { content, tags }); writeMock('snhelper-captures-v1', mockCaptures); writeMock('snhelper-memories-v1', mockSearch); return note } return request<CaptureNote>(`/captures/${id}`, { method: 'PATCH', body: JSON.stringify({ content, tags }) }) }
export async function deleteCapture(id: string): Promise<void> { if (isMockMode()) { mockCaptures = mockCaptures.filter((note) => note.id !== id); mockSearch = mockSearch.filter((item) => item.id !== id); writeMock('snhelper-captures-v1', mockCaptures); writeMock('snhelper-memories-v1', mockSearch); return } await request(`/captures/${id}`, { method: 'DELETE' }) }
export async function suggestTags(content: string, agent: string): Promise<string[]> {
  if (isMockMode()) {
    await wait(260)
    const rules: Record<string, string[]> = { Archivist: ['知识库', '归档'], Strategist: ['战略', '决策'], Enforcer: ['执行', '任务'], Simulator: ['社交', '沟通'] }
    const common = content.match(/创业|产品|考研|论文|复盘|灵感|计划|任务|沟通|会议/g) ?? []
    return Array.from(new Set([...(rules[agent] ?? ['灵感']), ...common])).slice(0, 5)
  }
  return request<string[]>('/capture/suggest-tags', { method: 'POST', body: JSON.stringify({ content, agent }) })
}

export async function testModelConnection(config: ModelConfig): Promise<{ success: boolean; model: string; message: string }> {
  return request('/provider/test', { method: 'POST', body: JSON.stringify({ base_url: config.baseUrl, api_key: config.apiKey, model: config.model }) })
}

export async function searchMemory(query: string): Promise<SearchResult[]> { if (isMockMode()) { await wait(180); return mockSearch.filter((item) => mockMatches(item, query)) } return request<SearchResult[]>(`/search?q=${encodeURIComponent(query)}`) }
export async function updateMemory(id: string, content: string, tags: string[]): Promise<SearchResult> { if (isMockMode()) { const item = mockSearch.find((result) => result.id === id); if (!item) throw new Error('记忆不存在'); Object.assign(item, { content, tags }); writeMock('snhelper-memories-v1', mockSearch); return item } return request<SearchResult>(`/memories/${id}`, { method: 'PATCH', body: JSON.stringify({ content, tags }) }) }
export async function deleteMemory(id: string): Promise<void> { if (isMockMode()) { mockSearch = mockSearch.filter((item) => item.id !== id); writeMock('snhelper-memories-v1', mockSearch); return } await request(`/memories/${id}`, { method: 'DELETE' }) }

export type ChatChunk = { text: string; agent?: string }
export type ChatChunkHandler = (chunk: ChatChunk) => void

function parseChatPayload(raw: string): ChatChunk | null {
  const value = raw.replace(/^data:\s?/, '').trim()
  if (!value || value === '[DONE]') return null
  try {
    const payload = JSON.parse(value) as Record<string, unknown>
    const text = payload.delta ?? payload.content ?? payload.message ?? payload.text ?? ''
    return text ? { text: String(text), agent: typeof payload.agent === 'string' ? payload.agent : undefined } : null
  } catch { return { text: value } }
}

export async function sendChat(message: string, project: string, onChunk?: ChatChunkHandler, signal?: AbortSignal, memoryContext: SearchResult[] = []): Promise<string> {
  if (isMockMode()) {
    const chunks: ChatChunk[] = [
      { text: `收到。你当前在「${project}」项目下输入了：` },
      { text: `「${message}」\n\n`, agent: 'Orchestrator' },
      ...(memoryContext.length > 0 ? [{ text: `我检索到 ${memoryContext.length} 条相关灵感速记：\n${memoryContext.slice(0, 3).map((item) => `- ${item.content}`).join('\n')}\n\n`, agent: 'Archivist' as string }] : []),
      { text: '我会先让 **Archivist** 提取上下文，再让 **Enforcer** 把它压缩成一个今天能完成的动作。\n\n', agent: 'Archivist' },
      { text: '> 建议：先用 15 分钟写出下一步的可验证结果。', agent: 'Enforcer' },
    ]
    let result = ''
    for (const chunk of chunks) { if (signal?.aborted) throw new ApiError(499, '对话已停止'); await wait(180); result += chunk.text; onChunk?.(chunk) }
    return result
  }
  const query = getCallMode() === 'fastapi-sse' ? '?stream=true' : ''
  const model = getModelConfig()
  const response = await fetch(`${getApiUrl()}/chat${query}`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ message, project, memory_context: memoryContext.slice(0, 5).map((item) => ({ id: item.id, content: item.content, tags: item.tags, score: item.score })), model_base_url: model.baseUrl || undefined, model_api_key: model.apiKey || undefined, model_name: model.model || undefined }), signal })
  if (!response.ok) throw new ApiError(response.status, await response.text().catch(() => `API ${response.status}`))
  if (!response.body) { const payload = await response.json() as Record<string, unknown>; const chunk = parseChatPayload(JSON.stringify(payload)); if (chunk) onChunk?.(chunk); return chunk?.text ?? '' }
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let result = ''; let buffer = ''; const isSse = response.headers.get('content-type')?.includes('text/event-stream')
  const emit = (raw: string) => { const chunk = parseChatPayload(raw); if (chunk) { result += chunk.text; onChunk?.(chunk) } }
  while (true) { if (signal?.aborted) { await reader.cancel(); throw new ApiError(499, '对话已停止') } const { done, value } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); if (isSse) { const events = buffer.split(/\r?\n\r?\n/); buffer = events.pop() ?? ''; events.forEach(emit) } else { emit(buffer); buffer = '' } }
  buffer += decoder.decode(); if (buffer.trim()) emit(buffer)
  return result
}

export { API_URL, mockAgents }
