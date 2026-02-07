'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, AlertCircle, DollarSign, Shield } from 'lucide-react'
import { useWebSocket } from '@/lib/websocket'

interface ActivityItem {
    id: string
    action: string
    resource_type: string
    resource_name: string
    actor: string
    timestamp: string
    details: string
}

export function RecentActivity() {
    const [activities, setActivities] = useState<ActivityItem[]>([])

    const { lastMessage } = useWebSocket({
        url: 'ws://localhost:8000/ws/secure',
        autoConnect: true,
        onMessage: (message) => {
            if (message.type === 'resource_change') {
                // Add new activities from WebSocket
                const newActivities = message.changes.map((change: any) => ({
                    id: change.id,
                    action: change.action,
                    resource_type: change.resource_type,
                    resource_name: change.resource_name,
                    actor: 'system',
                    timestamp: change.timestamp,
                    details: `${change.action} ${change.resource_type} resource`
                }))

                setActivities(prev => [...newActivities, ...prev.slice(0, 4)]) // Keep latest 5
            }
        }
    })

    useEffect(() => {
        // Fetch initial activities
        const fetchActivities = async () => {
            try {
                const token = localStorage.getItem('access_token')
                const response = await fetch('http://localhost:8000/api/v1/dashboard', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })

                if (response.ok) {
                    const data = await response.json()
                    setActivities(data.recent_activities || [])
                }
            } catch (error) {
                console.error('Failed to fetch activities:', error)
            }
        }

        fetchActivities()
    }, [])

    const getActionIcon = (action: string) => {
        if (action.includes('alert')) return <AlertCircle className="w-4 h-4 text-red-500" />
        if (action.includes('cost')) return <DollarSign className="w-4 h-4 text-yellow-500" />
        if (action.includes('security')) return <Shield className="w-4 h-4 text-blue-500" />
        return <Activity className="w-4 h-4 text-gray-500" />
    }

    const getActionColor = (action: string) => {
        if (action.includes('alert')) return 'bg-red-100 text-red-800'
        if (action.includes('security')) return 'bg-blue-100 text-blue-800'
        if (action.includes('cost')) return 'bg-yellow-100 text-yellow-800'
        return 'bg-gray-100 text-gray-800'
    }

    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)

        if (diffMins < 1) return 'Just now'
        if (diffMins < 60) return `${diffMins}m ago`
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
        return date.toLocaleDateString()
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5" />
                    Recent Activity
                </CardTitle>
                <CardDescription>Real-time updates from your cloud</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {activities.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            No recent activity
                        </div>
                    ) : (
                        activities.map((activity) => (
                            <div key={activity.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50">
                                <div className="flex-shrink-0 mt-1">
                                    {getActionIcon(activity.action)}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <Badge className={getActionColor(activity.action)}>
                                            {activity.action}
                                        </Badge>
                                        <span className="text-sm text-gray-500">
                                            {formatTime(activity.timestamp)}
                                        </span>
                                    </div>
                                    <p className="text-sm font-medium truncate">
                                        {activity.resource_name}
                                    </p>
                                    <p className="text-sm text-gray-600 truncate">
                                        {activity.details}
                                    </p>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* WebSocket Status Indicator */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-500">Real-time status:</span>
                        <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${lastMessage ? 'bg-green-500 animate-pulse' : 'bg-gray-300'
                                }`} />
                            <span className="text-gray-700">
                                {lastMessage ? 'Live' : 'Connected'}
                            </span>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}