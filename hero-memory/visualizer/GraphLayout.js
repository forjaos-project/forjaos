// Deterministic force layout computed in a QML WorkerScript, off the UI thread.

function hashId(value) {
    let hash = 2166136261
    for (let i = 0; i < value.length; i++) {
        hash ^= value.charCodeAt(i)
        hash = Math.imul(hash, 16777619)
    }
    return hash >>> 0
}

function computeLayout(nodes, links) {
    const count = nodes.length
    if (count === 0) return []
    const index = new Map()
    const x = new Float64Array(count)
    const y = new Float64Array(count)
    const velocityX = new Float64Array(count)
    const velocityY = new Float64Array(count)
    const forceX = new Float64Array(count)
    const forceY = new Float64Array(count)
    for (let i = 0; i < count; i++) {
        const id = String(nodes[i].id)
        index.set(id, i)
        const seed = hashId(id)
        const angle = (seed / 4294967296) * Math.PI * 2
        const radius = Math.sqrt((i + 0.5) / count) * 0.85
        x[i] = Math.cos(angle) * radius
        y[i] = Math.sin(angle) * radius
    }
    const edges = []
    for (let i = 0; i < links.length; i++) {
        const from = index.get(String(links[i].source))
        const to = index.get(String(links[i].target))
        if (from !== undefined && to !== undefined && from !== to)
            edges.push([from, to])
    }
    const cellSize = 0.12
    const separationSquared = 0.12 * 0.12
    const iterations = count > 5000 ? 8 : 20
    for (let step = 0; step < iterations; step++) {
        forceX.fill(0)
        forceY.fill(0)
        const grid = new Map()
        for (let i = 0; i < count; i++) {
            const key = Math.floor(x[i] / cellSize) + "," + Math.floor(y[i] / cellSize)
            let bucket = grid.get(key)
            if (bucket === undefined) {
                bucket = []
                grid.set(key, bucket)
            }
            bucket.push(i)
        }
        for (let i = 0; i < count; i++) {
            const cellX = Math.floor(x[i] / cellSize)
            const cellY = Math.floor(y[i] / cellSize)
            for (let gx = cellX - 1; gx <= cellX + 1; gx++) {
                for (let gy = cellY - 1; gy <= cellY + 1; gy++) {
                    const bucket = grid.get(gx + "," + gy)
                    if (bucket === undefined) continue
                    for (let b = 0; b < bucket.length; b++) {
                        const j = bucket[b]
                        if (j <= i) continue
                        let dx = x[i] - x[j]
                        let dy = y[i] - y[j]
                        let distanceSquared = dx * dx + dy * dy
                        if (distanceSquared >= separationSquared) continue
                        if (distanceSquared < 0.000001) {
                            const angle = ((i + j) * 2.399963) % (Math.PI * 2)
                            dx = Math.cos(angle) * 0.001
                            dy = Math.sin(angle) * 0.001
                            distanceSquared = dx * dx + dy * dy
                        }
                        const strength = Math.min(0.12, 0.0008 / (distanceSquared + 0.0004))
                        const fx = dx * strength
                        const fy = dy * strength
                        forceX[i] += fx
                        forceY[i] += fy
                        forceX[j] -= fx
                        forceY[j] -= fy
                    }
                }
            }
        }
        for (let edge = 0; edge < edges.length; edge++) {
            const from = edges[edge][0]
            const to = edges[edge][1]
            const dx = x[to] - x[from]
            const dy = y[to] - y[from]
            const distance = Math.max(0.0001, Math.hypot(dx, dy))
            const strength = Math.min(0.02, (distance - 0.09) * 0.014) / distance
            const fx = dx * strength
            const fy = dy * strength
            forceX[from] += fx
            forceY[from] += fy
            forceX[to] -= fx
            forceY[to] -= fy
        }
        for (let i = 0; i < count; i++) {
            velocityX[i] = (velocityX[i] + forceX[i] - x[i] * 0.001) * 0.75
            velocityY[i] = (velocityY[i] + forceY[i] - y[i] * 0.001) * 0.75
            x[i] = Math.max(-1, Math.min(1, x[i] + velocityX[i]))
            y[i] = Math.max(-1, Math.min(1, y[i] + velocityY[i]))
        }
    }
    const positions = new Array(count)
    for (let i = 0; i < count; i++) positions[i] = [x[i], y[i]]
    return positions
}

WorkerScript.onMessage = function (message) {
    const positions = computeLayout(message.nodes, message.links)
    WorkerScript.sendMessage({positions: positions, generation: message.generation})
}
