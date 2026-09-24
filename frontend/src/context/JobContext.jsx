import { createContext, useContext, useState } from 'react'

const JobContext = createContext(null)

export function JobProvider({ children }) {
  const [isJobRunning, setIsJobRunning] = useState(false)
  return (
    <JobContext.Provider value={{ isJobRunning, setIsJobRunning }}>
      {children}
    </JobContext.Provider>
  )
}

export function useJob() {
  return useContext(JobContext)
}