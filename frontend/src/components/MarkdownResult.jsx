import ReactMarkdown from 'react-markdown'
import { isMarkdown } from '../utils/markdown'

/**
 * Style overrides for markdown elements — avoids needing @tailwindcss/typography.
 */
const markdownComponents = {
  h1: ({ children }) => <h1 className="text-lg font-bold mt-3 mb-1">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-bold mt-2 mb-1">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-bold mt-2 mb-1">{children}</h3>,
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-0.5">{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-violet-400 pl-3 italic text-gray-300 mb-2">{children}</blockquote>
  ),
  code: ({ children, className }) => {
    const isInline = !className
    if (isInline) {
      return <code className="bg-gray-800 px-1 py-0.5 rounded text-sm text-violet-300">{children}</code>
    }
    return (
      <pre className="bg-gray-800 rounded-lg p-3 overflow-x-auto mb-2 text-sm">
        <code className={className}>{children}</code>
      </pre>
    )
  },
  pre: ({ children }) => <>{children}</>,
  table: ({ children }) => (
    <div className="overflow-x-auto mb-2">
      <table className="min-w-full border-collapse border border-gray-600 text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border border-gray-600 px-2 py-1 bg-gray-800 font-semibold">{children}</th>,
  td: ({ children }) => <td className="border border-gray-600 px-2 py-1">{children}</td>,
  hr: () => <hr className="border-gray-700 my-3" />,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-violet-400 hover:underline">{children}</a>
  ),
}

export default function MarkdownResult({ content, className = '' }) {
  if (isMarkdown(content)) {
    return (
      <div className={`text-sm leading-relaxed ${className}`}>
        <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
      </div>
    )
  }

  return (
    <pre className={`whitespace-pre-wrap text-sm leading-relaxed ${className}`}>
      {content}
    </pre>
  )
}