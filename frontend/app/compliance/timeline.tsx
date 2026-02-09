'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    AreaChart
} from 'recharts'
import {
    TrendingUp,
    TrendingDown,
    Calendar,
    Download,
    Filter
} from 'lucide-react'

interface TimelineData {
    date: string
    score: number
    status: string
    assessments: number
    failed_controls: number
}

interface ComplianceTimelineProps {
    timeline: TimelineData[]
    detailed?: boolean
}

export function ComplianceTimeline({ timeline, detailed = false }: ComplianceTimelineProps) {
    const [timeRange, setTimeRange] = useState('30d')
    const [chartData, setChartData] = useState<TimelineData[]>([])
    const [trendDirection, setTrendDirection] = useState<'up' | 'down' | 'stable'>('up')

    useEffect(() => {
        if (timeline.length > 0) {
            const processedData = processTimelineData(timeline, timeRange)
            setChartData(processedData)

            // Calculate trend
            if (processedData.length >= 2) {
                const firstScore = processedData[0].score
                const lastScore = processedData[processedData.length - 1].score
                setTrendDirection(
                    lastScore > firstScore ? 'up' :
                        lastScore < firstScore ? 'down' : 'stable'
                )
            }
        }
    }, [timeline, timeRange])

    const processTimelineData = (data: TimelineData[], range: string): TimelineData[] => {
        let limit = 30
        if (range === '7d') limit = 7
        if (range === '90d') limit = 90

        return data.slice(0, limit).reverse()
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        if (timeRange === '7d') {
            return date.toLocaleDateString('en-US', { weekday: 'short' })
        }
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
                    <p className="font-semibold">{label}</p>
                    <div className="space-y-1 mt-2">
                        <div className="flex items-center justify-between">
                            <span className="text-gray-600">Score:</span>
                            <span className="font-medium">{payload[0].value}%</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-gray-600">Status:</span>
                            <Badge className={
                                payload[0].value >= 80 ? 'bg-green-100 text-green-800' :
                                    payload[0].value >= 60 ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-red-100 text-red-800'
                            }>
                                {payload[0].value >= 80 ? 'Compliant' : 'Non-compliant'}
                            </Badge>
                        </div>
                    </div>
                </div>
            )
        }
        return null
    }

    const calculateStats = () => {
        if (chartData.length === 0) return { avg: 0, min: 0, max: 0, trend: 0 }

        const scores = chartData.map(d => d.score)
        const avg = scores.reduce((a, b) => a + b, 0) / scores.length
        const min = Math.min(...scores)
        const max = Math.max(...scores)

        const trend = scores.length >= 2
            ? ((scores[scores.length - 1] - scores[0]) / scores[0]) * 100
            : 0

        return { avg: Math.round(avg), min: Math.round(min), max: Math.round(max), trend }
    }

    const stats = calculateStats()

    return (
        <Card>
            <CardHeader>
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div>
                        <CardTitle>Compliance Timeline</CardTitle>
                        <CardDescription>
                            Track compliance score changes over time
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="flex bg-gray-100 rounded-lg p-1">
                            {['7d', '30d', '90d'].map((range) => (
                                <button
                                    key={range}
                                    onClick={() => setTimeRange(range)}
                                    className={`px-3 py-1 rounded text-sm font-medium ${timeRange === range
                                            ? 'bg-white shadow'
                                            : 'text-gray-600 hover:text-gray-900'
                                        }`}
                                >
                                    {range}
                                </button>
                            ))}
                        </div>
                        <Button variant="outline" size="sm">
                            <Download className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {chartData.length === 0 ? (
                    <div className="h-64 flex items-center justify-center text-gray-500">
                        No timeline data available
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* Stats Summary */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-gray-50 p-4 rounded-lg">
                                <div className="text-sm text-gray-500">Average</div>
                                <div className="text-2xl font-bold">{stats.avg}%</div>
                            </div>
                            <div className="bg-gray-50 p-4 rounded-lg">
                                <div className="text-sm text-gray-500">Trend</div>
                                <div className="flex items-center gap-2">
                                    <div className={`text-2xl font-bold ${trendDirection === 'up' ? 'text-green-600' :
                                            trendDirection === 'down' ? 'text-red-600' : 'text-gray-600'
                                        }`}>
                                        {trendDirection === 'up' ? '↗' :
                                            trendDirection === 'down' ? '↘' : '→'}
                                    </div>
                                    <div className={`font-medium ${stats.trend > 0 ? 'text-green-600' :
                                            stats.trend < 0 ? 'text-red-600' : 'text-gray-600'
                                        }`}>
                                        {Math.abs(stats.trend).toFixed(1)}%
                                    </div>
                                </div>
                            </div>
                            <div className="bg-gray-50 p-4 rounded-lg">
                                <div className="text-sm text-gray-500">High</div>
                                <div className="text-2xl font-bold text-green-600">{stats.max}%</div>
                            </div>
                            <div className="bg-gray-50 p-4 rounded-lg">
                                <div className="text-sm text-gray-500">Low</div>
                                <div className="text-2xl font-bold text-red-600">{stats.min}%</div>
                            </div>
                        </div>

                        {/* Chart */}
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis
                                        dataKey="date"
                                        tickFormatter={formatDate}
                                        tick={{ fontSize: 12 }}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 12 }}
                                        domain={[0, 100]}
                                        tickFormatter={(value) => `${value}%`}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Area
                                        type="monotone"
                                        dataKey="score"
                                        stroke="#3b82f6"
                                        fill="#3b82f6"
                                        fillOpacity={0.1}
                                        strokeWidth={2}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Detailed View */}
                        {detailed && (
                            <div className="mt-6">
                                <h4 className="font-semibold mb-4">Recent Assessments</h4>
                                <div className="space-y-3">
                                    {chartData.slice(-5).reverse().map((entry) => (
                                        <div key={entry.date} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                            <div>
                                                <div className="font-medium">{formatDate(entry.date)}</div>
                                                <div className="text-sm text-gray-500">
                                                    {entry.failed_controls} failed controls
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <Badge className={
                                                    entry.status === 'compliant' ? 'bg-green-100 text-green-800' :
                                                        'bg-red-100 text-red-800'
                                                }>
                                                    {entry.status}
                                                </Badge>
                                                <div className={`text-xl font-bold ${entry.score >= 80 ? 'text-green-600' :
                                                        entry.score >= 60 ? 'text-yellow-600' : 'text-red-600'
                                                    }`}>
                                                    {Math.round(entry.score)}%
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}