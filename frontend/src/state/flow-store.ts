import { createContext } from "react"

export type FlowState = {
  uploadIds: string[]
  mappingsConfirmed: boolean
  reviewStarted: boolean
  metricCreated: boolean
}

export type FlowContextValue = FlowState & {
  updateFlow: (update: Partial<FlowState>) => void
  resetFlow: () => void
}

export const initialFlowState: FlowState = {
  uploadIds: [],
  mappingsConfirmed: false,
  reviewStarted: false,
  metricCreated: false,
}

export const FlowContext = createContext<FlowContextValue | null>(null)
