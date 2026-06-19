// ============================================================================
// Viral Clip Studio — Admin Panel (UI shell)
// ============================================================================
// This is a FRONT-END SCAFFOLD ONLY. Every list below is mock/in-memory state
// so the screens render and behave like a real app, but nothing here actually
// calls a backend yet. Each "TODO" comment marks exactly where a real
// implementation needs to be wired in:
//   - GET/POST endpoints for settings, providers, platforms, queue, schedule
//   - OAuth redirect flows for YouTube / TikTok / Instagram / Facebook
//   - Secure server-side storage for API keys (never keep real keys in
//     client-side state/localStorage in production — this UI only holds
//     them in memory for editing, then should POST them to a backend that
//     stores them encrypted)
// Drop this into your project and start replacing the mock handlers.
// ============================================================================

import { useState } from 'react';
import {
  LayoutDashboard, Radar, Sparkles, Share2, ListChecks, CalendarClock,
  Plus, Trash2, Check, X, Clock, TrendingUp, KeyRound, Wifi, WifiOff,
  RefreshCw, DollarSign, AlertCircle, Eye, EyeOff,
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'scrape', label: 'Scrape', icon: Radar },
  { id: 'providers', label: 'AI providers', icon: Sparkles },
  { id: 'platforms', label: 'Platforms', icon: Share2 },
  { id: 'queue', label: 'Story queue', icon: ListChecks },
  { id: 'schedule', label: 'Schedule', icon: CalendarClock },
];

const WINDOW_OPTIONS = [
  { id: '1h', label: 'Last hour' },
  { id: '6h', label: 'Last 6 hours' },
  { id: '12h', label: 'Last 12 hours' },
  { id: '24h', label: 'Last 24 hours' },
  { id: '3d', label: 'Last 3 days' },
];

const SOURCE_DEFAULTS = [
  { id: 'gdelt', name: 'GDELT', desc: 'Global news index, updated every 15 min', enabled: true },
  { id: 'reddit', name: 'Reddit', desc: 'r/all + r/popular, hot/top filtered by window', enabled: true },
  { id: 'newsapi', name: 'NewsAPI', desc: 'Aggregated headlines across outlets', enabled: true },
  { id: 'gtrends', name: 'Google Trends', desc: 'Realtime search interest by region', enabled: false },
  { id: 'ytrending', name: 'YouTube trending', desc: 'YouTube Data API trending feed', enabled: false },
];

const PROVIDER_DEFAULTS = [
  { id: 'p1', name: 'DeepSeek', role: 'Prompt generation', apiKey: '', endpoint: 'https://api.deepseek.com', enabled: true },
  { id: 'p2', name: 'Creatomate', role: 'Video assembly', apiKey: '', endpoint: '', enabled: true },
  { id: 'p3', name: 'ElevenLabs', role: 'Voiceover (TTS)', apiKey: '', endpoint: '', enabled: true },
  { id: 'p4', name: 'HeyGen', role: 'AI avatar narration', apiKey: '', endpoint: '', enabled: false },
];

const PLATFORM_DEFAULTS = [
  { id: 'youtube', name: 'YouTube Shorts', connected: false, dailyCap: 6, enabled: true },
  { id: 'tiktok', name: 'TikTok', connected: false, dailyCap: 15, enabled: true },
  { id: 'instagram', name: 'Instagram Reels', connected: false, dailyCap: 10, enabled: true },
  { id: 'facebook', name: 'Facebook Reels', connected: false, dailyCap: 10, enabled: true },
];

const QUEUE_SEED = [
  { id: 1, title: 'Sample scraped story headline goes here', source: 'GDELT', score: 92, window: '1h', status: 'pending', spottedAt: '12 min ago' },
  { id: 2, title: 'Another placeholder trending story candidate', source: 'Reddit', score: 81, window: '6h', status: 'generating', spottedAt: '38 min ago' },
  { id: 3, title: 'Third example story used to preview the ready state', source: 'NewsAPI', score: 74, window: '24h', status: 'ready', spottedAt: '2 hr ago' },
  { id: 4, title: 'Fourth example, already rejected during review', source: 'Reddit', score: 58, window: '24h', status: 'rejected', spottedAt: '5 hr ago' },
];

const SCHEDULE_SEED = [
  { id: 1, title: 'Third example story used to preview the ready state', platform: 'YouTube Shorts', when: 'Today, 6:00 PM', status: 'scheduled' },
  { id: 2, title: 'A previously generated clip', platform: 'TikTok', when: 'Today, 6:15 PM', status: 'scheduled' },
  { id: 3, title: 'An older clip from this morning', platform: 'Instagram Reels', when: 'Today, 9:00 AM', status: 'published' },
];

function ScoreBadge({ score }) {
  const tone = score >= 85 ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
    : score >= 70 ? 'bg-amber-950 text-amber-300 border-amber-800'
    : 'bg-zinc-800 text-zinc-400 border-zinc-700';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-mono ${tone}`}>
      <TrendingUp className="h-3 w-3" /> {score}
    </span>
  );
}

function StatusBadge({ status }) {
  const map = {
    pending: 'bg-zinc-800 text-zinc-300 border-zinc-700',
    generating: 'bg-sky-950 text-sky-300 border-sky-800',
    ready: 'bg-emerald-950 text-emerald-300 border-emerald-800',
    published: 'bg-violet-950 text-violet-300 border-violet-800',
    rejected: 'bg-rose-950 text-rose-300 border-rose-800',
    scheduled: 'bg-amber-950 text-amber-300 border-amber-800',
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs capitalize ${map[status] || map.pending}`}>
      {status}
    </span>
  );
}

function Card({ children, className = '' }) {
  return (
    <div className={`rounded-lg border border-zinc-800 bg-zinc-900 ${className}`}>
      {children}
    </div>
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${checked ? 'bg-amber-500' : 'bg-zinc-700'}`}
      aria-pressed={checked}
    >
      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-zinc-950 transition-transform ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
    </button>
  );
}

export default function ViralClipStudioAdmin() {
  const [activeTab, setActiveTab] = useState('overview');

  const [scrapeWindow, setScrapeWindow] = useState('6h');
  const [frequency, setFrequency] = useState('30');
  const [sources, setSources] = useState(SOURCE_DEFAULTS);

  const [providers, setProviders] = useState(PROVIDER_DEFAULTS);
  const [visibleKeys, setVisibleKeys] = useState({});
  const [dailyBudget, setDailyBudget] = useState(15);

  const [platforms, setPlatforms] = useState(PLATFORM_DEFAULTS);

  const [queue, setQueue] = useState(QUEUE_SEED);

  // --- handlers (mock — replace bodies with real API calls) ----------------

  function toggleSource(id) {
    setSources((prev) => prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s)));
    // TODO: PATCH /api/scrape/sources/:id
  }

  function saveScrapeSettings() {
    // TODO: POST /api/scrape/settings  { window: scrapeWindow, frequency, sources }
    console.log('Saving scrape settings', { scrapeWindow, frequency, sources });
  }

  function updateProvider(id, field, value) {
    setProviders((prev) => prev.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  }

  function addProvider() {
    const id = `p${Date.now()}`;
    setProviders((prev) => [...prev, { id, name: 'New provider', role: '', apiKey: '', endpoint: '', enabled: false }]);
  }

  function removeProvider(id) {
    setProviders((prev) => prev.filter((p) => p.id !== id));
    // TODO: DELETE /api/providers/:id
  }

  function saveProviders() {
    // TODO: POST /api/providers — send keys to backend over HTTPS, store
    // them server-side (encrypted at rest). Do not persist real keys in
    // client state beyond the editing session.
    console.log('Saving providers', providers, 'daily budget cap ($):', dailyBudget);
  }

  function toggleConnect(id) {
    setPlatforms((prev) => prev.map((p) => (p.id === id ? { ...p, connected: !p.connected } : p)));
    // TODO: if connecting — redirect to `/auth/${id}/start` to kick off
    // that platform's OAuth flow; if disconnecting — DELETE /api/platforms/:id/token
  }

  function updateDailyCap(id, value) {
    setPlatforms((prev) => prev.map((p) => (p.id === id ? { ...p, dailyCap: Number(value) } : p)));
  }

  function togglePlatformEnabled(id) {
    setPlatforms((prev) => prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p)));
  }

  function approveStory(id) {
    setQueue((prev) => prev.map((q) => (q.id === id ? { ...q, status: 'generating' } : q)));
    // TODO: POST /api/queue/:id/approve — kicks off the create pipeline
  }

  function rejectStory(id) {
    setQueue((prev) => prev.map((q) => (q.id === id ? { ...q, status: 'rejected' } : q)));
    // TODO: POST /api/queue/:id/reject
  }

  function refreshQueue() {
    // TODO: GET /api/queue?window=scrapeWindow
    console.log('Refreshing queue for window', scrapeWindow);
  }

  const pendingCount = queue.filter((q) => q.status === 'pending').length;
  const generatingCount = queue.filter((q) => q.status === 'generating').length;
  const readyCount = queue.filter((q) => q.status === 'ready').length;

  return (
    <div className="flex min-h-[700px] w-full overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 font-sans text-zinc-100">
      {/* Sidebar */}
      <aside className="flex w-56 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 p-4">
        <div className="mb-6 px-2">
          <div className="text-sm font-medium text-zinc-100">Viral clip studio</div>
          <div className="text-xs text-zinc-500">Admin panel</div>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                  active ? 'bg-amber-500 text-amber-950' : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100'
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col">
        {/* Live ticker strip */}
        <div className="flex items-center gap-3 border-b border-zinc-800 bg-zinc-900 px-4 py-2 text-xs text-zinc-400">
          <span className="flex items-center gap-1.5 font-mono text-amber-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
            LIVE SCRAPE · {WINDOW_OPTIONS.find((w) => w.id === scrapeWindow)?.label}
          </span>
          <span className="text-zinc-700">|</span>
          <div className="flex flex-1 gap-4 overflow-hidden whitespace-nowrap">
            {queue.slice(0, 3).map((q) => (
              <span key={q.id} className="flex items-center gap-1.5 text-zinc-400">
                <span className="font-mono text-zinc-600">{q.source}</span> {q.title}
              </span>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && (
            <div className="flex flex-col gap-6">
              <div>
                <h1 className="text-lg font-medium text-zinc-100">Overview</h1>
                <p className="text-sm text-zinc-500">Pipeline status across scrape, create, and publish.</p>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-zinc-500">Pending review</div>
                  <div className="mt-1 text-2xl font-medium">{pendingCount}</div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-zinc-500">Generating now</div>
                  <div className="mt-1 text-2xl font-medium">{generatingCount}</div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-zinc-500">Ready to publish</div>
                  <div className="mt-1 text-2xl font-medium">{readyCount}</div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-zinc-500">Budget used today</div>
                  <div className="mt-1 text-2xl font-medium">$0 <span className="text-sm text-zinc-500">/ ${dailyBudget}</span></div>
                </Card>
              </div>

              <Card className="p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div className="text-sm font-medium text-zinc-200">Latest scraped stories</div>
                  <button onClick={refreshQueue} className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200">
                    <RefreshCw className="h-3.5 w-3.5" /> Refresh
                  </button>
                </div>
                <div className="flex flex-col divide-y divide-zinc-800">
                  {queue.map((q) => (
                    <div key={q.id} className="flex items-center gap-3 py-2.5 text-sm">
                      <ScoreBadge score={q.score} />
                      <span className="flex-1 truncate text-zinc-300">{q.title}</span>
                      <span className="text-xs text-zinc-500">{q.spottedAt}</span>
                      <StatusBadge status={q.status} />
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {activeTab === 'scrape' && (
            <div className="flex flex-col gap-6">
              <div>
                <h1 className="text-lg font-medium text-zinc-100">Scrape settings</h1>
                <p className="text-sm text-zinc-500">Choose how far back to look for viral moments, and which sources to pull from.</p>
              </div>

              <Card className="p-4">
                <div className="mb-3 text-sm font-medium text-zinc-200">Time window</div>
                <div className="flex flex-wrap gap-2">
                  {WINDOW_OPTIONS.map((w) => (
                    <button
                      key={w.id}
                      onClick={() => setScrapeWindow(w.id)}
                      className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                        scrapeWindow === w.id
                          ? 'border-amber-500 bg-amber-500 text-amber-950'
                          : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'
                      }`}
                    >
                      {w.label}
                    </button>
                  ))}
                </div>

                <div className="mt-5 flex items-center gap-3">
                  <Clock className="h-4 w-4 text-zinc-500" />
                  <span className="text-sm text-zinc-400">Check sources every</span>
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-200"
                  >
                    <option value="15">15 minutes</option>
                    <option value="30">30 minutes</option>
                    <option value="60">60 minutes</option>
                  </select>
                </div>
              </Card>

              <Card className="p-4">
                <div className="mb-3 text-sm font-medium text-zinc-200">Sources</div>
                <div className="flex flex-col divide-y divide-zinc-800">
                  {sources.map((s) => (
                    <div key={s.id} className="flex items-center gap-3 py-3">
                      <Toggle checked={s.enabled} onChange={() => toggleSource(s.id)} />
                      <div className="flex-1">
                        <div className="text-sm text-zinc-200">{s.name}</div>
                        <div className="text-xs text-zinc-500">{s.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <div>
                <button onClick={saveScrapeSettings} className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-400">
                  Save scrape settings
                </button>
              </div>
            </div>
          )}

          {activeTab === 'providers' && (
            <div className="flex flex-col gap-6">
              <div>
                <h1 className="text-lg font-medium text-zinc-100">AI providers</h1>
                <p className="text-sm text-zinc-500">Connect the APIs used for prompt generation, video creation, and voiceover.</p>
              </div>

              <Card className="p-4">
                <div className="flex items-center gap-3">
                  <DollarSign className="h-4 w-4 text-zinc-500" />
                  <span className="text-sm text-zinc-400">Daily generation budget cap</span>
                  <input
                    type="number"
                    value={dailyBudget}
                    onChange={(e) => setDailyBudget(Number(e.target.value))}
                    className="w-24 rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-200"
                  />
                  <span className="text-sm text-zinc-500">USD / day</span>
                </div>
              </Card>

              <div className="flex flex-col gap-3">
                {providers.map((p) => (
                  <Card key={p.id} className="p-4">
                    <div className="flex items-start gap-4">
                      <div className="grid flex-1 grid-cols-2 gap-3">
                        <div>
                          <label className="mb-1 block text-xs text-zinc-500">Name</label>
                          <input
                            value={p.name}
                            onChange={(e) => updateProvider(p.id, 'name', e.target.value)}
                            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-sm text-zinc-200"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs text-zinc-500">Role</label>
                          <input
                            value={p.role}
                            onChange={(e) => updateProvider(p.id, 'role', e.target.value)}
                            placeholder="e.g. video assembly"
                            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-sm text-zinc-200"
                          />
                        </div>
                        <div className="col-span-2">
                          <label className="mb-1 flex items-center gap-1 text-xs text-zinc-500">
                            <KeyRound className="h-3 w-3" /> API key
                          </label>
                          <div className="flex items-center gap-2">
                            <input
                              type={visibleKeys[p.id] ? 'text' : 'password'}
                              value={p.apiKey}
                              onChange={(e) => updateProvider(p.id, 'apiKey', e.target.value)}
                              placeholder="sk-..."
                              className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono text-sm text-zinc-200"
                            />
                            <button
                              type="button"
                              onClick={() => setVisibleKeys((v) => ({ ...v, [p.id]: !v[p.id] }))}
                              className="rounded-md border border-zinc-700 p-1.5 text-zinc-400 hover:text-zinc-200"
                            >
                              {visibleKeys[p.id] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                            </button>
                          </div>
                        </div>
                        <div className="col-span-2">
                          <label className="mb-1 block text-xs text-zinc-500">Endpoint (optional override)</label>
                          <input
                            value={p.endpoint}
                            onChange={(e) => updateProvider(p.id, 'endpoint', e.target.value)}
                            placeholder="https://api.example.com"
                            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono text-sm text-zinc-200"
                          />
                        </div>
                      </div>
                      <div className="flex flex-col items-center gap-3 pt-5">
                        <Toggle checked={p.enabled} onChange={() => updateProvider(p.id, 'enabled', !p.enabled)} />
                        <button onClick={() => removeProvider(p.id)} className="text-zinc-500 hover:text-rose-400">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              <div className="flex gap-3">
                <button onClick={addProvider} className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-900">
                  <Plus className="h-4 w-4" /> Add provider
                </button>
                <button onClick={saveProviders} className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-400">
                  Save providers
                </button>
              </div>
            </div>
          )}

          {activeTab === 'platforms' && (
            <div className="flex flex-col gap-6">
              <div>
                <h1 className="text-lg font-medium text-zinc-100">Platforms</h1>
                <p className="text-sm text-zinc-500">Connect the accounts you want to publish to, and cap how often each one posts.</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {platforms.map((p) => (
                  <Card key={p.id} className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium text-zinc-200">{p.name}</div>
                      <Toggle checked={p.enabled} onChange={() => togglePlatformEnabled(p.id)} />
                    </div>

                    <div className="mt-3 flex items-center gap-2 text-xs">
                      {p.connected ? (
                        <span className="flex items-center gap-1 text-emerald-400"><Wifi className="h-3.5 w-3.5" /> Connected</span>
                      ) : (
                        <span className="flex items-center gap-1 text-zinc-500"><WifiOff className="h-3.5 w-3.5" /> Not connected</span>
                      )}
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-zinc-500">Daily cap</span>
                        <input
                          type="number"
                          value={p.dailyCap}
                          onChange={(e) => updateDailyCap(p.id, e.target.value)}
                          className="w-16 rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-200"
                        />
                      </div>
                      <button
                        onClick={() => toggleConnect(p.id)}
                        className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                          p.connected ? 'border border-zinc-700 text-zinc-300 hover:bg-zinc-900' : 'bg-amber-500 text-amber-950 hover:bg-amber-400'
                        }`}
                      >
                        {p.connected ? 'Disconnect' : 'Connect'}
                      </button>
                    </div>
                  </Card>
                ))}
              </div>

              <Card className="flex items-start gap-2 p-4 text-xs text-zinc-500">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  "Connect" should redirect into that platform's OAuth flow on your backend
                  (e.g. <code className="font-mono text-zinc-400">/auth/youtube/start</code>) rather than
                  storing any token here — this panel only reflects connection status.
                </span>
              </Card>
            </div>
          )}

          {activeTab === 'queue' && (
            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-lg font-medium text-zinc-100">Story queue</h1>
                  <p className="text-sm text-zinc-500">Review scraped candidates before they're sent to the create pipeline.</p>
                </div>
                <button onClick={refreshQueue} className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-900">
                  <RefreshCw className="h-3.5 w-3.5" /> Refresh
                </button>
              </div>

              <Card>
                <div className="flex flex-col divide-y divide-zinc-800">
                  {queue.map((q) => (
                    <div key={q.id} className="flex items-center gap-4 p-4">
                      <ScoreBadge score={q.score} />
                      <div className="flex-1">
                        <div className="text-sm text-zinc-200">{q.title}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                          <span className="font-mono">{q.source}</span>
                          <span>·</span>
                          <span>window: {q.window}</span>
                          <span>·</span>
                          <span>{q.spottedAt}</span>
                        </div>
                      </div>
                      <StatusBadge status={q.status} />
                      {q.status === 'pending' && (
                        <div className="flex gap-2">
                          <button onClick={() => approveStory(q.id)} className="flex items-center gap-1 rounded-md bg-emerald-500 px-3 py-1.5 text-xs font-medium text-emerald-950 hover:bg-emerald-400">
                            <Check className="h-3.5 w-3.5" /> Approve
                          </button>
                          <button onClick={() => rejectStory(q.id)} className="flex items-center gap-1 rounded-md border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-900">
                            <X className="h-3.5 w-3.5" /> Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {activeTab === 'schedule' && (
            <div className="flex flex-col gap-6">
              <div>
                <h1 className="text-lg font-medium text-zinc-100">Schedule</h1>
                <p className="text-sm text-zinc-500">Upcoming and recently published posts across all connected platforms.</p>
              </div>

              <Card>
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                      <th className="px-4 py-3 font-normal">Clip</th>
                      <th className="px-4 py-3 font-normal">Platform</th>
                      <th className="px-4 py-3 font-normal">When</th>
                      <th className="px-4 py-3 font-normal">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {SCHEDULE_SEED.map((s) => (
                      <tr key={s.id}>
                        <td className="px-4 py-3 text-zinc-300">{s.title}</td>
                        <td className="px-4 py-3 text-zinc-400">{s.platform}</td>
                        <td className="px-4 py-3 text-zinc-400">{s.when}</td>
                        <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
