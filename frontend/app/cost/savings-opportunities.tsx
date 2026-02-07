'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
    ArrowRight,
    Zap,
    Shield,
    Database,
    Cpu,
    TrendingUp,
    AlertTriangle,
    CheckCircle
} from 'lucide-react'

interface Recommendation {
    id: string
    title: string
    description: string
    estimated_savings: number
    implementation_effort: string
    risk: string
    action_type: string
    resource_type: string
    resource_id: string
}

interface SavingsOpportunitiesProps {
    recommendations: Recommendation[]
}

export function SavingsOpportunities({ recommendations }: SavingsOpportunitiesProps) {
    const [selectedCategory, setSelectedCategory] = useState<string>('all')
    const [sortBy, setSortBy] = useState<'savings' | 'effort' | 'risk'>('savings')

    const categories = [
        { id: 'all', label: 'All', count: recommendations.length },
        { id: 'compute', label: 'Compute', count: recommendations.filter(r => r.resource_type.includes('EC2')).length },
        { id: 'storage', label: 'Storage', count: recommendations.filter(r => r.resource_type.includes('S3') || r.resource_type.includes('EBS')).length },
        { id: 'database', label: 'Database', count: recommendations.filter(r => r.resource_type.includes('RDS')).length },
        { id: 'other', label: 'Other', count: recommendations.filter(r => !r.resource_type.includes('EC2') && !r.resource_type.includes('S3') && !r.resource_type.includes('RDS')).length },
    ]

    const filteredRecommendations = recommendations.filter(rec => {
        if (selectedCategory === 'all') return true
        if (selectedCategory === 'compute') return rec.resource_type.includes('EC2')
        if (selectedCategory === 'storage') return rec.resource_type.includes('S3') || rec.resource_type.includes('EBS')
        if (selectedCategory === 'database') return rec.resource_type.includes('RDS')
        return true
    })

    const sortedRecommendations = [...filteredRecommendations].sort((a, b) => {
        if (sortBy === 'savings') return b.estimated_savings - a.estimated_savings
        if (sortBy === 'effort') {
            const effortOrder = { low: 0, medium: 1, high: 2 }
            return effortOrder[a.implementation_effort as keyof typeof effortOrder] - effortOrder[b.implementation_effort as keyof typeof effortOrder]
        }
        if (sortBy === 'risk') {
            const riskOrder = { low: 0, medium: 1, high: 2 }
            return riskOrder[a.risk as keyof typeof riskOrder] - riskOrder[b.risk as keyof typeof riskOrder]
        }
        return 0
    })

    const totalSavings = recommendations.reduce((sum, rec) => sum + rec.estimated_savings, 0)
    const highImpactSavings = recommendations
        .filter(rec => rec.estimated_savings > 100)
        .reduce((sum, rec) => sum + rec.estimated_savings, 0)

    const getResourceIcon = (resourceType: string) => {
        if (resourceType.includes('EC2')) return <Cpu className="w-5 h-5 text-blue-600" />
        if (resourceType.includes('S3')) return <Database className="w-5 h-5 text-green-600" />
        if (resourceType.includes('RDS')) return <Database className="w-5 h-5 text-purple-600" />
        if (resourceType.includes('EBS')) return <Database className="w-5 h-5 text-yellow-600" />
        return <Zap className="w-5 h-5 text-gray-600" />
    }

    const getEffortColor = (effort: string) => {
        switch (effort) {
            case 'low': return 'bg-green-100 text-green-800'
            case 'medium': return 'bg-yellow-100 text-yellow-800'
            case 'high': return 'bg-red-100 text-red-800'
            default: return 'bg-gray-100 text-gray-800'
        }
    }

    const getRiskColor = (risk: string) => {
        switch (risk) {
            case 'low': return 'bg-green-100 text-green-800'
            case 'medium': return 'bg-yellow-100 text-yellow-800'
            case 'high': return 'bg-red-100 text-red-800'
            default: return 'bg-gray-100 text-gray-800'
        }
    }

    const getActionTypeIcon = (actionType: string) => {
        switch (actionType) {
            case 'shutdown': return <Zap className="w-4 h-4" />
            case 'resize': return <TrendingUp className="w-4 h-4" />
            case 'delete': return <AlertTriangle className="w-4 h-4" />
            case 'purchase_reserved': return <CheckCircle className="w-4 h-4" />
            default: return <ArrowRight className="w-4 h-4" />
        }
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-green-600" />
                            Savings Opportunities
                        </CardTitle>
                        <CardDescription>
                            AI-powered recommendations to optimize your cloud spend
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="text-right">
                            <div className="text-2xl font-bold text-green-600">
                                ${totalSavings.toLocaleString()}
                            </div>
                            <div className="text-sm text-gray-500">Total potential savings</div>
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {/* Summary */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-4 rounded-lg border border-green-200">
                        <div className="text-sm text-green-700 font-medium mb-2">High Impact</div>
                        <div className="text-2xl font-bold text-green-800">
                            ${highImpactSavings.toLocaleString()}
                        </div>
                        <div className="text-sm text-green-600 mt-1">
                            {recommendations.filter(r => r.estimated_savings > 100).length} recommendations
                        </div>
                    </div>

                    <div className="bg-gradient-to-r from-blue-50 to-cyan-50 p-4 rounded-lg border border-blue-200">
                        <div className="text-sm text-blue-700 font-medium mb-2">Easy Wins</div>
                        <div className="text-2xl font-bold text-blue-800">
                            {recommendations.filter(r => r.implementation_effort === 'low').length}
                        </div>
                        <div className="text-sm text-blue-600 mt-1">
                            Low effort recommendations
                        </div>
                    </div>

                    <div className="bg-gradient-to-r from-purple-50 to-pink-50 p-4 rounded-lg border border-purple-200">
                        <div className="text-sm text-purple-700 font-medium mb-2">Quick Actions</div>
                        <div className="text-2xl font-bold text-purple-800">
                            {recommendations.filter(r => r.implementation_effort === 'low' && r.risk === 'low').length}
                        </div>
                        <div className="text-sm text-purple-600 mt-1">
                            Low risk, easy to implement
                        </div>
                    </div>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-3 mb-6">
                    <div className="text-sm font-medium text-gray-700">Categories:</div>
                    {categories.map(category => (
                        <button
                            key={category.id}
                            onClick={() => setSelectedCategory(category.id)}
                            className={`px-3 py-1 rounded-full text-sm font-medium transition ${selectedCategory === category.id
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            {category.label} ({category.count})
                        </button>
                    ))}

                    <div className="ml-auto flex items-center gap-2">
                        <span className="text-sm text-gray-600">Sort by:</span>
                        <select
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value as any)}
                            className="border rounded-md px-3 py-1 text-sm"
                        >
                            <option value="savings">Highest Savings</option>
                            <option value="effort">Lowest Effort</option>
                            <option value="risk">Lowest Risk</option>
                        </select>
                    </div>
                </div>

                {/* Recommendations List */}
                <div className="space-y-4">
                    {sortedRecommendations.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                            <TrendingUp className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                            <p>No savings opportunities found for this category</p>
                        </div>
                    ) : (
                        sortedRecommendations.map(recommendation => (
                            <div
                                key={recommendation.id}
                                className="flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                            >
                                <div className="flex-shrink-0">
                                    {getResourceIcon(recommendation.resource_type)}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-2">
                                        <h4 className="font-semibold text-gray-900 truncate">
                                            {recommendation.title}
                                        </h4>
                                        <Badge className={getEffortColor(recommendation.implementation_effort)}>
                                            {recommendation.implementation_effort} effort
                                        </Badge>
                                        <Badge className={getRiskColor(recommendation.risk)}>
                                            {recommendation.risk} risk
                                        </Badge>
                                    </div>

                                    <p className="text-sm text-gray-600 mb-3">
                                        {recommendation.description}
                                    </p>

                                    <div className="flex flex-wrap items-center gap-4">
                                        <div className="flex items-center gap-2">
                                            <Shield className="w-4 h-4 text-gray-400" />
                                            <span className="text-sm text-gray-500">{recommendation.resource_type}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {getActionTypeIcon(recommendation.action_type)}
                                            <span className="text-sm text-gray-500 capitalize">
                                                {recommendation.action_type.replace('_', ' ')}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex-shrink-0 flex flex-col items-end">
                                    <div className="text-xl font-bold text-green-600 mb-2">
                                        ${recommendation.estimated_savings.toLocaleString()}
                                    </div>
                                    <div className="text-sm text-gray-500 mb-3">Monthly savings</div>
                                    <Button size="sm" className="gap-2">
                                        Implement
                                        <ArrowRight className="w-4 h-4" />
                                    </Button>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* Implementation Progress */}
                {recommendations.length > 0 && (
                    <div className="mt-8 pt-6 border-t border-gray-200">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-sm font-medium text-gray-700">
                                Implementation Progress
                            </div>
                            <div className="text-sm text-gray-500">
                                0 of {recommendations.length} implemented
                            </div>
                        </div>
                        <Progress value={0} className="h-2" />
                        <div className="text-xs text-gray-500 mt-2">
                            Start implementing recommendations to unlock savings
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}