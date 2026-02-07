'use client'

import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
    Network,
    Search,
    Target,
    Shield,
    AlertTriangle,
    Cpu,
    Database,
    Users,
    Globe
} from 'lucide-react'
import * as d3 from 'd3'

interface AttackGraph {
    nodes: Array<{
        id: string
        name: string
        type: string
        group: string
        risk_score: number
        criticality: string
        account_id: string
        region: string
        size: number
    }>
    links: Array<{
        source: string
        target: string
        type: string
        weight: number
    }>
}

interface AttackPath {
    nodes: Array<{
        id: string
        type: string
        name: string
        account_id: string
        region: string
        risk_score: number
        criticality: string
    }>
    edges: Array<{
        source: string
        target: string
        type: string
        weight: number
    }>
    total_risk: number
    path_length: number
    critical_nodes: string[]
}

export function AttackPathVisualizer() {
    const [graphData, setGraphData] = useState<AttackGraph | null>(null)
    const [attackPaths, setAttackPaths] = useState<AttackPath[]>([])
    const [selectedPath, setSelectedPath] = useState<number>(0)
    const [selectedNode, setSelectedNode] = useState<string | null>(null)
    const [blastRadius, setBlastRadius] = useState<any>(null)
    const [isLoading, setIsLoading] = useState(true)
    const svgRef = useRef<SVGSVGElement>(null)

    useEffect(() => {
        fetchAttackGraph()
        fetchAttackPaths()
    }, [])

    useEffect(() => {
        if (graphData && svgRef.current) {
            renderGraph()
        }
    }, [graphData, selectedPath])

    const fetchAttackGraph = async () => {
        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch('http://localhost:8000/api/v1/security/attack-graph', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setGraphData(data.graph)
            }
        } catch (error) {
            console.error('Failed to fetch attack graph:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const fetchAttackPaths = async () => {
        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch('http://localhost:8000/api/v1/security/attack-paths?max_length=4', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setAttackPaths(data.paths)
            }
        } catch (error) {
            console.error('Failed to fetch attack paths:', error)
        }
    }

    const calculateBlastRadius = async (nodeId: string) => {
        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch(`http://localhost:8000/api/v1/security/blast-radius/${encodeURIComponent(nodeId)}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setBlastRadius(data)
                setSelectedNode(nodeId)
            }
        } catch (error) {
            console.error('Failed to calculate blast radius:', error)
        }
    }

    const renderGraph = () => {
        if (!graphData || !svgRef.current) return

        const svg = d3.select(svgRef.current)
        svg.selectAll('*').remove()

        const width = svgRef.current.clientWidth
        const height = 600

        svg.attr('width', width).attr('height', height)

        // Create simulation
        const simulation = d3.forceSimulation(graphData.nodes as any)
            .force('link', d3.forceLink(graphData.links).id((d: any) => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(50))

        // Create links
        const link = svg.append('g')
            .selectAll('line')
            .data(graphData.links)
            .enter()
            .append('line')
            .attr('stroke', '#94a3b8')
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.6)

        // Create nodes
        const node = svg.append('g')
            .selectAll('g')
            .data(graphData.nodes)
            .enter()
            .append('g')
            .call(d3.drag() as any
                .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended)
            )
            .on('click', (event, d) => {
                calculateBlastRadius(d.id)
            })

        // Add circles to nodes
        node.append('circle')
            .attr('r', (d: any) => d.size)
            .attr('fill', (d: any) => getNodeColor(d.criticality))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)

        // Add labels
        node.append('text')
            .text((d: any) => d.name)
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .attr('font-size', '10px')
            .attr('fill', '#1f2937')

        // Add node type icons
        node.append('text')
            .attr('font-family', 'FontAwesome')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .attr('font-size', '12px')
            .attr('fill', '#fff')
            .text((d: any) => getNodeIcon(d.type))

        // Update positions
        simulation.on('tick', () => {
            link
                .attr('x1', (d: any) => d.source.x)
                .attr('y1', (d: any) => d.source.y)
                .attr('x2', (d: any) => d.target.x)
                .attr('y2', (d: any) => d.target.y)

            node.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
        })

        function dragstarted(event: any, d: any) {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
        }

        function dragged(event: any, d: any) {
            d.fx = event.x
            d.fy = event.y
        }

        function dragended(event: any, d: any) {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
        }
    }

    const getNodeColor = (criticality: string) => {
        switch (criticality) {
            case 'critical': return '#dc2626'
            case 'high': return '#ea580c'
            case 'medium': return '#d97706'
            case 'low': return '#059669'
            default: return '#6b7280'
        }
    }

    const getNodeIcon = (type: string) => {
        switch (type) {
            case 'iam_role': return '👤'
            case 'iam_user': return '👥'
            case 'ec2_instance': return '🖥️'
            case 's3_bucket': return '📦'
            case 'lambda_function': return '⚡'
            case 'rds_instance': return '🗄️'
            default: return '📄'
        }
    }

    const getEdgeTypeLabel = (type: string) => {
        switch (type) {
            case 'can_assume': return 'Can Assume'
            case 'can_access': return 'Can Access'
            case 'can_execute': return 'Can Execute'
            case 'network_reachable': return 'Network Reachable'
            default: return type
        }
    }

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Attack Path Analysis</CardTitle>
                    <CardDescription>Loading attack graph...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="h-96 bg-gray-100 animate-pulse rounded"></div>
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
                            <CardTitle className="flex items-center gap-2">
                                <Network className="w-5 h-5" />
                                Attack Path Analysis
                            </CardTitle>
                            <CardDescription>
                                Visualize potential attack paths and blast radius in your cloud environment
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Select
                                value={selectedPath.toString()}
                                onValueChange={(value) => setSelectedPath(parseInt(value))}
                            >
                                <SelectTrigger className="w-48">
                                    <SelectValue placeholder="Select attack path" />
                                </SelectTrigger>
                                <SelectContent>
                                    {attackPaths.map((path, index) => (
                                        <SelectItem key={index} value={index.toString()}>
                                            Path {index + 1} - Risk: {Math.round(path.total_risk)}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Button variant="outline" onClick={fetchAttackGraph}>
                                Refresh
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <div className="border border-gray-200 rounded-lg bg-gray-50 p-4">
                                <svg
                                    ref={svgRef}
                                    className="w-full h-96"
                                />
                            </div>

                            {selectedPath < attackPaths.length && (
                                <div className="mt-6">
                                    <h3 className="font-semibold mb-3">Selected Attack Path</h3>
                                    <div className="space-y-4">
                                        {attackPaths[selectedPath].nodes.map((node, index) => (
                                            <div key={node.id} className="flex items-center gap-4 p-3 bg-white border rounded-lg">
                                                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white ${node.criticality === 'critical' ? 'bg-red-600' :
                                                        node.criticality === 'high' ? 'bg-orange-600' :
                                                            node.criticality === 'medium' ? 'bg-yellow-600' : 'bg-green-600'
                                                    }`}>
                                                    {getNodeIcon(node.type)}
                                                </div>
                                                <div className="flex-1">
                                                    <div className="font-medium">{node.name}</div>
                                                    <div className="text-sm text-gray-500">
                                                        {node.type} • {node.account_id} • {node.region}
                                                    </div>
                                                </div>
                                                <Badge className={`
                          ${node.criticality === 'critical' ? 'bg-red-100 text-red-800' :
                                                        node.criticality === 'high' ? 'bg-orange-100 text-orange-800' :
                                                            node.criticality === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                                                'bg-green-100 text-green-800'}
                        `}>
                                                    {node.criticality}
                                                </Badge>
                                                <div className="text-right">
                                                    <div className="text-sm text-gray-500">Risk</div>
                                                    <div className="font-bold">{Math.round(node.risk_score)}</div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <div className="font-medium">Path Analysis</div>
                                                <div className="text-sm text-gray-600">
                                                    {attackPaths[selectedPath].path_length} steps •
                                                    {attackPaths[selectedPath].critical_nodes.length} critical nodes
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm text-gray-600">Total Path Risk</div>
                                                <div className="text-2xl font-bold text-red-600">
                                                    {Math.round(attackPaths[selectedPath].total_risk)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="space-y-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Blast Radius</CardTitle>
                                    <CardDescription>
                                        Impact analysis for selected node
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {blastRadius ? (
                                        <div className="space-y-4">
                                            <div className="p-3 bg-gray-50 rounded-lg">
                                                <div className="font-medium">{blastRadius.node_name}</div>
                                                <div className="text-sm text-gray-500">{blastRadius.node_type}</div>
                                            </div>

                                            <div className="grid grid-cols-2 gap-3">
                                                <div className="bg-white p-3 rounded-lg border text-center">
                                                    <div className="text-2xl font-bold">{blastRadius.reachable_nodes}</div>
                                                    <div className="text-sm text-gray-500">Reachable Nodes</div>
                                                </div>
                                                <div className="bg-white p-3 rounded-lg border text-center">
                                                    <div className="text-2xl font-bold text-red-600">{blastRadius.critical_reachable}</div>
                                                    <div className="text-sm text-gray-500">Critical Nodes</div>
                                                </div>
                                            </div>

                                            <div>
                                                <div className="font-medium mb-2">High Value Targets</div>
                                                <div className="space-y-2">
                                                    {blastRadius.high_value_targets.slice(0, 3).map((target: any) => (
                                                        <div key={target.id} className="text-sm p-2 bg-gray-50 rounded">
                                                            <div className="font-medium">{target.name}</div>
                                                            <div className="text-gray-500">Risk: {Math.round(target.risk_score)}</div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            <div>
                                                <div className="font-medium mb-2">Recommendations</div>
                                                <ul className="text-sm space-y-1">
                                                    {blastRadius.recommendations?.map((rec: string, index: number) => (
                                                        <li key={index} className="flex items-start gap-2">
                                                            <Shield className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                                                            <span>{rec}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-center py-8 text-gray-500">
                                            <Target className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                                            <p>Click on a node to calculate blast radius</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle>Legend</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 bg-red-600 rounded-full"></div>
                                        <span className="text-sm">Critical Node</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 bg-orange-600 rounded-full"></div>
                                        <span className="text-sm">High Risk Node</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                                        <span className="text-sm">Normal Node</span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-4">
                                        <div className="w-6 h-px bg-gray-400"></div>
                                        <span className="text-sm">Relationship</span>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}