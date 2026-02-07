import { useState, useEffect, useCallback, useRef } from 'react'

type WebSocketMessage = {
    type: string
    [key: string]: any
}

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface UseWebSocketOptions {
    url: string
    autoConnect?: boolean
    onMessage?: (message: WebSocketMessage) => void
    onConnect?: () => void
    onDisconnect?: () => void
    onError?: (error: Event) => void
}

export function useWebSocket({
    url,
    autoConnect = true,
    onMessage,
    onConnect,
    onDisconnect,
    onError
}: UseWebSocketOptions) {
    const [status, setStatus] = useState<WebSocketStatus>('disconnected')
    const [messages, setMessages] = useState<WebSocketMessage[]>([])
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
    const reconnectAttemptsRef = useRef(0)
    const maxReconnectAttempts = 5

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.CONNECTING || wsRef.current?.readyState === WebSocket.OPEN) {
            return
        }

        setStatus('connecting')

        try {
            const token = localStorage.getItem('access_token')
            const wsUrl = token ? `${url}?token=${token}` : url
            const ws = new WebSocket(wsUrl)

            wsRef.current = ws

            ws.onopen = () => {
                setStatus('connected')
                reconnectAttemptsRef.current = 0
                onConnect?.()

                // Send initial ping
                ws.send(JSON.stringify({ type: 'ping' }))

                // Subscribe to default channels
                ws.send(JSON.stringify({
                    type: 'subscribe',
                    channels: ['resource_changes', 'alerts', 'metrics']
                }))
            }

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data)
                    setMessages(prev => [...prev.slice(-9), message]) // Keep last 10 messages
                    setLastMessage(message)
                    onMessage?.(message)
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error)
                }
            }

            ws.onclose = () => {
                setStatus('disconnected')
                onDisconnect?.()

                // Attempt reconnection
                if (reconnectAttemptsRef.current < maxReconnectAttempts) {
                    reconnectTimeoutRef.current = setTimeout(() => {
                        reconnectAttemptsRef.current++
                        connect()
                    }, 1000 * Math.min(30, Math.pow(2, reconnectAttemptsRef.current))) // Exponential backoff
                }
            }

            ws.onerror = (error) => {
                setStatus('error')
                onError?.(error)
            }

        } catch (error) {
            console.error('Failed to create WebSocket:', error)
            setStatus('error')
        }
    }, [url, onMessage, onConnect, onDisconnect, onError])

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
        }

        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }

        setStatus('disconnected')
    }, [])

    const send = useCallback((message: WebSocketMessage) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message))
            return true
        }
        return false
    }, [])

    const sendPing = useCallback(() => {
        return send({ type: 'ping' })
    }, [send])

    const subscribe = useCallback((channels: string[]) => {
        return send({ type: 'subscribe', channels })
    }, [send])

    const unsubscribe = useCallback((channels: string[]) => {
        return send({ type: 'unsubscribe', channels })
    }, [send])

    // Auto-connect on mount
    useEffect(() => {
        if (autoConnect) {
            connect()
        }

        return () => {
            disconnect()
        }
    }, [autoConnect, connect, disconnect])

    // Send periodic pings to keep connection alive
    useEffect(() => {
        if (status !== 'connected') return

        const interval = setInterval(() => {
            sendPing()
        }, 30000) // Ping every 30 seconds

        return () => clearInterval(interval)
    }, [status, sendPing])

    return {
        status,
        messages,
        lastMessage,
        connect,
        disconnect,
        send,
        sendPing,
        subscribe,
        unsubscribe,
        isConnected: status === 'connected'
    }
}