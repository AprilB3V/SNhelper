import { useEffect, useState } from 'react'
import { Check, Database, Edit3, Eye, EyeOff, KeyRound, Moon, PlugZap, RefreshCw, Save, Server, Sun, Trash2, X } from 'lucide-react'
import { API_URL, createProject, deleteMemory, deleteProject, getCallMode, getModelConfig, getProjects, searchMemory, setCallMode, setModelConfig, testModelConnection, updateMemory, updateProject, type CallMode } from '../api'
import type { Project, SearchResult } from '../types'
import { useAppStore } from '../store'
import { PageHeader } from '../components/Layout'

export function Settings() {
  const { theme, toggleTheme, setProjects: syncProjects, setCurrentProject } = useAppStore()
  const [apiUrl, setApiUrl] = useState(API_URL)
  const [apiKey, setApiKey] = useState('')
  const [modelBaseUrl, setModelBaseUrl] = useState('')
  const [modelApiKey, setModelApiKey] = useState('')
  const [modelName, setModelName] = useState('gpt-4o-mini')
  const [showModelKey, setShowModelKey] = useState(false)
  const [modelStatus, setModelStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')
  const [modelStatusText, setModelStatusText] = useState('')
  const [callMode, setCallModeState] = useState<CallMode>(getCallMode())
  const [showApiKey, setShowApiKey] = useState(false)
  const [saved, setSaved] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectName, setProjectName] = useState('')
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null)
  const [memories, setMemories] = useState<SearchResult[]>([])
  const [memoryOpen, setMemoryOpen] = useState(false)
  const [memoryLoading, setMemoryLoading] = useState(false)
  const [memoryError, setMemoryError] = useState('')
  const [editingMemoryId, setEditingMemoryId] = useState<string | null>(null)
  const [memoryContent, setMemoryContent] = useState('')
  const [memoryTags, setMemoryTags] = useState('')

  useEffect(() => {
    setApiUrl(localStorage.getItem('snhelper-api-url') ?? API_URL)
    setApiKey(localStorage.getItem('snhelper-api-key') ?? '')
    const model = getModelConfig(); setModelBaseUrl(model.baseUrl); setModelApiKey(model.apiKey); setModelName(model.model)
    setCallModeState(getCallMode())
    getProjects().then(setProjects).catch(() => undefined)
  }, [])

  const save = () => {
    localStorage.setItem('snhelper-api-url', apiUrl.trim())
    if (apiKey.trim()) localStorage.setItem('snhelper-api-key', apiKey.trim())
    else localStorage.removeItem('snhelper-api-key')
    setCallMode(callMode)
    setModelConfig({ baseUrl: modelBaseUrl, apiKey: modelApiKey, model: modelName })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const testModel = async () => {
    if (!modelBaseUrl.trim() || !modelApiKey.trim()) { setModelStatus('error'); setModelStatusText('请先填写模型服务地址和模型 API Key'); return }
    setModelStatus('testing'); setModelStatusText('正在测试模型连接...')
    try { const result = await testModelConnection({ baseUrl: modelBaseUrl, apiKey: modelApiKey, model: modelName }); setModelStatus('ok'); setModelStatusText(result.message || `${result.model} 连接成功`) }
    catch (error) { setModelStatus('error'); setModelStatusText(error instanceof Error ? error.message : '模型连接失败') }
  }

  const persistModel = (next: { baseUrl?: string; apiKey?: string; model?: string }) => {
    const current = getModelConfig()
    setModelConfig({ baseUrl: next.baseUrl ?? current.baseUrl, apiKey: next.apiKey ?? current.apiKey, model: next.model ?? current.model })
  }
  const loadMemories = async () => {
    setMemoryLoading(true); setMemoryError('')
    try { setMemories(await searchMemory('')) } catch (error) { setMemoryError(error instanceof Error ? error.message : '长期记忆加载失败') } finally { setMemoryLoading(false) }
  }
  const toggleMemories = () => { const next = !memoryOpen; setMemoryOpen(next); if (next) void loadMemories() }
  const beginMemoryEdit = (memory: SearchResult) => { setEditingMemoryId(memory.id); setMemoryContent(memory.content); setMemoryTags(memory.tags.join(', ')) }
  const saveMemory = async (id: string) => {
    const updated = await updateMemory(id, memoryContent.trim(), memoryTags.split(',').map((tag) => tag.trim()).filter(Boolean))
    setMemories((current) => current.map((item) => item.id === id ? updated : item)); setEditingMemoryId(null)
  }
  const removeMemory = async (id: string) => {
    if (!window.confirm('删除这条长期记忆？')) return
    await deleteMemory(id); setMemories((current) => current.filter((item) => item.id !== id))
  }

  const addProject = async () => { if (!projectName.trim()) return; const project = await createProject(projectName.trim()); setProjects((prev) => { const next = [...prev, project]; syncProjects(next); return next }); setProjectName('') }
  const saveProject = async (project: Project) => { if (!projectName.trim()) return; const updated = await updateProject(project.id, projectName.trim()); setProjects((prev) => { const next = prev.map((item) => item.id === project.id ? updated : item); syncProjects(next); return next }); setEditingProjectId(null); setProjectName('') }
  const removeProject = async (id: string) => { if (id === 'all') return; await deleteProject(id); setProjects((prev) => { const next = prev.filter((project) => project.id !== id); syncProjects(next); if (useAppStore.getState().currentProject.id === id) setCurrentProject(next[0]); return next }) }

  return <div className="page">
    <PageHeader eyebrow="SYSTEM / PREFERENCES" title="系统设置" description="调整连接、外观和长期记忆的边界。" />
    <div className="settings-layout">
      <section className="settings-section">
        <div className="settings-heading"><div className="settings-icon"><Server size={17} /></div><div><h2>后端连接</h2><p>配置你的 LangGraph 服务地址和访问凭证。</p></div></div>
        <div className="credential-fields">
          <label className="form-label">FastAPI 地址<input value={apiUrl} onChange={(event) => setApiUrl(event.target.value)} placeholder="http://127.0.0.1:8000" /></label>
          <label className="form-label">FastAPI API Key<div className="secret-input"><input type={showApiKey ? 'text' : 'password'} value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="后端设置了 SNHELPER_API_KEY 时填写" autoComplete="off" /><button type="button" className="icon-button" onClick={() => setShowApiKey(!showApiKey)} aria-label={showApiKey ? '隐藏 API Key' : '显示 API Key'}>{showApiKey ? <EyeOff size={15} /> : <Eye size={15} />}</button></div></label>
          <label className="form-label">调用模式<select value={callMode} onChange={(event) => { const mode = event.target.value as CallMode; setCallModeState(mode); setCallMode(mode) }}><option value="mock">Mock（本地演示数据）</option><option value="fastapi-rest">FastAPI REST（JSON）</option><option value="fastapi-sse">FastAPI SSE（流式对话）</option></select></label>
        </div>
        <div className="connection-note"><KeyRound size={13} /><span>FastAPI Key 仅保存在当前浏览器，会以 Bearer Token 发送。</span><button className="text-link" onClick={save}>{saved ? <><Check size={14} />已保存</> : <><Save size={14} />保存连接配置</>}</button></div>
        <div className="connection-note"><span className="status-dot live" />当前使用 {callMode === 'mock' ? 'Mock 数据' : callMode === 'fastapi-sse' ? 'FastAPI SSE 流式 API' : 'FastAPI REST API'}</div>
      </section>
      <section className="settings-section">
        <div className="settings-heading"><div className="settings-icon"><PlugZap size={17} /></div><div><h2>外部模型服务</h2><p>填写 OpenAI 兼容服务商地址；对话由 FastAPI 代理调用，避免浏览器直接暴露密钥。</p></div></div>
        <div className="credential-fields">
          <label className="form-label">模型服务地址<input value={modelBaseUrl} onChange={(event) => { const value = event.target.value; setModelBaseUrl(value); persistModel({ baseUrl: value }) }} placeholder="https://api.openai.com/v1 或服务商 /v1" /></label>
          <label className="form-label">模型 API Key<div className="secret-input"><input type={showModelKey ? 'text' : 'password'} value={modelApiKey} onChange={(event) => { const value = event.target.value; setModelApiKey(value); persistModel({ apiKey: value }) }} placeholder="sk-..." autoComplete="off" /><button type="button" className="icon-button" onClick={() => setShowModelKey(!showModelKey)} aria-label={showModelKey ? '隐藏模型 API Key' : '显示模型 API Key'}>{showModelKey ? <EyeOff size={15} /> : <Eye size={15} />}</button></div></label>
          <label className="form-label">模型名称<input value={modelName} onChange={(event) => { const value = event.target.value; setModelName(value); persistModel({ model: value }) }} placeholder="gpt-4o-mini / deepseek-chat" /></label>
        </div>
        <div className="connection-note"><span className={`status-dot ${modelStatus === 'ok' ? 'live' : modelStatus === 'error' ? 'error' : ''}`} />{modelStatusText || '模型配置仅在 FastAPI REST/SSE 模式下生效。'}<button className="text-link" onClick={testModel} disabled={modelStatus === 'testing'}><PlugZap size={14} />{modelStatus === 'testing' ? '测试中...' : '测试模型连接'}</button></div>
      </section>
      <section className="settings-section"><div className="settings-heading"><div className="settings-icon"><Sun size={17} /></div><div><h2>外观</h2><p>选择适合当前环境的显示方式。</p></div></div><div className="theme-picker"><button className={theme === 'dark' ? 'selected' : ''} onClick={() => theme !== 'dark' && toggleTheme()}><Moon size={16} /><span>深色</span><small>适合夜间专注</small></button><button className={theme === 'light' ? 'selected' : ''} onClick={() => theme !== 'light' && toggleTheme()}><Sun size={16} /><span>浅色</span><small>适合明亮环境</small></button></div></section>
      <section className="settings-section"><div className="settings-heading"><div className="settings-icon"><Server size={17} /></div><div><h2>项目管理</h2><p>新增、修改或删除工作区项目。</p></div></div><div className="project-manager-add"><input value={editingProjectId ? projectName : projectName} onChange={(event) => setProjectName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') editingProjectId ? saveProject(projects.find((item) => item.id === editingProjectId)!) : addProject() }} placeholder="新项目名称" /><button className="button soft" onClick={() => editingProjectId ? saveProject(projects.find((item) => item.id === editingProjectId)!) : addProject()}>{editingProjectId ? '保存修改' : '新增项目'}</button>{editingProjectId && <button className="button ghost" onClick={() => { setEditingProjectId(null); setProjectName('') }}>取消</button>}</div><div className="project-manager-list">{projects.map((project) => <div className="project-manager-row" key={project.id}><span><i className="project-dot" style={{ background: project.color ?? '#d2a55e' }} />{project.name}</span><div>{project.id !== 'all' && <><button className="icon-button" onClick={() => { setEditingProjectId(project.id); setProjectName(project.name) }} aria-label="编辑项目"><Save size={14} /></button><button className="icon-button danger-icon" onClick={() => removeProject(project.id)} aria-label="删除项目"><Trash2 size={14} /></button></>}</div></div>)}</div></section>
      <section className="settings-section danger-zone">
        <div className="settings-heading"><div className="settings-icon"><Database size={17} /></div><div><h2>长期记忆</h2><p>查看、编辑和删除系统沉淀的个人知识。</p></div></div>
        <div className="memory-row"><div><strong>{memoryOpen ? `${memories.length} 条长期记忆` : '长期记忆库'}</strong><span>{memoryOpen ? '显示最近记录，可直接编辑或删除' : '按需加载，避免设置页初始请求过多'}</span></div><button className="button ghost" onClick={toggleMemories}><Database size={15} />{memoryOpen ? '收起管理' : '打开记忆管理'}</button></div>
        {memoryOpen && <div className="memory-manager"><div className="memory-manager-toolbar"><span>最近记忆</span><button className="icon-button" onClick={() => void loadMemories()} disabled={memoryLoading} aria-label="刷新记忆"><RefreshCw size={14} className={memoryLoading ? 'spin' : ''} /></button></div>{memoryError && <div className="connection-note"><span className="status-dot error" />{memoryError}</div>}{!memoryLoading && !memoryError && memories.length === 0 && <div className="empty-state">暂无长期记忆。</div>}{memories.map((memory) => <article className="memory-manager-item" key={memory.id}>{editingMemoryId === memory.id ? <div className="memory-edit"><textarea value={memoryContent} onChange={(event) => setMemoryContent(event.target.value)} /><input value={memoryTags} onChange={(event) => setMemoryTags(event.target.value)} placeholder="标签，用逗号分隔" /><div><button className="button primary" onClick={() => void saveMemory(memory.id)}><Check size={14} />保存</button><button className="button ghost" onClick={() => setEditingMemoryId(null)}><X size={14} />取消</button></div></div> : <><p>{memory.content}</p><div className="memory-manager-meta"><div>{memory.tags.map((tag) => <span className="tag-chip" key={tag}>{tag}</span>)}</div><div className="result-actions"><button className="icon-button" onClick={() => beginMemoryEdit(memory)} aria-label="编辑长期记忆"><Edit3 size={14} /></button><button className="icon-button danger-icon" onClick={() => void removeMemory(memory.id)} aria-label="删除长期记忆"><Trash2 size={14} /></button></div></div></>}</article>)}</div>}
      </section>
    </div>
  </div>
}
