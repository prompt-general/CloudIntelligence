'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardHeader } from '@/components/dashboard/header'
import { DashboardSidebar } from '@/components/dashboard/sidebar'
import { ResourceOverview } from '@/components/dashboard/resource-overview'
import { CostOverview } from '@/components/dashboard/cost-overview'
import { SecurityOverview } from '@/components/dashboard/security-overview'
import { RecentActivity } from '@/components/dashboard/recent-activity'
import { QuickActions } from '@/components/dashboard/quick-actions'
import { CloudAccountCard } from '@/components/dashboard/cloud-account-card'
import { useAuth } from '@/lib/auth'

interface DashboardData {
    organization: any
    cloudAccounts: any[]
    resources: any[]
    metrics: {
        totalResources: number
        totalCost: number
        securityScore: number
        optimizationScore: number
    }
}

export default function DashboardPage() {
    const router = useRouter()
    const { user, isLoading: authLoading } = useAuth()
    const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [selectedOrganization, setSelectedOrganization] = useState<string>('')
    const [timeRange, setTimeRange] = useState('7d')

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login')
        }
    }, [user, authLoading, router])

    useEffect(() => {
        const fetchDashboardData = async () => {
            setIsLoading(true)
            try {
                const token = localStorage.getItem('access_token')
                const response = await fetch('http://localhost:8000/api/v1/dashboard', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })

                if (response.ok) {
                    const data = await response.json()
                    setDashboardData(data)
                    if (data.organization) {
                        setSelectedOrganization(data.organization.id)
                    }
                }
            } catch (error) {
                console.error('Failed to fetch dashboard data:', error)
            } finally {
                setIsLoading(false)
            }
        }

        if (user) {
            fetchDashboardData()
        }
    }, [user])

    if (authLoading || isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading dashboard...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <DashboardHeader
                user={user}
                organization={dashboardData?.organization}
                onOrganizationChange={setSelectedOrganization}
            />

            <div className="flex">
                <DashboardSidebar />

                <main className="flex-1 p-6 lg:p-8">
                    {/* Quick Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">Total Resources</p>
                                    <p className="text-3xl font-bold mt-2">
                                        {dashboardData?.metrics.totalResources.toLocaleString() || '0'}
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                    </svg>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">Monthly Cost</p>
                                    <p className="text-3xl font-bold mt-2">
                                        ${dashboardData?.metrics.totalCost.toLocaleString() || '0'}
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center">
                                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">Security Score</p>
                                    <p className="text-3xl font-bold mt-2">
                                        {dashboardData?.metrics.securityScore || '0'}%
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-red-100 flex items-center justify-center">
                                    <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                    </svg>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500">Optimization</p>
                                    <p className="text-3xl font-bold mt-2">
                                        {dashboardData?.metrics.optimizationScore || '0'}%
                                    </p>
                                </div>
                                <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center">
                                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Main Content Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                        <div className="lg:col-span-2">
                            <ResourceOverview
                                resources={dashboardData?.resources || []}
                                isLoading={isLoading}
                            />
                        </div>
                        <div className="space-y-6">
                            <QuickActions />
                            <RecentActivity />
                        </div>
                    </div>

                    {/* Cloud Accounts */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold">Cloud Accounts</h2>
                            <button
                                onClick={() => router.push('/dashboard/accounts/connect')}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                            >
                                + Connect Account
                            </button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {dashboardData?.cloudAccounts.map((account) => (
                                <CloudAccountCard key={account.id} account={account} />
                            ))}
                        </div>
                    </div>

                    {/* Bottom Row */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <CostOverview timeRange={timeRange} />
                        <SecurityOverview />
                    </div>
                </main>
            </div>
        </div>
    )
}