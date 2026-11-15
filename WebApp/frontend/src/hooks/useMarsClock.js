import { useState, useEffect } from 'react'

export const MARS_SOL_SECONDS = 88775.244
export const MARS_EPOCH_JD = 2405521.813
export const JEZERO_LONGITUDE_DEG = 77.58

function earthToJd(year, month, day, hour = 0, minute = 0, second = 0) {
  if (month <= 2) {
    year -= 1
    month += 12
  }
  const A = Math.floor(year / 100)
  const B = 2 - A + Math.floor(A / 4)
  const jd = Math.floor(365.25 * (year + 4716)) +
    Math.floor(30.6001 * (month + 1)) +
    day + B - 1524.5 +
    (hour + minute / 60 + second / 3600) / 24
  return jd
}

function marsSolCount(landingDate, referenceDate) {
  const landingJd = earthToJd(
    landingDate.getFullYear(),
    landingDate.getMonth() + 1,
    landingDate.getDate()
  )
  const refJd = earthToJd(
    referenceDate.getFullYear(),
    referenceDate.getMonth() + 1,
    referenceDate.getDate(),
    referenceDate.getHours(),
    referenceDate.getMinutes(),
    referenceDate.getSeconds()
  )
  return (refJd - landingJd) * 86400 / MARS_SOL_SECONDS
}

function marsMtc(date) {
  const jd = earthToJd(
    date.getFullYear(),
    date.getMonth() + 1,
    date.getDate(),
    date.getHours(),
    date.getMinutes(),
    date.getSeconds()
  )
  const mtcFraction = (jd - MARS_EPOCH_JD) * 86400 / MARS_SOL_SECONDS
  return mtcFraction % 24
}

function lmst(mtcVal, longitudeDeg) {
  return (mtcVal + longitudeDeg / 15) % 24
}

export function useMarsClock(landingDate = new Date('2021-02-18')) {
  const [sol, setSol] = useState(0)
  const [mtc, setMtc] = useState(0)

  useEffect(() => {
    const updateClock = () => {
      const now = new Date()
      const count = marsSolCount(landingDate, now)
      setSol(count < 0 ? 0 : count)
      setMtc(marsMtc(now))
    }
    updateClock()
    const interval = setInterval(updateClock, 1000)
    return () => clearInterval(interval)
  }, [landingDate])

  const landingDateObj = new Date(landingDate)
  const solsElapsed = marsSolCount(landingDate, new Date())
  const totalSeconds = solsElapsed * MARS_SOL_SECONDS
  const terrestrialEquivalent = new Date(
    landingDateObj.getTime() + totalSeconds * 1000
  )

  return {
    landingDate: landingDateObj,

    sol,
    solCount: Math.max(0, Math.floor(solsElapsed)),
    mtc,
    lmst: lmst(mtc, JEZERO_LONGITUDE_DEG),
    terrestrialEquivalent,
  }
}
