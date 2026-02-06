'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search, Filter, ChevronRight } from 'lucide-react'

interface Resource {
    id: string
    name: string
    type: string
    provider: string
    region: string
    cost: number
    securityScore: number
    optimizationScore: number
    status: 'running' | 'stopped' | 'error'
}

interface ResourceOverviewProps {
    resources: Resource[]
    isLoading: boolean
}

export function ResourceOverview({ resources, isLoading }: ResourceOverviewProps) {
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedType, setSelectedType] = useState<string>('all')

    const resourceTypes = ['all', 'ec2', 's3', 'rds', 'lambda', 'vpc']

    const filteredResources = resources.filter(resource => {
        const matchesSearch =
            resource.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            resource.type.toLowerCase().includes(searchTerm.toLowerCase())
        const matchesType = selectedType === 'all' || resource.type === selectedType
        return matchesSearch && matchesType
    })

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'running': return 'bg-green-100 text-green-800'
            case 'stopped': return 'bg-yellow-100 text-yellow-800'
            case 'error': return 'bg-red-100 text-red-800'
            default: return 'bg-gray-100 text-gray-800'
        }
    }

    const getResourceIcon = (type: string) => {
        switch (type) {
            case 'ec2': return '🖥️'
            case 's3': return '📦'
            case 'rds': return '🗄️'
            case 'lambda': return '⚡'
            case 'vpc': return '🌐'
            default: return '📄'
        }
    }

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Resources</CardTitle>
                    <CardDescription>Loading resources...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-12 bg-gray-100 animate-pulse rounded"></div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>Resources</CardTitle>
                        <CardDescription>
                            {filteredResources.length} resources across your cloud accounts
                        </CardDescription>
                    </div>
                    <Button variant="outline" size="sm">
                        View All
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {/* Filters */}
                <div className="flex flex-col sm:flex-row gap-4 mb-6">
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                        <Input
                            placeholder="Search resources..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-10"
                        />
                    </div>
                    <div className="flex gap-2 overflow-x-auto pb-2">
                        {resourceTypes.map(type => (
                            <button
                                key={type}
                                onClick={() => setSelectedType(type)}
                                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap ${selectedType === type
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                    }`}
                            >
                                {type === 'all' ? 'All Resources' : type.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Resource Table */}
                <div className="space-y-3">
                    {filteredResources.slice(0, 8).map((resource) => (
                        <div
                            key={resource.id}
                            className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                        >
                            <div className="flex items-center space-x-4">
                                <div className="text-2xl">{getResourceIcon(resource.type)}</div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <h4 className="font-medium">{resource.name}</h4>
                                        <Badge className={getStatusColor(resource.status)}>
                                            {resource.status}
                                        </Badge>
                                    </div>
                                    <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                                        <span className="uppercase">{resource.type}</span>
                                        <span>•</span>
                                        <span>{resource.region}</span>
                                        <span>•</span>
                                        <span>${resource.cost}/month</span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-6">
                                <div className="text-right">
                                    <div className="text-sm text-gray-500">Security</div>
                                    <div className={`font-semibold ${resource.securityScore > 80 ? 'text-green-600' :
                                            resource.securityScore > 60 ? 'text-yellow-600' : 'text-red-600'
                                        }`}>
                                        {resource.securityScore}%
                                    </div>
                                </div>

                                <div className="text-right">
                                    <div className="text-sm text-gray-500">Optimization</div>
                                    <div className={`font-semibold ${resource.optimizationScore > 80 ? 'text-green-600' :
                                            resource.optimizationScore > 60 ? 'text-yellow-600' : 'text-red-600'
                                        }`}>
                                        {resource.optimizationScore}%
                                    </div>
                                </div>

                                <Button variant="ghost" size="sm">
                                    <ChevronRight className="w-4 h-4" />
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>

                {filteredResources.length === 0 && (
                    <div className="text-center py-12">
                        <div className="text-gray-400 mb-4">No resources found</div>
                        <Button onClick={() => setSearchTerm('')}>Clear filters</Button>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}