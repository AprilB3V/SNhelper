import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Chat } from './pages/Chat'
import { Capture } from './pages/Capture'
import { Tasks } from './pages/Tasks'
import { Search } from './pages/Search'
import { Settings } from './pages/Settings'
import './styles.css'

export default function App() { return <BrowserRouter><Routes><Route element={<Layout />}><Route path="/" element={<Dashboard />} /><Route path="/chat" element={<Chat />} /><Route path="/capture" element={<Capture />} /><Route path="/tasks" element={<Tasks />} /><Route path="/search" element={<Search />} /><Route path="/settings" element={<Settings />} /></Route></Routes></BrowserRouter> }
