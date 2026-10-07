import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { BrainCircuit, CheckSquare, ChevronDown, CircleHelp, Command, LayoutDashboard, Menu, MessageSquare, Moon, Plus, Search, Settings, Sun, X, Zap } from 'lucide-react'
import { createProject, getProjects } from '../api'
import { useAppStore } from '../store'

const navItems = [
  { to: '/', label: '总览', icon: LayoutDashboard },
  { to: '/chat', label: '对话中枢', icon: MessageSquare },
  { to: '/capture', label: '灵感速记', icon: Zap },
  { to: '/tasks', label: '执行清单', icon: CheckSquare },
  { to: '/search', label: '知识检索', icon: Search },
]

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [projectMenu, setProjectMenu] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const location = useLocation()
  const { projects, currentProject, setProjects, setCurrentProject, theme, toggleTheme } = useAppStore()

  useEffect(() => { getProjects().then(setProjects).catch(() => undefined) }, [setProjects])
  useEffect(() => { setMobileOpen(false) }, [location.pathname])
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])
  const addProject = async () => { const name = newProjectName.trim(); if (!name) return; const project = await createProject(name); setProjects([...projects, project]); setCurrentProject(project); setNewProjectName(''); setProjectMenu(false) }

  return (
    <div className="app-shell">
      <header className="mobile-header">
        <button className="icon-button" onClick={() => setMobileOpen(true)} aria-label="打开导航"><Menu size={20} /></button>
        <div className="brand-mark"><BrainCircuit size={18} /><span>SN<span className="accent">/</span>HELPER</span></div>
        <button className="icon-button" onClick={toggleTheme} aria-label="切换主题">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
      </header>
      <aside className={`sidebar ${mobileOpen ? 'is-open' : ''}`}>
        <div className="sidebar-top">
          <div className="brand-mark"><span className="brand-glyph"><BrainCircuit size={18} /></span><span>SN<span className="accent">/</span>HELPER</span></div>
          <button className="icon-button sidebar-close" onClick={() => setMobileOpen(false)} aria-label="关闭导航"><X size={18} /></button>
          <div className="eyebrow">PERSONAL COGNITIVE EXOSKELETON</div>
        </div>
        <div className="project-switcher">
          <div className="field-label">当前工作区</div>
          <button className="project-button" onClick={() => setProjectMenu(!projectMenu)}>
            <span className="project-dot" style={{ background: currentProject.color ?? '#d2a55e' }} />
            <span>{currentProject.name}</span><ChevronDown size={15} className="muted" />
          </button>
          {projectMenu && <div className="project-menu">{projects.map((project) => <button key={project.id} onClick={() => { setCurrentProject(project); setProjectMenu(false) }}><span className="project-dot" style={{ background: project.color ?? '#d2a55e' }} />{project.name}</button>)}<div className="project-create"><input autoFocus value={newProjectName} onChange={(event) => setNewProjectName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') addProject(); if (event.key === 'Escape') setProjectMenu(false) }} placeholder="新项目名称" /><button onClick={addProject} aria-label="创建项目"><Plus size={14} /></button></div></div>}
        </div>
        <nav className="main-nav">{navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={17} /><span>{label}</span></NavLink>)}</nav>
        <div className="sidebar-footer">
          <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Settings size={17} /><span>系统设置</span></NavLink>
          <div className="agent-status" title="Agent 服务状态：当前本地实例中有 5 个角色可用"><span className="status-dot live" /><div><strong>Agent 系统在线</strong><small>5 个角色已就绪</small></div><CircleHelp size={15} className="muted" /></div>
          <div className="profile" title="当前工作实例身份，用于区分本地或远程控制面板"><div className="avatar">L</div><div><strong>Lin / 主理人</strong><small>Local instance</small></div><Command size={15} className="muted" /></div>
        </div>
      </aside>
      {mobileOpen && <button className="scrim" onClick={() => setMobileOpen(false)} aria-label="关闭导航" />}
      <main className="content"><Outlet /></main>
    </div>
  )
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: React.ReactNode }) {
  return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p className="page-description">{description}</p>}</div>{action}</div>
}

export function SectionTitle({ title, meta, action }: { title: string; meta?: string; action?: React.ReactNode }) { return <div className="section-title"><div><h2>{title}</h2>{meta && <span>{meta}</span>}</div>{action}</div> }
export function AgentTag({ children }: { children: React.ReactNode }) { return <span className={`agent-tag agent-${String(children).toLowerCase()}`}><span className="tag-pip" />{children}</span> }
