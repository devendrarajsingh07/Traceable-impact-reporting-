import { useContext } from "react"

import { FlowContext } from "./flow-store"

export function useFlow() {
  const context = useContext(FlowContext)
  if (!context) throw new Error("useFlow must be used inside FlowProvider")
  return context
}
