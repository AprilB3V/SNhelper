import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

export function Markdown({ children }: { children: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code({ className, children, ...props }) { const match = /language-(\w+)/.exec(className ?? ''); return match ? <SyntaxHighlighter style={oneDark as any} language={match[1]} PreTag="div">{String(children).replace(/\n$/, '')}</SyntaxHighlighter> : <code className={className} {...props}>{children}</code> } }}>{children}</ReactMarkdown>
}
