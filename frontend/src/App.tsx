import { useEffect, type ReactNode } from "react"
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom"

import { getMappings, getReport, getUploads } from "./lib/api"
import { LandingPage } from "./pages/LandingPage"
import { MatchPage } from "./pages/MatchPage"
import { MetricsPage } from "./pages/MetricsPage"
import { ReportPage } from "./pages/ReportPage"
import { ReviewPage } from "./pages/ReviewPage"
import { UploadPage } from "./pages/UploadPage"
import { FlowProvider } from "./state/FlowContext"
import { useFlow } from "./state/useFlow"

export default function App() {
  return <BrowserRouter><FlowProvider><HydratedRoutes /></FlowProvider></BrowserRouter>
}

function HydratedRoutes() {
  const { updateFlow } = useFlow()

  useEffect(() => {
    Promise.allSettled([getUploads(), getMappings(), getReport()]).then(([uploads, mappings, report]) => {
      updateFlow({
        uploadIds: uploads.status === "fulfilled" ? uploads.value.map((item) => item.id) : [],
        mappingsConfirmed: mappings.status === "fulfilled" && mappings.value.some((item) => item.status === "confirmed"),
        reviewStarted: false,
        metricCreated: report.status === "fulfilled" && report.value.metrics.length > 0,
      })
    })
  }, [updateFlow])

  return <><ScrollToTop /><Routes><Route path="/" element={<LandingPage />} /><Route path="/upload" element={<UploadPage />} /><Route path="/match" element={<Guard requires="upload"><MatchPage /></Guard>} /><Route path="/review" element={<Guard requires="mapping"><ReviewPage /></Guard>} /><Route path="/metrics" element={<Guard requires="mapping"><MetricsPage /></Guard>} /><Route path="/report" element={<ReportPage />} /><Route path="/shared/:token" element={<ReportPage shared />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></>
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function Guard({ requires, children }: { requires: "upload" | "mapping"; children: ReactNode }) {
  const flow = useFlow()
  const location = useLocation()
  if (requires === "upload" && !flow.uploadIds.length) return <Navigate to="/upload" replace state={{ notice: `Add a file before opening ${location.pathname.slice(1)}.` }} />
  if (requires === "mapping" && !flow.mappingsConfirmed) return <Navigate to={flow.uploadIds.length ? "/match" : "/upload"} replace state={{ notice: `Confirm column mappings before opening ${location.pathname.slice(1)}.` }} />
  return children
}
