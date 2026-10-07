import { useEffect, useMemo, useState } from 'react'
import { ArrowUpRight, Check, Clock3, MessageSquare, Pause, Play, Plus, RefreshCw, Sparkles, Target, TrendingUp } from 'lucide-react'
import { completeTask, getHealth, getTasks, searchMemory } from '../api'
import { useConversationStore } from '../conversation-store'
import { useFocusStore } from '../focus-store'
import type { Health, Task } from '../types'
import { AgentTag, PageHeader, SectionTitle } from '../components/Layout'
import { Link, useNavigate } from 'react-router-dom'
import { useAppStore } from '../store'

const today = () => {
  const value = new Date()
  const offset = value.getTimezoneOffset() * 60 * 1000
  return new Date(value.getTime() - offset).toISOString().slice(0, 10)
}

const formatDuration = (seconds: number) => `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60).toString().padStart(2, '0')}m`
const todayLabel = () => new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase()

export function Dashboard() {
  const navigate = useNavigate()
  const { currentProject } = useAppStore()
  const { conversations, selectConversation } = useConversationStore()
  const { running: focusRunning, start: startFocus, pause: pauseFocus, sync: syncFocus, getSeconds } = useFocusStore()
  const [health, setHealth] = useState<Health | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [memoryCount, setMemoryCount] = useState(0)
  const [focusSeconds, setFocusSeconds] = useState(0)

  const refresh = () => {
    setLoading(true); setError('')
    Promise.all([getHealth(), getTasks(today()), searchMemory('')]).then(([nextHealth, nextTasks, memories]) => { setHealth(nextHealth); setTasks(nextTasks); setMemoryCount(memories.length) }).catch((reason) => setError(reason instanceof Error ? reason.message : '总览数据加载失败')).finally(() => setLoading(false))
  }
  useEffect(() => { refresh() }, [])
  useEffect(() => { const update = () => { syncFocus(); setFocusSeconds(getSeconds()) }; update(); const timer = window.setInterval(update, 1000); return () => window.clearInterval(timer) }, [getSeconds, syncFocus])

  const visibleTasks = useMemo(() => currentProject.id === 'all' ? tasks : tasks.filter((task) => !task.project || task.project === currentProject.id), [currentProject.id, tasks])
  const pending = visibleTasks.filter((task) => !task.done).length
  const completedTaskMinutes = visibleTasks.filter((task) => task.done).reduce((total, task) => total + task.duration, 0)
  const focusTotalSeconds = focusSeconds + completedTaskMinutes * 60
  const recentConversations = conversations.filter((conversation) => conversation.project === currentProject.name).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).slice(0, 3)
  const toggleTask = async (task: Task) => {
    try { await completeTask(task.id); setTasks((current) => current.map((item) => item.id === task.id ? { ...item, done: !item.done } : item)) } catch (reason) { setError(reason instanceof Error ? reason.message : '任务更新失败') }
  }
  const openConversation = (id: string) => { selectConversation(id); navigate('/chat') }

  return <div className="page"><PageHeader eyebrow={todayLabel()} title="早上好，Lin。" description="今天给认知系统一个清晰的起点。" action={<button className="button ghost" onClick={refresh}><RefreshCw size={15} className={loading ? 'spin' : ''} />刷新状态</button>} />
    {error && <div className="connection-note dashboard-error"><span className="status-dot error" />{error}</div>}
    <section className="hero-grid"><div className="focus-panel"><div className="focus-glow" /><div className="eyebrow">TODAY'S FOCUS</div><h2>把想法变成<br /><em>下一步动作</em></h2><p>{pending > 0 ? `还有 ${pending} 个任务待完成，从「${visibleTasks.find((task) => !task.done)?.title ?? '下一步动作'}」开始。` : '今天的任务已完成，可以记录复盘或开启新的对话。'}</p><div className="focus-actions"><Link className="button primary" to="/chat"><MessageSquare size={16} />开始对话</Link><Link className="button soft" to="/capture"><Plus size={16} />快速记录</Link></div><div className="focus-foot"><span><span className="status-dot live" />{health?.status === 'ok' ? 'Orchestrator 在线' : '正在检查服务'}</span><span className="muted">{focusRunning ? '专注计时进行中' : '准备开始专注'}</span></div></div><div className="metrics-grid"><Link className="metric-card metric-link" to="/tasks"><div className="metric-icon coral"><Target size={17} /></div><span>今日待办</span><strong>{pending}<small> 项</small></strong><div className="metric-note"><TrendingUp size={13} /> {visibleTasks.length ? `${visibleTasks.filter((task) => task.done).length} 项已完成` : '打开清单添加任务'}</div></Link><div className="metric-card focus-metric"><div className="metric-icon teal"><Clock3 size={17} /></div><span>专注时间</span><strong>{formatDuration(focusTotalSeconds)}</strong><div className="progress"><span style={{ width: `${Math.min(100, Math.round((focusTotalSeconds / (3 * 60 * 60)) * 100))}%` }} /></div><div className="metric-note"><button className="text-link focus-control" onClick={() => focusRunning ? pauseFocus() : startFocus()}>{focusRunning ? <><Pause size={12} />暂停计时</> : <><Play size={12} />开始计时</>}</button><span>目标 3 小时</span></div></div><Link className="metric-card wide metric-link" to="/search"><div className="metric-icon brass"><Sparkles size={17} /></div><span>知识库记忆</span><strong>{memoryCount}<small> 条</small></strong><div className="metric-note">打开知识检索管理</div></Link></div></section>
    <div className="dashboard-grid"><section className="panel"><SectionTitle title="最近对话" meta={recentConversations.length ? `当前项目 · ${recentConversations.length} 条` : '当前项目暂无对话'} action={<Link className="text-link" to="/chat">查看全部 <ArrowUpRight size={14} /></Link>} /><div className="conversation-list">{recentConversations.length === 0 ? <div className="empty-state"><MessageSquare size={17} />还没有对话，<Link className="text-link" to="/chat">开始第一条</Link></div> : recentConversations.map((conversation) => { const last = conversation.messages[conversation.messages.length - 1]; return <button className="conversation conversation-link" key={conversation.id} onClick={() => openConversation(conversation.id)}><div className="conversation-icon"><MessageSquare size={16} /></div><div><strong>{conversation.title}</strong><p>{last?.content.slice(0, 64) || '尚未发送消息'}</p><div className="conversation-meta"><AgentTag>{conversation.agent || 'Orchestrator'}</AgentTag><span>{new Date(conversation.updatedAt).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span></div></div></button> })}</div></section><section className="panel"><SectionTitle title="今日微任务" meta={`${pending} 项待完成`} action={<Link className="text-link" to="/tasks">打开清单 <ArrowUpRight size={14} /></Link>} /><div className="task-list">{visibleTasks.length === 0 ? <div className="empty-state">今天还没有任务，<Link className="text-link" to="/tasks">添加一个动作</Link></div> : visibleTasks.slice(0, 4).map((task) => <div className={`task-row ${task.done ? 'done' : ''}`} key={task.id}><button className="check-box task-check" onClick={() => void toggleTask(task)} aria-label={task.done ? '标记未完成' : '标记完成'}>{task.done && <Check size={13} />}</button><Link to="/tasks"><div><strong>{task.title}</strong><span><Clock3 size={12} /> {task.duration} min</span></div></Link></div>)}</div></section></div>
    <section className="agent-strip"><div><div className="eyebrow">AGENT CONSTELLATION</div><h2>五个角色，各司其职。</h2></div><div className="agent-chips">{health?.agents.map((agent) => <span key={agent.id} className="agent-chip"><span className="chip-dot" style={{ background: agent.color }} />{agent.name}<small>{agent.role}</small></span>) ?? <span className="muted">正在连接 Agent 服务...</span>}</div></section>
  </div>
}
