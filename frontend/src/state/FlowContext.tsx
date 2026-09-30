import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"

import { FlowContext, initialFlowState, type FlowContextValue, type FlowState } from "./flow-store"

function readStoredState(): FlowState {
  try {
    const stored = window.localStorage.getItem("traceable-flow")
    return stored ? { ...initialFlowState, ...JSON.parse(stored) } : initialFlowState
  } catch {
    return initialFlowState
  }
}

export function FlowProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<FlowState>(readStoredState)
  const updateFlow = useCallback((update: Partial<FlowState>) => setState((current) => ({ ...current, ...update })), [])
  const resetFlow = useCallback(() => setState(initialFlowState), [])

  useEffect(() => {
    window.localStorage.setItem("traceable-flow", JSON.stringify(state))
  }, [state])

  const value = useMemo<FlowContextValue>(() => ({
    ...state,
    updateFlow,
    resetFlow,
  }), [resetFlow, state, updateFlow])

  return <FlowContext.Provider value={value}>{children}</FlowContext.Provider>
}
