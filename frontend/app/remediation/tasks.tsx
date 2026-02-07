'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
    Search,
    Filter,
    PlayCircle,
    CheckCircle,
    XCircle,
    Clock,
    AlertTriangle,
    RotateCcw,
    Download,
    Eye
} from 'lucide-react'

interface RemediationTask {
    id: string
    action_type: string
    resource_id: string
    resource_type: string
    account_id: string
    region: string
    status: string
    requested_by: string
    requested_at: string
    executed_at?: string
    dry_run: boolean
    execution_log: any[]
}

export function RemediationTasks() {
    const [tasks, setTasks] = useState<RemediationTask[]>([])
    const [filteredTasks, setFilteredTasks] = useState<RemediationTask[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [statusFilter, setStatusFilter] = useState('all')
    const [resourceTypeFilter, setResourceTypeFilter] = useState('all')
    const [selectedTask, setSelectedTask] = useState<RemediationTask | null>(null)

    useEffect(() => {
        fetchTasks()
    }, [])

    useEffect(() => {
        filterTasks()
    }, [tasks, searchTerm, statusFilter, resourceTypeFilter])

    const fetchTasks = async () => {
        setIsLoading(true)
        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch('http://localhost:8000/api/v1/remediation/tasks?limit=100', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setTasks(data.tasks || [])
            }
        } catch (error) {
            console.error('Failed to fetch tasks:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const filterTasks = () => {
        let filtered = tasks

        if (searchTerm) {
            filtered = filtered.filter(task =>
                task.action_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
                task.resource_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                task.resource_type.toLowerCase().includes(searchTerm.toLowerCase())
            )
        }

        if (statusFilter !== 'all') {
            filtered = filtered.filter(task => task.status === statusFilter)
        }

        if (resourceTypeFilter !== 'all') {
            filtered = filtered.filter(task => task.resource_type === resourceTypeFilter)
        }

        setFilteredTasks(filtered)
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-4 h-4 text-green-600" />
            case 'failed':
                return <XCircle className="w-4 h-4 text-red-600" />
            case 'pending':
                return <Clock className="w-4 h-4 text-yellow-600" />
            case 'in_progress':
                return <PlayCircle className="w-4 h-4 text-blue-600" />
            default:
                return <AlertTriangle className="w-4 h-4 text-gray-600" />
        }
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'bg-green-100 text-green-800'
            case 'failed':
                return 'bg-red-100 text-red-800'
            case 'pending':
                return 'bg-yellow-100 text-yellow-800'
            case 'in_progress':
                return 'bg-blue-100 text-blue-800'
            default:
                return 'bg-gray-100 text-gray-800'
        }
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString()
    }

    const executeTask = async (taskId: string, dryRun: boolean) => {
        try {
            const token = localStorage.getItem('access_token')
            await fetch('http://localhost:8000/api/v1/remediation/execute', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    finding_id: taskId,
                    action_type: 'retry',
                    dry_run: dryRun
                })
            })

            fetchTasks()
        } catch (error) {
            console.error('Failed to execute task:', error)
        }
    }

    const rollbackTask = async (taskId: string) => {
        try {
            const token = localStorage.getItem('access_token')
            await fetch(`http://localhost:8000/api/v1/remediation/tasks/${taskId}/rollback`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            fetchTasks()
        } catch (error) {
            console.error('Failed to rollback task:', error)
        }
    }

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Remediation Tasks</CardTitle>
                    <CardDescription>Loading tasks...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-16 bg-gray-100 animate-pulse rounded"></div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        )
    }

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        <div>
                            <CardTitle>Remediation Tasks</CardTitle>
                            <CardDescription>
                                View and manage all remediation actions
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm" className="gap-2">
                                <Download className="w-4 h-4" />
                                Export
                            </Button>
                            <Button onClick={fetchTasks} variant="outline" size="sm">
                                Refresh
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Filters */}
                    <div className="flex flex-col lg:flex-row gap-4 mb-6">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                            <Input
                                placeholder="Search tasks..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-10"
                            />
                        </div>

                        <div className="flex gap-2">
                            <Select value={statusFilter} onValueChange={setStatusFilter}>
                                <SelectTrigger className="w-40">
                                    <SelectValue placeholder="Status" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Status</SelectItem>
                                    <SelectItem value="pending">Pending</SelectItem>
                                    <SelectItem value="in_progress">In Progress</SelectItem>
                                    <SelectItem value="completed">Completed</SelectItem>
                                    <SelectItem value="failed">Failed</SelectItem>
                                </SelectContent>
                            </Select>

                            <Select value={resourceTypeFilter} onValueChange={setResourceTypeFilter}>
                                <SelectTrigger className="w-40">
                                    <SelectValue placeholder="Resource Type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Resources</SelectItem>
                                    <SelectItem value="AWS::EC2::Instance">EC2</SelectItem>
                                    <SelectItem value="AWS::S3::Bucket">S3</SelectItem>
                                    <SelectItem value="AWS::RDS::DBInstance">RDS</SelectItem>
                                    <SelectItem value="AWS::IAM::Role">IAM</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Tasks Table */}
                    <div className="space-y-4">
                        {filteredTasks.length === 0 ? (
                            <div className="text-center py-12 text-gray-500">
                                <Filter className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                                <p>No tasks found matching your filters</p>
                            </div>
                        ) : (
                            filteredTasks.map((task) => (
                                <div
                                    key={task.id}
                                    className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
                                >
                                    <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                {getStatusIcon(task.status)}
                                                <Badge className={getStatusColor(task.status)}>
                                                    {task.status.replace('_', ' ')}
                                                </Badge>
                                                {task.dry_run && (
                                                    <Badge className="bg-gray-100 text-gray-800">
                                                        Dry Run
                                                    </Badge>
                                                )}
                                                <span className="text-sm text-gray-500">
                                                    {formatDate(task.requested_at)}
                                                </span>
                                            </div>

                                            <div className="mb-2">
                                                <h4 className="font-medium">
                                                    {task.action_type.replace(/_/g, ' ')}
                                                </h4>
                                                <p className="text-sm text-gray-600">
                                                    {task.resource_type} • {task.resource_id}
                                                </p>
                                                <p className="text-sm text-gray-500">
                                                    Account: {task.account_id} • Region: {task.region}
                                                </p>
                                            </div>

                                            <div className="text-sm text-gray-500">
                                                Requested by {task.requested_by}
                                                {task.executed_at && ` • Executed ${formatDate(task.executed_at)}`}
                                            </div>
                                        </div>

                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => setSelectedTask(task)}
                                            >
                                                <Eye className="w-4 h-4" />
                                                Details
                                            </Button>

                                            {task.status === 'failed' && (
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => executeTask(task.id, false)}
                                                >
                                                    <PlayCircle className="w-4 h-4" />
                                                    Retry
                                                </Button>
                                            )}

                                            {task.status === 'completed' && !task.dry_run && (
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => rollbackTask(task.id)}
                                                >
                                                    <RotateCcw className="w-4 h-4" />
                                                    Rollback
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Task Details Modal */}
            {selectedTask && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
                        <div className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-xl font-semibold">Task Details</h3>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setSelectedTask(null)}
                                >
                                    ✕
                                </Button>
                            </div>

                            <div className="space-y-6">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <div className="text-sm text-gray-500">Task ID</div>
                                        <div className="font-medium">{selectedTask.id}</div>
                                    </div>
                                    <div>
                                        <div className="text-sm text-gray-500">Status</div>
                                        <Badge className={getStatusColor(selectedTask.status)}>
                                            {selectedTask.status}
                                        </Badge>
                                    </div>
                                    <div>
                                        <div className="text-sm text-gray-500">Action Type</div>
                                        <div className="font-medium">{selectedTask.action_type}</div>
                                    </div>
                                    <div>
                                        <div className="text-sm text-gray-500">Resource</div>
                                        <div className="font-medium">{selectedTask.resource_type}</div>
                                    </div>
                                </div>

                                <div>
                                    <h4 className="font-medium mb-2">Execution Log</h4>
                                    <div className="bg-gray-50 rounded-lg p-4">
                                        {selectedTask.execution_log.length > 0 ? (
                                            <div className="space-y-2">
                                                {selectedTask.execution_log.map((log, index) => (
                                                    <div key={index} className="text-sm">
                                                        <span className="text-gray-500">
                                                            {new Date(log.timestamp).toLocaleTimeString()}:
                                                        </span>{' '}
                                                        <span className="text-gray-800">{log.message}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="text-gray-500 text-center py-4">
                                                No execution log available
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="flex justify-end gap-2">
                                    <Button variant="outline" onClick={() => setSelectedTask(null)}>
                                        Close
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}