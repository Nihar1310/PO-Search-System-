import { useEffect, useRef, useState } from 'react'
import { RefreshCw, LogIn, LogOut, Database } from 'lucide-react'
import { disconnectAuth, getAuthLoginUrl, triggerSync } from '../services/api'
import GlassButton from './GlassButton'

const BACKEND_ORIGIN = (() => {
  try {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    return new URL(base).origin
  } catch (err) {
    return 'http://localhost:8000'
  }
})()

export default function ConnectionPanel({ authState, onRefresh }) {
  const [busyAction, setBusyAction] = useState(null)
  const [infoMessage, setInfoMessage] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [lastSync, setLastSync] = useState(null)
  const oauthWindowRef = useRef(null)

  useEffect(() => {
    const handleOAuthMessage = async (event) => {
      if (!event?.data || event.origin !== BACKEND_ORIGIN) return
      if (event.data?.type === 'po-auth-success') {
        oauthWindowRef.current?.close()
        oauthWindowRef.current = null
        setErrorMessage(null)
        setInfoMessage('Google account connected! Refreshing status…')
        setBusyAction('refresh')

        if (typeof onRefresh === 'function') {
          try {
            await onRefresh()
            setInfoMessage('Google account connected! Ready to sync your POs.')
          } catch (err) {
            setErrorMessage('Connected, but failed to refresh status automatically. Click “Refresh Status”.')
          }
        }

        setBusyAction(null)
      }
    }

    window.addEventListener('message', handleOAuthMessage)
    return () => {
      window.removeEventListener('message', handleOAuthMessage)
    }
  }, [onRefresh])

  const handleConnect = async () => {
    setBusyAction('connect')
    setErrorMessage(null)
    setInfoMessage(null)
    try {
      const { auth_url: authUrl } = await getAuthLoginUrl()
      if (authUrl) {
        const popup = window.open(authUrl, '_blank', 'noopener,noreferrer')
        if (!popup) {
          setErrorMessage('Popup blocked. Allow popups for this site and try again.')
          return
        }
        oauthWindowRef.current = popup
        setInfoMessage('Complete Google consent in the new tab. We will refresh automatically.')
      }
    } catch (err) {
      setErrorMessage('Failed to initiate Google OAuth. Check backend logs.')
    } finally {
      setBusyAction(null)
    }
  }

  const handleDisconnect = async () => {
    setBusyAction('disconnect')
    setErrorMessage(null)
    try {
      await disconnectAuth()
      setInfoMessage('Disconnected from Google. Reconnect when ready.')
      onRefresh()
    } catch (err) {
      setErrorMessage('Failed to disconnect credentials.')
    } finally {
      setBusyAction(null)
    }
  }

  const handleSync = async () => {
    setBusyAction('sync')
    setErrorMessage(null)
    setInfoMessage(null)
    try {
      const response = await triggerSync()
      setLastSync(response)
      const { status, summary } = response
      const baseMessage = status === 'completed'
        ? `Synced successfully. ${summary.ingested} new POs saved.`
        : status === 'no_changes'
          ? 'Sync completed. No new POs were found.'
          : `Sync status: ${status}.`
      setInfoMessage(baseMessage)
      if (summary.errors?.length) {
        setErrorMessage('Some documents failed to sync. Check backend logs for details.')
      }
    } catch (err) {
      setErrorMessage('Failed to trigger sync. Ensure backend is running.')
    } finally {
      setBusyAction(null)
    }
  }

  const handleRefresh = async () => {
    setBusyAction('refresh')
    setInfoMessage(null)
    setErrorMessage(null)
    await onRefresh()
    setBusyAction(null)
  }

  return (
    <div className="glass rounded-2xl shadow-xl border border-white/20 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">Google Connection</h2>
          {authState.loading ? (
            <p className="text-sm text-gray-500">Checking status…</p>
          ) : authState.error ? (
            <p className="text-sm text-red-600">{authState.error}</p>
          ) : authState.connected ? (
            <p className="text-sm text-green-600">Connected to Gmail & Drive.</p>
          ) : (
            <p className="text-sm text-gray-600">Not connected. Authorize to enable PO search.</p>
          )}
        </div>
        <GlassButton
          type="button"
          variant="ghost"
          icon={RefreshCw}
          loading={busyAction === 'refresh'}
          onClick={handleRefresh}
          disabled={busyAction === 'refresh'}
          className="px-5 py-2 text-sm"
        >
          {busyAction === 'refresh' ? 'Refreshing…' : 'Refresh Status'}
        </GlassButton>
      </div>

      <div className="flex flex-wrap gap-3">
        {authState.connected ? (
          <GlassButton
            type="button"
            variant="danger"
            icon={LogOut}
            loading={busyAction === 'disconnect'}
            onClick={handleDisconnect}
            disabled={busyAction === 'disconnect'}
            className="px-6 py-2 text-sm"
          >
            {busyAction === 'disconnect' ? 'Disconnecting…' : 'Disconnect'}
          </GlassButton>
        ) : (
          <GlassButton
            type="button"
            variant="primary"
            icon={LogIn}
            loading={busyAction === 'connect'}
            onClick={handleConnect}
            disabled={busyAction === 'connect'}
            className="px-6 py-2 text-sm"
          >
            {busyAction === 'connect' ? 'Opening…' : 'Connect Google'}
          </GlassButton>
        )}
        <GlassButton
          type="button"
          variant="neutral"
          icon={Database}
          loading={busyAction === 'sync'}
          onClick={handleSync}
          disabled={!authState.connected || busyAction === 'sync'}
          className="px-6 py-2 text-sm"
        >
          {busyAction === 'sync' ? 'Syncing…' : 'Trigger Sync'}
        </GlassButton>
      </div>

      {infoMessage && <p className="text-sm text-blue-600">{infoMessage}</p>}
      {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}

      {lastSync && (
        <div className="rounded-xl border border-white/40 bg-white/70 p-4 text-sm text-gray-700 space-y-2">
          <div className="flex justify-between">
            <span className="font-medium">Source</span>
            <span className="font-medium">Fetched</span>
          </div>
          {['gmail', 'drive'].map((source) => (
            <div key={source} className="flex justify-between text-xs md:text-sm">
              <span className="capitalize">{source}</span>
              <span>
                {lastSync.summary.sources[source].fetched}
                {lastSync.summary.sources[source].error && (
                  <span className="text-red-500"> (error)</span>
                )}
              </span>
            </div>
          ))}
          <div className="pt-2 border-t border-white/40 grid grid-cols-2 gap-2 text-xs md:text-sm">
            <div>New POs: <span className="font-semibold">{lastSync.summary.ingested}</span></div>
            <div>Duplicates: <span className="font-semibold">{lastSync.summary.duplicates}</span></div>
          </div>
        </div>
      )}
    </div>
  )
}
