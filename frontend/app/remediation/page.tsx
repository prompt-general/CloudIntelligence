'use client'

import { useState, useEffect } from 'react'
import { DashboardHeader } from '@/components/dashboard/header'
import { DashboardSidebar } from '@/components/dashboard/sidebar'
import { RemediationStats } from '@/components/remediation/stats'
import { RemediationTasks } from '@/components/remediation/tasks'
import { RemediationWorkflows } from '@/components/remediation/workflows'
import { QuickRemediate } from '@/components/remediation/quick-remediate'
import { PendingApprovals } from '@/components/remediation/pending-approvals'
import { useAuth } from '@/lib/auth'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import {
    ShieldCheck,
    PlayCircle,
    ListChecks,
    Workflow,
    Zap,
    AlertTriangle,
    CheckCircle
} from 'lucide-react'

interface RemediationDashboardData {
    statistics: {
        total_tasks: number
        completed_tasks: number
        failed_tasks: number
        pending_tasks: number
        success_rate: number
        estimated_savings: number
        auto_remediations: number
    }
    recent_tasks: any[]
    active_workflows: any[]
}

export default function RemediationPage() {
    const { user, isLoading: authLoading } = useAuth()
    const [dashboardData, setDashboardData] = useState<RemediationDashboardData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [activeTab, setActiveTab] = useState('overview')

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login')
        }
    }, [user, authLoading])

    useEffect(() => {
        fetchRemediationData()
    }, [user])

    const fetchRemediationData = async () => {
        if (!user) return

        setIsLoading(true)
        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch('http://localhost:8000/api/v1/remediation/dashboard', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setDashboardData(data)
            }
        } catch (error) {
            console.error('Failed to fetch remediation data:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const runAutoRemediation = async () => {
        try {
            const token = localStorage.getItem('access_token')
            await fetch('http://localhost:8000/api/v1/remediation/execute', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    finding_id: 'auto_remediation',
                    action_type: 'auto_fix',
                    dry_run: false
                })
            })

            fetchRemediationData()
        } catch (error) {
            console.error('Failed to run auto remediation:', error)
        }
    }

    if (authLoading || isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading remediation center...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <DashboardHeader user={user} />

            <div className="flex">
                <DashboardSidebar active="remediation" />

                <main className="flex-1 p-6 lg:p-8">
                    {/* Header */}
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
                        <div>
                            <h1 className="text-3xl font-bold">Remediation Center</h1>
                            <p className="text-gray-600 mt-2">
                                One-click fixes, approval workflows, and automated remediation
                            </p>
                        </div>

                        <div className="flex items-center gap-3">
                            <Button
                                variant="outline"
                                className="gap-2"
                                onClick={fetchRemediationData}
                            >
                                <Zap className="w-4 h-4" />
                                Refresh
                            </Button>
                            <Button
                                className="gap-2 bg-green-600 hover:bg-green-700"
                                onClick={runAutoRemediation}
                            >
                                <PlayCircle className="w-4 h-4" />
                                Run Auto-Remediation
                            </Button>
                        </div>
                    </div>

                    {/* Stats */}
                    {dashboardData && (
                        <div className="mb-8">
                            <RemediationStats stats={dashboardData.statistics} />
                        </div>
                    )}

                    {/* Main Content Tabs */}
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                        <TabsList className="grid grid-cols-2 lg:grid-cols-5">
                            <TabsTrigger value="overview" className="gap-2">
                                <ShieldCheck className="w-4 h-4" />
                                Overview
                            </TabsTrigger>
                            <TabsTrigger value="tasks" className="gap-2">
                                <ListChecks className="w-4 h-4" />
                                Tasks
                            </TabsTrigger>
                            <TabsTrigger value="workflows" className="gap-2">
                                <Workflow className="w-4 h-4" />
                                Workflows
                            </TabsTrigger>
                            <TabsTrigger value="quick" className="gap-2">
                                <Zap className="w-4 h-4" />
                                Quick Remediate
                            </TabsTrigger>
                            <TabsTrigger value="approvals" className="gap-2">
                                <AlertTriangle className="w-4 h-4" />
                                Approvals
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2">
                                    {dashboardData && (
                                        <div className="space-y-6">
                                            <div className="bg-white rounded-xl border border-gray-200 p-6">
                                                <h3 className="font-semibold mb-4">Recent Remediation Tasks</h3>
                                                <div className="space-y-3">
                                                    {dashboardData.recent_tasks.slice(0, 5).map((task) => (
                                                        <div key={task.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                            <div>
                                                                <div className="font-medium">{task.action_type}</div>
                                                                <div className="text-sm text-gray-500">{task.resource_type}</div>
                                                            </div>
                                                            <div className="flex items-center gap-3">
                                                                <span className={`px-2 py-1 rounded text-xs font-medium ${task.status === 'completed' ? 'bg-green-100 text-green-800' :
                                                                        task.status === 'failed' ? 'bg-red-100 text-red-800' :
                                                                            'bg-yellow-100 text-yellow-800'
                                                                    }`}>
                                                                    {task.status}
                                                                </span>
                                                                <span className="text-sm text-gray-500">
                                                                    {new Date(task.requested_at).toLocaleDateString()}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="bg-white rounded-xl border border-gray-200 p-6">
                                                <h3 className="font-semibold mb-4">Active Workflows</h3>
                                                {dashboardData.active_workflows.length > 0 ? (
                                                    <div className="space-y-3">
                                                        {dashboardData.active_workflows.map((workflow) => (
                                                            <div key={workflow.id} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                                                                <div>
                                                                    <div className="font-medium">Workflow Execution</div>
                                                                    <div className="text-sm text-gray-600">Current step: {workflow.current_step}</div>
                                                                </div>
                                                                <div className="text-sm text-gray-500">
                                                                    Started {new Date(workflow.started_at).toLocaleTimeString()}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="text-center py-8 text-gray-500">
                                                        <Workflow className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                                                        <p>No active workflows</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="space-y-6">
                                    <QuickRemediate />
                                    <PendingApprovals />
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="tasks">
                            <RemediationTasks />
                        </TabsContent>

                        <TabsContent value="workflows">
                            <RemediationWorkflows />
                        </TabsContent>

                        <TabsContent value="quick">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                <QuickRemediate expanded />
                                <div className="bg-white rounded-xl border border-gray-200 p-6">
                                    <h3 className="font-semibold mb-4">Quick Actions</h3>
                                    <div className="space-y-3">
                                        <Button className="w-full justify-start gap-2" variant="outline">
                                            <Zap className="w-4 h-4" />
                                            Fix All Critical Security Issues
                                        </Button>
                                        <Button className="w-full justify-start gap-2" variant="outline">
                                            <CheckCircle className="w-4 h-4" />
                                            Apply All Cost Savings
                                        </Button>
                                        <Button className="w-full justify-start gap-2" variant="outline">
                                            <ShieldCheck className="w-4 h-4" />
                                            Run Compliance Remediation
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="approvals">
                            <PendingApprovals expanded />
                        </TabsContent>
                    </Tabs>
                </main>
            </div>
        </div>
    )
}