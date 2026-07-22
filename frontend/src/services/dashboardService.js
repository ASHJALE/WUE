import { fetchCurrentUser } from './authSession.js'
import { getEstimates } from './estimateService.js'
import { getQuotations } from './quotationService.js'

const PAGE_SIZE = 200

async function fetchAll(fetchPage, userId) {
  const records = []
  let skip = 0
  while (true) {
    const page = await fetchPage({ user_id: userId, skip, limit: PAGE_SIZE })
    records.push(...page)
    if (page.length < PAGE_SIZE) return records
    skip += PAGE_SIZE
  }
}

function newestFirst(records) {
  return [...records].sort(
    (left, right) => new Date(right.created_at) - new Date(left.created_at),
  )
}

function quotationStatusCounts(quotations) {
  return quotations.reduce(
    (counts, quotation) => ({
      ...counts,
      [quotation.status]: (counts[quotation.status] || 0) + 1,
    }),
    { draft: 0, approved: 0, completed: 0, rejected: 0 },
  )
}

function estimateTimeline(estimates) {
  const counts = estimates.reduce((result, estimate) => {
    const date = estimate.created_at.slice(0, 10)
    return { ...result, [date]: (result[date] || 0) + 1 }
  }, {})
  return Object.entries(counts)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([date, count]) => ({ date, count }))
}

export async function getDashboardSummary() {
  const user = await fetchCurrentUser()
  const [estimates, quotations] = await Promise.all([
    fetchAll(getEstimates, user.id),
    fetchAll(getQuotations, user.id),
  ])
  const statusCounts = quotationStatusCounts(quotations)
  const materialValueCents = quotations.reduce(
    (total, quotation) => total + Math.round(Number(quotation.material_total) * 100),
    0,
  )
  return {
    user,
    estimates,
    quotations,
    summary: {
      totalEstimates: estimates.length,
      ...statusCounts,
      materialValue: materialValueCents / 100,
    },
    recentEstimates: newestFirst(estimates).slice(0, 5),
    recentQuotations: newestFirst(quotations).slice(0, 5),
    quotationStatusCounts: statusCounts,
    estimateTimeline: estimateTimeline(estimates),
  }
}
