'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardHeader } from '@/components/dashboard/header'
import { DashboardSidebar } from '@/components/dashboard/sidebar'
import { CostOverviewChart } from '@/components/cost/overview-chart'
import { CostBreakdown } from '@/components/cost/breakdown'
import { SavingsOpportunities } from '@/components/cost/savings-opportunities'
import { BudgetHealth } from '@/components/cost/budget-health'
import { CostForecast } from '@/components/cost/forecast'
import { AnomalyDetection } from '@/components/cost/anomaly-detection'
import { CostTrends } from '@/components/cost/trends'
import { useAuth } from '@/lib/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Download, Filter, TrendingUp, AlertCircle } from 'lucide-react'

interface CostData {
    period: {
        start: string
        end: string
    }
    total_cost: number
    breakdown: {
        by_service: Record<string, number>
        by_region: Record<string, number>
        by_account: Record<string, number>
    }
    trend_percentage: number
    forecast_30d: number
    recommendations: any[]
    anomalies: any[]
}

export default function CostPage() {
    const router = useRouter()
    const { user, isLoading: authLoading } = useAuth()
    const [costData, setCostData] = useState<CostData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [timeRange, setTimeRange] = useState('30d')
    const [activeTab, setActiveTab] = useState('overview')

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login')
        }
    }, [user, authLoading, router])

    useEffect(() => {
        const fetchCostData = async () => {
            setIsLoading(true)
            try {
                const token = localStorage.getItem('access_token')
                const response = await fetch(`http://localhost:8000/api/v1/cost/analysis?time_range=${timeRange}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })

                if (response.ok) {
                    const data = await response.json()
                    setCostData(data)
                }
            } catch (error) {
                console.error('Failed to fetch cost data:', error)
            } finally {
                setIsLoading(false)
            }
        }

        if (user) {
            fetchCostData()
        }
    }, [user, timeRange])

    if (authLoading || isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading cost intelligence...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <DashboardHeader
                user={user}
                onTimeRangeChange={setTimeRange}
            />

            <div className="flex">
                <DashboardSidebar active="cost" />

                <main className="flex-1 p-6 lg:p-8">
                    {/* Header */}
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
                        <div>
                            <h1 className="text-3xl font-bold">Cost Intelligence</h1>
                            <p className="text-gray-600 mt-2">
                                AI-powered cost analysis, forecasting, and optimization
                            </p>
                        </div>

                        <div className="flex items-center gap-3">
                            <Button variant="outline" className="gap-2">
                                <Download className="w-4 h-4" />
                                Export Report
                            </Button>
                            <Button variant="outline" className="gap-2">
                                <Filter className="w-4 h-4" />
                                Filters
                            </Button>
                            <Button className="gap-2 bg-green-600 hover:bg-green-700">
                                <TrendingUp className="w-4 h-4" />
                                Savings Dashboard
                            </Button>
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Total Cost</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold">
                                    ${costData?.total_cost?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                                </div>
                                <div className={`flex items-center mt-2 text-sm ${costData?.trend_percentage >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                                    <TrendingUp className={`w-4 h-4 mr-1 ${costData?.trend_percentage < 0 ? 'rotate-180' : ''}`} />
                                    {Math.abs(costData?.trend_percentage || 0).toFixed(1)}% from last period
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">30-Day Forecast</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold">
                                    ${costData?.forecast_30d?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                                </div>
                                <div className="text-sm text-gray-600 mt-2">
                                    Predicted next 30 days
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Active Anomalies</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center">
                                    <div className="text-3xl font-bold mr-3">
                                        {costData?.anomalies?.length || 0}
                                    </div>
                                    <div className="text-sm text-gray-600">
                                        Cost anomalies detected
                                    </div>
                                </div>
                                {costData?.anomalies && costData.anomalies.length > 0 && (
                                    <div className="flex items-center mt-2 text-sm text-red-600">
                                        <AlertCircle className="w-4 h-4 mr-1" />
                                        Review recommended
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-gray-500">Savings Opportunity</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold text-green-600">
                                    ${
                                        costData?.recommendations
                                            ?.reduce((sum, rec) => sum + (rec.estimated_savings || 0), 0)
                                            .toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'
                                    }
                                </div>
                                <div className="text-sm text-gray-600 mt-2">
                                    {costData?.recommendations?.length || 0} recommendations
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Main Content Tabs */}
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                        <TabsList className="grid grid-cols-2 lg:grid-cols-6">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="breakdown">Breakdown</TabsTrigger>
                            <TabsTrigger value="forecast">Forecast</TabsTrigger>
                            <TabsTrigger value="budgets">Budgets</TabsTrigger>
                            <TabsTrigger value="savings">Savings</TabsTrigger>
                            <TabsTrigger value="trends">Trends</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2">
                                    <CostOverviewChart timeRange={timeRange} />
                                </div>
                                <div className="space-y-6">
                                    <BudgetHealth />
                                    <AnomalyDetection anomalies={costData?.anomalies || []} />
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="breakdown">
                            <CostBreakdown breakdown={costData?.breakdown} />
                        </TabsContent>

                        <TabsContent value="forecast">
                            <CostForecast />
                        </TabsContent>

                        <TabsContent value="budgets">
                            <div className="space-y-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Budget Management</CardTitle>
                                        <CardDescription>
                                            Create and monitor budgets across your cloud accounts
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <BudgetHealth detailed />
                                    </CardContent>
                                </Card>
                            </div>
                        </TabsContent>

                        <TabsContent value="savings">
                            <SavingsOpportunities recommendations={costData?.recommendations || []} />
                        </TabsContent>

                        <TabsContent value="trends">
                            <CostTrends />
                        </TabsContent>
                    </Tabs>
                </main>
            </div>
        </div>
    )
}