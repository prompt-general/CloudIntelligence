'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardHeader } from '@/components/dashboard/header'
import { DashboardSidebar } from '@/components/dashboard/sidebar'
import { ComplianceScoreCard } from '@/components/compliance/score-card'
import { FrameworkOverview } from '@/components/compliance/framework-overview'
import { ComplianceTimeline } from '@/components/compliance/timeline'
import { ControlList } from '@/components/compliance/control-list'
import { EvidenceLibrary } from '@/components/compliance/evidence-library'
import { ReportGenerator } from '@/components/compliance/report-generator'
import { useAuth } from '@/lib/auth'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import {
    FileCheck,
    Shield,
    TrendingUp,
    ListChecks,
    FileText,
    Download,
    RefreshCw,
    AlertTriangle
} from 'lucide-react'

interface ComplianceDashboardData {
    summary: {
        average_score: number
        compliant_frameworks: number
        total_frameworks: number
        high_risk_controls: number
    }
    frameworks: any[]
    timeline: any[]
    high_risk_controls: any[]
}

export default function CompliancePage() {
    const router = useRouter()
    const { user, isLoading: authLoading } = useAuth()
    const [dashboardData, setDashboardData] = useState<ComplianceDashboardData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [activeTab, setActiveTab] = useState('overview')
    const [assessing, setAssessing] = useState(false)

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login')
        }
    }, [user, authLoading, router])

    useEffect(() => {
        fetchComplianceData()
    }, [user])

    const fetchComplianceData = async () => {
        if (!user) return

        setIsLoading(true)
        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch('http://localhost:8000/api/v1/compliance/dashboard', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setDashboardData(data)
            }
        } catch (error) {
            console.error('Failed to fetch compliance data:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const runAssessment = async () => {
        setAssessing(true)
        try {
            const token = localStorage.getItem('access_token')
            await fetch('http://localhost:8000/api/v1/compliance/assess', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    frameworks: null,
                    force_refresh: true
                })
            })

            // Poll for completion
            setTimeout(fetchComplianceData, 5000)
        } catch (error) {
            console.error('Failed to run assessment:', error)
        } finally {
            setAssessing(false)
        }
    }

    if (authLoading || isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading compliance dashboard...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <DashboardHeader user={user} />

            <div className="flex">
                <DashboardSidebar active="compliance" />

                <main className="flex-1 p-6 lg:p-8">
                    {/* Header */}
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
                        <div>
                            <h1 className="text-3xl font-bold">Compliance Automation</h1>
                            <p className="text-gray-600 mt-2">
                                Automated compliance monitoring, evidence collection, and audit reporting
                            </p>
                        </div>

                        <div className="flex items-center gap-3">
                            <Button
                                variant="outline"
                                className="gap-2"
                                onClick={fetchComplianceData}
                                disabled={assessing}
                            >
                                <RefreshCw className={`w-4 h-4 ${assessing ? 'animate-spin' : ''}`} />
                                Refresh
                            </Button>
                            <Button
                                className="gap-2 bg-green-600 hover:bg-green-700"
                                onClick={runAssessment}
                                disabled={assessing}
                            >
                                <FileCheck className="w-4 h-4" />
                                {assessing ? 'Assessing...' : 'Run Assessment'}
                            </Button>
                        </div>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">Overall Score</p>
                                    <p className={`text-3xl font-bold mt-2 ${(dashboardData?.summary.average_score || 0) >= 80 ? 'text-green-600' :
                                            (dashboardData?.summary.average_score || 0) >= 60 ? 'text-yellow-600' : 'text-red-600'
                                        }`}>
                                        {Math.round(dashboardData?.summary.average_score || 0)}%
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                                    <FileCheck className="w-6 h-6 text-blue-600" />
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">Compliant Frameworks</p>
                                    <p className="text-3xl font-bold mt-2">
                                        {dashboardData?.summary.compliant_frameworks || 0}/{dashboardData?.summary.total_frameworks || 0}
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center">
                                    <Shield className="w-6 h-6 text-green-600" />
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">High Risk Controls</p>
                                    <p className="text-3xl font-bold mt-2">
                                        {dashboardData?.summary.high_risk_controls || 0}
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-red-100 flex items-center justify-center">
                                    <AlertTriangle className="w-6 h-6 text-red-600" />
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">Last Assessment</p>
                                    <p className="text-lg font-bold mt-2">
                                        {dashboardData?.frameworks[0]?.last_assessed
                                            ? new Date(dashboardData.frameworks[0].last_assessed).toLocaleDateString()
                                            : 'Never'
                                        }
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center">
                                    <TrendingUp className="w-6 h-6 text-purple-600" />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Main Content Tabs */}
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                        <TabsList className="grid grid-cols-2 lg:grid-cols-6">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="frameworks">Frameworks</TabsTrigger>
                            <TabsTrigger value="controls">Controls</TabsTrigger>
                            <TabsTrigger value="timeline">Timeline</TabsTrigger>
                            <TabsTrigger value="evidence">Evidence</TabsTrigger>
                            <TabsTrigger value="reports">Reports</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2 space-y-6">
                                    <ComplianceScoreCard
                                        score={dashboardData?.summary.average_score || 0}
                                        frameworks={dashboardData?.frameworks || []}
                                    />
                                    <ComplianceTimeline timeline={dashboardData?.timeline || []} />
                                </div>
                                <div className="space-y-6">
                                    <FrameworkOverview frameworks={dashboardData?.frameworks || []} />
                                    {dashboardData?.high_risk_controls && dashboardData.high_risk_controls.length > 0 && (
                                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                                            <h3 className="font-semibold mb-4">High Risk Controls</h3>
                                            <div className="space-y-3">
                                                {dashboardData.high_risk_controls.slice(0, 3).map((control: any) => (
                                                    <div key={control.control_id} className="p-3 bg-red-50 rounded-lg">
                                                        <div className="font-medium text-red-800">{control.control_id}</div>
                                                        <div className="text-sm text-red-600 truncate">{control.title}</div>
                                                        <div className="text-xs text-red-500 mt-1">
                                                            Risk: {Math.round(control.risk_score)}%
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="frameworks">
                            <div className="space-y-6">
                                {dashboardData?.frameworks.map((framework) => (
                                    <div key={framework.framework} className="bg-white rounded-xl border border-gray-200 p-6">
                                        <div className="flex items-center justify-between mb-4">
                                            <div>
                                                <h3 className="font-semibold text-lg">{framework.framework.toUpperCase()}</h3>
                                                <p className="text-gray-600">
                                                    {framework.passed}/{framework.total} controls passed
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <div className={`text-2xl font-bold ${framework.score >= 80 ? 'text-green-600' :
                                                        framework.score >= 60 ? 'text-yellow-600' : 'text-red-600'
                                                    }`}>
                                                    {Math.round(framework.score)}%
                                                </div>
                                                <div className="text-sm text-gray-500">
                                                    {framework.status}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <Button size="sm" variant="outline">
                                                View Details
                                            </Button>
                                            <Button size="sm" variant="outline">
                                                Generate Report
                                            </Button>
                                            <Button size="sm">
                                                Run Assessment
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </TabsContent>

                        <TabsContent value="controls">
                            <ControlList />
                        </TabsContent>

                        <TabsContent value="timeline">
                            <ComplianceTimeline timeline={dashboardData?.timeline || []} detailed />
                        </TabsContent>

                        <TabsContent value="evidence">
                            <EvidenceLibrary />
                        </TabsContent>

                        <TabsContent value="reports">
                            <ReportGenerator />
                        </TabsContent>
                    </Tabs>
                </main>
            </div>
        </div>
    )
}