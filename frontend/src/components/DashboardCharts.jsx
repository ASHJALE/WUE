import { useEffect, useRef } from 'react'
import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js'

Chart.register(
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  Legend,
  LinearScale,
  Tooltip,
)

function ChartCanvas({ config, label }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!canvasRef.current || !config) return undefined
    const chart = new Chart(canvasRef.current, config)
    return () => chart.destroy()
  }, [config])

  return <canvas aria-label={label} ref={canvasRef} role="img" />
}

export default function DashboardCharts({ quotations, statusCounts, timeline }) {
  const hasQuotations = quotations.length > 0
  const hasEstimates = timeline.length > 0
  const doughnutConfig = hasQuotations ? {
    type: 'doughnut',
    data: {
      labels: ['Draft', 'Approved', 'Completed', 'Rejected'],
      datasets: [{
        data: [statusCounts.draft, statusCounts.approved, statusCounts.completed, statusCounts.rejected],
        backgroundColor: ['#6c757d', '#0d6efd', '#198754', '#dc3545'],
      }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  } : null
  const timelineConfig = hasEstimates ? {
    type: 'bar',
    data: {
      labels: timeline.map((point) => point.date),
      datasets: [{ label: 'Estimates created', data: timeline.map((point) => point.count), backgroundColor: '#198754' }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  } : null

  return (
    <div className="row g-4 mb-4">
      <div className="col-lg-5">
        <section className="card border-0 shadow-sm h-100"><div className="card-body p-4">
          <h2 className="h5">Quotation Status</h2>
          <div className="dashboard-chart">
            {doughnutConfig
              ? <ChartCanvas config={doughnutConfig} label="Quotation status doughnut chart" />
              : <p className="text-secondary text-center py-5">Create a quotation to view status analytics.</p>}
          </div>
        </div></section>
      </div>
      <div className="col-lg-7">
        <section className="card border-0 shadow-sm h-100"><div className="card-body p-4">
          <h2 className="h5">Estimate Timeline</h2>
          <div className="dashboard-chart">
            {timelineConfig
              ? <ChartCanvas config={timelineConfig} label="Estimate creation timeline chart" />
              : <p className="text-secondary text-center py-5">Create an estimate to view timeline analytics.</p>}
          </div>
        </div></section>
      </div>
    </div>
  )
}
