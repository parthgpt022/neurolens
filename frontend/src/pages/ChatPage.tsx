// frontend/src/pages/ChatPage.tsx
import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, Mic, MicOff, Loader2, FileText, ChevronDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { chatApi, type ChatMessage, type Citation } from '../api/services'
import { useVoice } from '../hooks/useVoice'
import clsx from 'clsx'

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const voice = useVoice()

  // When voice transcript arrives, put it in the input box
  useEffect(() => {
    if (voice.transcript) setInput(voice.transcript)
  }, [voice.transcript])

  const { data: session, isLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => chatApi.getSession(sessionId!).then((r) => r.data),
    enabled: !!sessionId && sessionId !== 'new',
    onSuccess: (data) => setMessages(data.messages || []),
  })

  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      chatApi.sendMessage(sessionId!, message).then((r) => r.data),
    onMutate: (message) => {
      // Optimistically add user message
      const optimistic: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
        citations: null,
        latency_ms: null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, optimistic])
    },
    onSuccess: (data) => {
      const assistantMsg: ChatMessage = {
        id: data.message_id,
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        latency_ms: data.latency_ms,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      voice.clearTranscript()
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const msg = input.trim()
    if (!msg || sendMutation.isPending || !sessionId) return
    setInput('')
    sendMutation.mutate(msg)
  }

  if (sessionId === 'new') {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <div className="text-center">
          <FileText className="mx-auto mb-3" size={32} />
          <p className="text-sm">Select documents from the library and click "Start Chat"</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-gray-300" size={24} />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 bg-white flex items-center gap-3">
        <div>
          <h2 className="font-medium text-gray-900 text-sm">{session?.title || 'Chat'}</h2>
          <p className="text-xs text-gray-400">
            {session?.document_ids.length} document{session?.document_ids.length !== 1 ? 's' : ''} · RAG + Llama 3
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 py-12">
            <p className="text-sm">Ask anything about the uploaded document(s).</p>
            <p className="text-xs mt-1 text-gray-300">Try: "What is the total amount?" or "Summarize this document"</p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {sendMutation.isPending && (
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 size={14} className="animate-spin" />
            <span className="text-xs">Thinking…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-100 bg-white">
        {voice.error && (
          <p className="text-xs text-red-400 mb-2">{voice.error}</p>
        )}
        <div className="flex items-end gap-3">
          <div className="flex-1 flex items-end gap-2 border border-gray-200 rounded-xl px-4 py-3 focus-within:border-brand-400 transition-colors bg-gray-50">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
              }}
              placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
              className="flex-1 resize-none bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none max-h-32"
              rows={1}
            />
          </div>

          {/* Voice button */}
          <button
            onClick={voice.state === 'recording' ? voice.stopRecording : voice.startRecording}
            disabled={voice.state === 'transcribing'}
            className={clsx(
              'p-3 rounded-xl transition-colors flex-shrink-0',
              voice.state === 'recording'
                ? 'bg-red-100 text-red-500 hover:bg-red-200 animate-pulse'
                : voice.state === 'transcribing'
                ? 'bg-gray-100 text-gray-300'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            )}
            title={voice.state === 'recording' ? 'Stop recording' : 'Voice input'}
          >
            {voice.state === 'transcribing' ? (
              <Loader2 size={18} className="animate-spin" />
            ) : voice.state === 'recording' ? (
              <MicOff size={18} />
            ) : (
              <Mic size={18} />
            )}
          </button>

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!input.trim() || sendMutation.isPending}
            className="p-3 bg-brand-500 text-white rounded-xl hover:bg-brand-600 transition-colors flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-xs text-gray-300 mt-2 text-center">
          Answers grounded in your documents · Powered by Llama 3 + NPU embeddings
        </p>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [showCitations, setShowCitations] = useState(false)
  const isUser = message.role === 'user'

  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div className={clsx('max-w-2xl', isUser ? 'items-end' : 'items-start', 'flex flex-col gap-1')}>
        <div
          className={clsx(
            'rounded-2xl px-4 py-3 text-sm',
            isUser
              ? 'bg-brand-500 text-white rounded-br-sm'
              : 'bg-white border border-gray-100 text-gray-900 rounded-bl-sm shadow-sm'
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-sm max-w-none">
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setShowCitations((s) => !s)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              <ChevronDown
                size={12}
                className={clsx('transition-transform', showCitations && 'rotate-180')}
              />
              {message.citations.length} source{message.citations.length > 1 ? 's' : ''}
              {message.latency_ms && (
                <span className="ml-2 text-gray-300">· {message.latency_ms.toFixed(0)}ms</span>
              )}
            </button>
            {showCitations && (
              <div className="mt-2 space-y-2">
                {message.citations.map((c) => (
                  <CitationCard key={c.index} citation={c} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-lg p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500">
          Source {citation.index} · Page {citation.page_number}
        </span>
        <span className="text-xs text-gray-300">
          {(citation.relevance_score * 100).toFixed(0)}% match
        </span>
      </div>
      <p className="text-xs text-gray-600 leading-relaxed">{citation.text}</p>
    </div>
  )
}
