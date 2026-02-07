'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardHeader } from '@/components/dashboard/header'
import { DashboardSidebar } from '@/components/dashboard/sidebar'
import { SecurityScoreCard } from '@/components/security/score-card'
import { SecurityFindingsTable } from '@/components/security/findings-table'
import { AttackPathVisualizer } from '@/components/security/attack-path-visualizer'
import { ComplianceDashboard } from '@/components/security/compliance-dashboard'
import { TopRisks } from '@/components/security/top-risks'
import { SecurityTrends } from '@/components/security/trends'
import { useAuth } from '@/lib/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import {
    Shield,
    AlertTriangle,
    Target,
    RefreshCw,
    FileText,
    Network,
    TrendingUp
} from 'lucide-react'

interface SecurityDashboardData {
    security_score: number
    findings_summary: {
        total: number
        critical: number
        high: number
        medium: number
        low: number
        new_last_7_days: number
    }
    top_risks: any[]
    trend_data: any[]
    last_updated: string
}

export default function SecurityPage() {
    const router = useRouter()
    const { user, isLoading: authLoading } = useAuth()
    const [dashboardData, setDashboardData] = useState<SecurityDashboardData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [activeTab, setActiveTab] = useState('overview')
    const [scanning, setScanning] = useState(false)

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login')
        }
    }, [user, authLoading, router])

    useEffect(() => {
        fetchSecurityData()
    }, [user])

    const fetchSecurityData = async () => {
        if (!user) return

        setIsLoading(true)
        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch('http://localhost:8000/api/v1/security/dashboard', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setDashboardData(data)
            }
        } catch (error) {
            console.error('Failed to fetch security data:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const runSecurityScan = async () => {
        setScanning(true)
        try {
            const token = localStorage.getItem('access_token')
            await fetch('http://localhost:8000/api/v1/security/scan', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    scan_type: 'full',
                    notify: true
                })
            })

            // Wait a moment and refresh data
            setTimeout(fetchSecurityData, 3000)
        } catch (error) {
            console.error('Failed to run security scan:', error)
        } finally {
            setScanning(false)
        }
    }

    if (authLoading || isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading security intelligence...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <DashboardHeader user={user} />

            <div className="flex">
                <DashboardSidebar active="security" />

                <main className="flex-1 p-6 lg:p-8">
                    {/* Header */}
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
                        <div>
                            <h1 className="text-3xl font-bold">Security Intelligence</h1>
                            <p className="text-gray-600 mt-2">
                                AI-powered security analysis, attack path visualization, and vulnerability management
                            </p>
                        </div>

                        <div className="flex items-center gap-3">
                            <Button
                                variant="outline"
                                className="gap-2"
                                onClick={fetchSecurityData}
                                disabled={scanning}
                            >
                                <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
                                Refresh
                            </Button>
                            <Button
                                className="gap-2 bg-red-600 hover:bg-red-700"
                                onClick={runSecurityScan}
                                disabled={scanning}
                            >
                                <AlertTriangle className="w-4 h-4" />
                                {scanning ? 'Scanning...' : 'Run Security Scan'}
                            </Button>
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Security Score</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className={`text-3xl font-bold ${(dashboardData?.security_score || 0) >= 80 ? 'text-green-600' :
                                        (dashboardData?.security_score || 0) >= 60 ? 'text-yellow-600' : 'text-red-600'
                                    }`}>
                                    {dashboardData?.security_score || 0}/100
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Critical</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold text-red-600">
                                    {dashboardData?.findings_summary.critical || 0}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">High</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold text-orange-600">
                                    {dashboardData?.findings_summary.high || 0}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Total</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold">
                                    {dashboardData?.findings_summary.total || 0}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">New (7d)</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold">
                                    {dashboardData?.findings_summary.new_last_7_days || 0}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Last Scan</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-sm">
                                    {dashboardData?.last_updated
                                        ? new Date(dashboardData.last_updated).toLocaleTimeString()
                                        : 'Never'
                                    }
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Main Content Tabs */}
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                        <TabsList className="grid grid-cols-2 lg:grid-cols-5">
                            <TabsTrigger value="overview" className="gap-2">
                                <Shield className="w-4 h-4" />
                                Overview
                            </TabsTrigger>
                            <TabsTrigger value="findings" className="gap-2">
                                <AlertTriangle className="w-4 h-4" />
                                Findings
                            </TabsTrigger>
                            <TabsTrigger value="attack-paths" className="gap-2">
                                <Network className="w-4 h-4" />
                                Attack Paths
                            </TabsTrigger>
                            <TabsTrigger value="compliance" className="gap-2">
                                <FileText className="w-4 h-4" />
                                Compliance
                            </TabsTrigger>
                            <TabsTrigger value="trends" className="gap-2">
                                <TrendingUp className="w-4 h-4" />
                                Trends
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2 space-y-6">
                                    <SecurityScoreCard
                                        score={dashboardData?.security_score || 0}
                                        findings={dashboardData?.findings_summary}
                                    />
                                    <SecurityTrends trendData={dashboardData?.trend_data || []} />
                                </div>
                                <div className="space-y-6">
                                    <TopRisks risks={dashboardData?.top_risks || []} />
                                    <Card>
                                        <CardHeader>
                                            <CardTitle>Quick Actions</CardTitle>
                                        </CardHeader>
                                        <CardContent className="space-y-3">
                                            <Button className="w-full justify-start gap-2" variant="outline">
                                                <Target className="w-4 h-4" />
                                                View Critical Findings
                                            </Button>
                                            <Button className="w-full justify-start gap-2" variant="outline">
                                                <Network className="w-4 h-4" />
                                                Analyze Attack Paths
                                            </Button>
                                            <Button className="w-full justify-start gap-2" variant="outline">
                                                <FileText className="w-4 h-4" />
                                                Generate Compliance Report
                                            </Button>
                                        </CardContent>
                                    </Card>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="findings">
                            <SecurityFindingsTable />
                        </TabsContent>

                        <TabsContent value="attack-paths">
                            <AttackPathVisualizer />
                        </TabsContent>

                        <TabsContent value="compliance">
                            <ComplianceDashboard />
                        </TabsContent>

                        <TabsContent value="trends">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Security Trends</CardTitle>
                                    <CardDescription>
                                        Historical view of security findings and improvements
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <SecurityTrends
                                        trendData={dashboardData?.trend_data || []}
                                        detailed
                                    />
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </main>
            </div>
        </div>
    )
}