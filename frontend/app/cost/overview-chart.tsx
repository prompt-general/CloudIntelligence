'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { TrendingUp, TrendingDown, Calendar, DollarSign } from 'lucide-react'

interface CostOverviewChartProps {
    timeRange: string
}

export function CostOverviewChart({ timeRange }: CostOverviewChartProps) {
    const [chartData, setChartData] = useState<any[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [chartType, setChartType] = useState<'line' | 'area'>('area')

    useEffect(() => {
        const fetchChartData = async () => {
            setIsLoading(true)
            try {
                const token = localStorage.getItem('access_token')
                const response = await fetch(`http://localhost:8000/api/v1/cost/trends?days=${parseInt(timeRange)}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })

                if (response.ok) {
                    const data = await response.json()
                    setChartData(data.trend_data || [])
                }
            } catch (error) {
                console.error('Failed to fetch chart data:', error)
                // Generate mock data if API fails
                generateMockData()
            } finally {
                setIsLoading(false)
            }
        }

        fetchChartData()
    }, [timeRange])

    const generateMockData = () => {
        const data = []
        const days = parseInt(timeRange) || 30
        let cumulative = 0

        for (let i = 0; i < days; i++) {
            const dailyCost = 1000 + Math.random() * 500
            cumulative += dailyCost

            data.push({
                date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                cost: Math.round(dailyCost),
                cumulative: Math.round(cumulative)
            })
        }

        setChartData(data)
    }

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value)
    }

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
                    <p className="font-semibold text-gray-800">{label}</p>
                    <p className="text-sm text-gray-600">
                        Daily: {formatCurrency(payload[0].value)}
                    </p>
                    <p className="text-sm text-gray-600">
                        Cumulative: {formatCurrency(payload[1].value)}
                    </p>
                </div>
            )
        }
        return null
    }

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Cost Overview</CardTitle>
                    <CardDescription>Loading chart data...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="h-80 bg-gray-100 animate-pulse rounded"></div>
                </CardContent>
            </Card>
        )
    }

    const totalCost = chartData.reduce((sum, day) => sum + day.cost, 0)
    const avgDailyCost = totalCost / chartData.length
    const firstDayCost = chartData[0]?.cost || 0
    const lastDayCost = chartData[chartData.length - 1]?.cost || 0
    const trendPercentage = ((lastDayCost - firstDayCost) / firstDayCost) * 100

    return (
        <Card>
            <CardHeader>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <CardTitle>Cost Overview</CardTitle>
                        <CardDescription>
                            {timeRange} cost trend and analysis
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant={chartType === 'line' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setChartType('line')}
                        >
                            Line
                        </Button>
                        <Button
                            variant={chartType === 'area' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setChartType('area')}
                        >
                            Area
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-6">
                    {/* Summary Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-gray-50 p-4 rounded-lg">
                            <div className="flex items-center gap-2 text-gray-600 mb-2">
                                <DollarSign className="w-4 h-4" />
                                <span className="text-sm">Total Cost</span>
                            </div>
                            <div className="text-2xl font-bold">
                                {formatCurrency(totalCost)}
                            </div>
                        </div>

                        <div className="bg-gray-50 p-4 rounded-lg">
                            <div className="flex items-center gap-2 text-gray-600 mb-2">
                                <Calendar className="w-4 h-4" />
                                <span className="text-sm">Avg Daily</span>
                            </div>
                            <div className="text-2xl font-bold">
                                {formatCurrency(avgDailyCost)}
                            </div>
                        </div>

                        <div className="bg-gray-50 p-4 rounded-lg">
                            <div className="flex items-center gap-2 text-gray-600 mb-2">
                                {trendPercentage >= 0 ? (
                                    <TrendingUp className="w-4 h-4 text-red-600" />
                                ) : (
                                    <TrendingDown className="w-4 h-4 text-green-600" />
                                )}
                                <span className="text-sm">Trend</span>
                            </div>
                            <div className={`text-2xl font-bold ${trendPercentage >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                                {Math.abs(trendPercentage).toFixed(1)}%
                            </div>
                        </div>

                        <div className="bg-gray-50 p-4 rounded-lg">
                            <div className="flex items-center gap-2 text-gray-600 mb-2">
                                <span className="text-sm">Days</span>
                            </div>
                            <div className="text-2xl font-bold">
                                {chartData.length}
                            </div>
                        </div>
                    </div>

                    {/* Chart */}
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            {chartType === 'area' ? (
                                <AreaChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fontSize: 12 }}
                                        tickFormatter={(value) => {
                                            const date = new Date(value)
                                            return `${date.getMonth() + 1}/${date.getDate()}`
                                        }}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 12 }}
                                        tickFormatter={(value) => `$${value / 1000}k`}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Area
                                        type="monotone"
                                        dataKey="cost"
                                        stroke="#3b82f6"
                                        fill="#3b82f6"
                                        fillOpacity={0.1}
                                        strokeWidth={2}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="cumulative"
                                        stroke="#10b981"
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                </AreaChart>
                            ) : (
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fontSize: 12 }}
                                        tickFormatter={(value) => {
                                            const date = new Date(value)
                                            return `${date.getMonth() + 1}/${date.getDate()}`
                                        }}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 12 }}
                                        tickFormatter={(value) => `$${value / 1000}k`}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Line
                                        type="monotone"
                                        dataKey="cost"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        dot={{ r: 2 }}
                                        activeDot={{ r: 4 }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="cumulative"
                                        stroke="#10b981"
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                </LineChart>
                            )}
                        </ResponsiveContainer>
                    </div>

                    {/* Legend */}
                    <div className="flex items-center justify-center gap-6 text-sm">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                            <span className="text-gray-600">Daily Cost</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                            <span className="text-gray-600">Cumulative Cost</span>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}