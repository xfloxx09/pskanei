import { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard, Radar, Sparkles, Share2, ListChecks, CalendarClock,
  Plus, Trash2, Check, X, Clock, TrendingUp, KeyRound, Wifi, WifiOff,
  RefreshCw, DollarSign, AlertCircle, Eye, EyeOff,
} from 'lucide-react';

const API = '/api';

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

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

function ScoreBadge({ score, aiScore, isTopPick }) {
  const tone = score >= 85 ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
    : score >= 70 ? 'bg-amber-950 text-amber-300 border-amber-800'
    : 'bg-zinc-800 text-zinc-400 border-zinc-700';
  return (
    <div className="flex items-center gap-1.5">
      <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-mono ${tone} ${isTopPick ? 'ring-1 ring-amber-400' : ''}`}>
        <TrendingUp className="h-3 w-3" /> {score}
      </span>
      {aiScore != null && (
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-mono ${
          aiScore >= 80 ? 'bg-purple-950 text-purple-300 border-purple-800' :
          aiScore >= 60 ? 'bg-sky-950 text-sky-300 border-sky-800' :
          'bg-zinc-800 text-zinc-400 border-zinc-700'
        }`}>
          <Sparkles className="h-3 w-3" /> {aiScore}
        </span>
      )}
      {isTopPick && <span className="text-amber-400 text-xs" title="AI Top Pick">&#9733;</span>}
    </div>
  );
}

function CategoryBadge({ category }) {
  if (!category) return null;
  const colors = {
    finance: 'bg-green-950 text-green-300 border-green-800',
    tech: 'bg-blue-950 text-blue-300 border-blue-800',
    politics: 'bg-red-950 text-red-300 border-red-800',
    entertainment: 'bg-pink-950 text-pink-300 border-pink-800',
    science: 'bg-cyan-950 text-cyan-300 border-cyan-800',
    sports: 'bg-orange-950 text-orange-300 border-orange-800',
    weird: 'bg-yellow-950 text-yellow-300 border-yellow-800',
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs capitalize ${colors[category] || 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>
      {category}
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
    failed: 'bg-rose-950 text-rose-300 border-rose-800',
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

function fmtWhen(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffMin = Math.floor((now - d) / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hr ago`;
  return d.toLocaleDateString();
}

export default function ViralClipStudioAdmin() {
  const [activeTab, setActiveTab] = useState('overview');
  const [scrapeWindow, setScrapeWindow] = useState('6h');
  const [frequency, setFrequency] = useState('30');
  const [sources, setSources] = useState(SOURCE_DEFAULTS);
  const [scraperKeys, setScraperKeys] = useState({});
  const [providers, setProviders] = useState(PROVIDER_DEFAULTS);
  const [visibleKeys, setVisibleKeys] = useState({});
  const [dailyBudget, setDailyBudget] = useState(15);
  const [platforms, setPlatforms] = useState(PLATFORM_DEFAULTS);
  const [queue, setQueue] = useState([]);
  const [schedule, setSchedule] = useState([]);
  const [statusCounts, setStatusCounts] = useState({ pending: 0, generating: 0, ready: 0, budget_used_today: 0 });
  const [toast, setToast] = useState('');
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);

  const showToast = useCallback((msg, duration = 8000) => {
    setToast(msg);
    setTimeout(() => setToast(''), duration);
  }, []);

  // --- Load data on mount and tab switch ---
  const loadQueue = useCallback(async () => {
    try {
      const data = await fetchJSON(`${API}/queue?limit=200`);
      setQueue(data);
    } catch { /* offline */ }
  }, []);

  const loadSchedule = useCallback(async () => {
    try {
      const data = await fetchJSON(`${API}/schedule?limit=200`);
      setSchedule(data);
    } catch { /* offline */ }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const data = await fetchJSON(`${API}/status`);
      setStatusCounts(data);
      if (data.daily_budget != null) setDailyBudget(data.daily_budget);
    } catch { /* offline */ }
  }, []);

  const loadScrapeSettings = useCallback(async () => {
    try {
      const data = await fetchJSON(`${API}/scrape/settings`);
      if (data.window) setScrapeWindow(data.window);
      if (data.frequency) setFrequency(data.frequency);
      if (data.sources?.length) setSources(data.sources);
      if (data.scraper_keys) setScraperKeys(data.scraper_keys);
    } catch { /* offline */ }
  }, []);

  const loadProviders = useCallback(async () => {
    try {
      const data = await fetchJSON(`${API}/providers`);
      if (data.providers?.length) {
        setProviders(data.providers.map(p => ({
          id: p.id,
          name: p.name,
          role: p.role,
          apiKey: p.apiKey || '',
          endpoint: p.endpoint || '',
          enabled: p.enabled,
        })));
      }
      if (data.daily_budget != null) setDailyBudget(data.daily_budget);
    } catch { /* offline */ }
  }, []);

  const loadPlatforms = useCallback(async () => {
    try {
      const data = await fetchJSON(`${API}/platforms`);
      if (data?.length) {
        setPlatforms(data.map(p => ({
          id: p.id,
          name: p.name,
          connected: p.connected,
          dailyCap: p.dailyCap,
          enabled: p.enabled,
        })));
      }
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    loadStatus();
    loadQueue();
    loadSchedule();
    loadScrapeSettings();
    loadProviders();
    loadPlatforms();
  }, [loadStatus, loadQueue, loadSchedule, loadScrapeSettings, loadProviders, loadPlatforms]);

  // --- handlers ---

  function toggleSource(id) {
    setSources((prev) => prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s)));
  }

  async function saveScrapeSettings() {
    try {
      setLoading(true);
      await fetchJSON(`${API}/scrape/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ window: scrapeWindow, frequency, sources, scraper_keys: scraperKeys }),
      });
      showToast('Scrape settings saved');
    } catch (e) {
      showToast(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
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
  }

  async function saveProviders() {
    try {
      setLoading(true);
      await fetchJSON(`${API}/providers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ providers, daily_budget: dailyBudget }),
      });
      showToast('Providers saved');
    } catch (e) {
      showToast(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  function toggleConnect(id) {
    const p = platforms.find(pl => pl.id === id);
    if (!p) return;
    if (p.connected) {
      fetchJSON(`${API}/platforms/${id}/token`, { method: 'DELETE' })
        .then(() => {
          setPlatforms(prev => prev.map(pl => pl.id === id ? { ...pl, connected: false } : pl));
          showToast(`${p.name} disconnected`);
        })
        .catch(e => showToast(`Error: ${e.message}`));
    } else {
      window.location.href = `${API}/platforms/${id}/connect`;
    }
  }

  function updateDailyCap(id, value) {
    setPlatforms((prev) => prev.map((p) => (p.id === id ? { ...p, dailyCap: Number(value) } : p)));
    fetchJSON(`${API}/platforms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platforms: platforms.map(p => ({
        id: p.id, name: p.name, connected: p.connected, dailyCap: p.id === id ? Number(value) : p.dailyCap, enabled: p.enabled,
      }))}),
    }).catch(() => {});
  }

  function togglePlatformEnabled(id) {
    setPlatforms((prev) => {
      const next = prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p));
      fetchJSON(`${API}/platforms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platforms: next.map(p => ({
          id: p.id, name: p.name, connected: p.connected, dailyCap: p.dailyCap, enabled: p.enabled,
        }))}),
      }).catch(() => {});
      return next;
    });
  }

  async function approveStory(id) {
    try {
      setLoading(true);
      await fetchJSON(`${API}/queue/${id}/approve`, { method: 'POST' });
      showToast('Story approved — generating');
      loadQueue();
      loadStatus();
    } catch (e) {
      showToast(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function rejectStory(id) {
    try {
      setLoading(true);
      await fetchJSON(`${API}/queue/${id}/reject`, { method: 'POST' });
      showToast('Story rejected');
      loadQueue();
      loadStatus();
    } catch (e) {
      showToast(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  function refreshQueue() {
    loadQueue();
    loadStatus();
  }

  async function triggerScrape() {
    setScraping(true);
    try {
      const data = await fetchJSON(`${API}/scrape/trigger`, { method: 'POST' });
      const detail = data?.detail || {};
      const saved = detail?.stories_saved ?? 0;
      const status = detail?.status ?? 'done';
      const counts = detail?.source_counts || {};
      const errors = detail?.source_errors || {};

      if (data?.error) {
        showToast(`Scrape failed: ${data.error}`);
      } else if (status === 'skipped') {
        const countStr = Object.entries(counts).map(([k, v]) => `${k}=${v}`).join(', ');
        const errStr = Object.entries(errors).map(([k, v]) => `${k}: ${v}`).join('; ');
        const info = [countStr, errStr].filter(Boolean).join(' | ');
        showToast(`${detail?.reason || 'Scrape skipped'}${info ? ` (${info})` : ''}`, 10000);
      } else if (saved > 0) {
        const curated = detail?.ai_curated || 0;
        showToast(`${saved} stories found${curated ? `, ${curated} AI-curated` : ''}`, 5000);
      } else {
        const errStr = Object.entries(errors).map(([k, v]) => `${k}: ${v}`).join('; ');
        showToast(`No stories found${errStr ? ' — ' + errStr : ''}`, 10000);
      }
      await loadQueue();
      await loadStatus();
    } catch (e) {
      showToast(`Scrape failed: ${e.message}`, 10000);
    } finally {
      setScraping(false);
    }
  }

  const pendingCount = statusCounts.pending ?? queue.filter(q => q.status === 'pending').length;
  const generatingCount = statusCounts.generating ?? queue.filter(q => q.status === 'generating').length;
  const readyCount = statusCounts.ready ?? queue.filter(q => q.status === 'ready').length;

  return (
    <div className="flex min-h-screen w-full overflow-hidden bg-zinc-950 font-sans text-zinc-100">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 max-w-lg rounded-md border border-amber-500 bg-amber-950 px-4 py-2 text-sm text-amber-200 shadow-lg">
          {toast}
        </div>
      )}

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
                  <div className="mt-1 text-2xl font-medium">${statusCounts.budget_used_today || 0} <span className="text-sm text-zinc-500">/ ${dailyBudget}</span></div>
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
                  {queue.length === 0 && (
                    <div className="py-8 text-center text-sm text-zinc-500">No stories yet. Configure scrape settings and sources.</div>
                  )}
                  {queue.map((q) => (
                    <div key={q.id} className="flex items-center gap-3 py-2.5 text-sm">
                      <ScoreBadge score={q.score} aiScore={q.ai_curation?.viral_score} isTopPick={q.ai_curation?.is_top_pick} />
                      <span className="flex-1 truncate text-zinc-300">{q.title}</span>
                      <CategoryBadge category={q.ai_curation?.category} />
                      <span className="text-xs text-zinc-500">{fmtWhen(q.spotted_at)}</span>
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

              <Card className="p-4">
                <div className="mb-3 text-sm font-medium text-zinc-200">API Keys</div>
                <p className="mb-3 text-xs text-zinc-500">Keys are encrypted at rest. Reddit requires a script app at reddit.com/prefs/apps.</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 flex items-center gap-1 text-xs text-zinc-500">
                      <KeyRound className="h-3 w-3" /> Reddit Client ID
                    </label>
                    <input
                      type="password"
                      value={scraperKeys.reddit_client_id || ''}
                      onChange={(e) => setScraperKeys(prev => ({ ...prev, reddit_client_id: e.target.value }))}
                      placeholder="From Reddit app settings"
                      className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono text-sm text-zinc-200"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center gap-1 text-xs text-zinc-500">
                      <KeyRound className="h-3 w-3" /> Reddit Client Secret
                    </label>
                    <input
                      type="password"
                      value={scraperKeys.reddit_client_secret || ''}
                      onChange={(e) => setScraperKeys(prev => ({ ...prev, reddit_client_secret: e.target.value }))}
                      placeholder="From Reddit app settings"
                      className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono text-sm text-zinc-200"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center gap-1 text-xs text-zinc-500">
                      <KeyRound className="h-3 w-3" /> NewsAPI key
                    </label>
                    <input
                      type="password"
                      value={scraperKeys.newsapi || ''}
                      onChange={(e) => setScraperKeys(prev => ({ ...prev, newsapi: e.target.value }))}
                      placeholder="API key for newsapi.org"
                      className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono text-sm text-zinc-200"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center gap-1 text-xs text-zinc-500">
                      <KeyRound className="h-3 w-3" /> YouTube API key
                    </label>
                    <input
                      type="password"
                      value={scraperKeys.youtube || ''}
                      onChange={(e) => setScraperKeys(prev => ({ ...prev, youtube: e.target.value }))}
                      placeholder="Google Cloud API key"
                      className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono text-sm text-zinc-200"
                    />
                  </div>
                </div>
              </Card>

              <div className="flex gap-3">
                <button onClick={saveScrapeSettings} disabled={loading} className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-400">
                  {loading ? 'Saving...' : 'Save scrape settings'}
                </button>
                <button onClick={triggerScrape} disabled={scraping} className="rounded-md border border-amber-500 px-4 py-2 text-sm text-amber-400 hover:bg-amber-950 disabled:opacity-50">
                  {scraping ? (
                    <><RefreshCw className="inline h-3.5 w-3.5 mr-1 animate-spin" /> Scraping...</>
                  ) : (
                    <><RefreshCw className="inline h-3.5 w-3.5 mr-1" /> Run now</>
                  )}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'providers' && (
            <div className="flex flex-col gap-6">
              <div>
                <h1 className="text-lg font-medium text-zinc-100">AI providers</h1>
                <p className="text-sm text-zinc-500">Connect the APIs used for prompt generation, video creation, and voiceover. Keys are encrypted at rest.</p>
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
                <button onClick={saveProviders} disabled={loading} className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-400">
                  {loading ? 'Saving...' : 'Save providers'}
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
                  "Connect" redirects into that platform's OAuth flow. Tokens are stored encrypted on the server.
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
                <div className="flex items-center gap-2">
                  <button onClick={async () => {
                    if (!confirm('Delete ALL stories?')) return;
                    try {
                      const res = await fetchJSON(`${API}/queue`, { method: 'DELETE' });
                      showToast(`${res.deleted} stories cleared`);
                      loadQueue();
                      loadStatus();
                    } catch (e) { showToast(`Error: ${e.message}`); }
                  }} className="flex items-center gap-1.5 rounded-md border border-rose-800 px-3 py-1.5 text-sm text-rose-400 hover:bg-rose-950">
                    <Trash2 className="h-3.5 w-3.5" /> Clear all
                  </button>
                  <button onClick={async () => {
                    setLoading(true);
                    try {
                      const res = await fetchJSON(`${API}/queue/curate`, { method: 'POST' });
                      showToast(`AI analyzed ${res.analyzed} stories. Top picks: ${res.top_pick_ids.length}`);
                      loadQueue();
                    } catch (e) { showToast(`Curate failed: ${e.message}`); }
                    finally { setLoading(false); }
                  }} disabled={loading} className="flex items-center gap-1.5 rounded-md border border-purple-800 px-3 py-1.5 text-sm text-purple-400 hover:bg-purple-950">
                    <Sparkles className="h-3.5 w-3.5" /> {loading ? 'Analyzing...' : 'Analyze'}
                  </button>
                  <button onClick={refreshQueue} className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-900">
                    <RefreshCw className="h-3.5 w-3.5" /> Refresh
                  </button>
                </div>
              </div>

              <Card>
                <div className="flex flex-col divide-y divide-zinc-800">
                  {queue.length === 0 && (
                    <div className="py-12 text-center text-sm text-zinc-500">No stories in queue. Run a scrape first.</div>
                  )}
                  {queue.map((q) => (
                    <div key={q.id} className="flex items-center gap-4 p-4">
                      <ScoreBadge score={q.score} aiScore={q.ai_curation?.viral_score} isTopPick={q.ai_curation?.is_top_pick} />
                      <div className="flex-1">
                        <div className="text-sm text-zinc-200">{q.title}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                          <span className="font-mono">{q.source}</span>
                          <span>·</span>
                          <span>window: {q.time_window}</span>
                          <span>·</span>
                          <span>{fmtWhen(q.spotted_at)}</span>
                        </div>
                      </div>
                      <CategoryBadge category={q.ai_curation?.category} />
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
                      {q.status === 'failed' && (
                        <button onClick={async () => {
                          try {
                            await fetchJSON(`${API}/queue/${q.id}/retry`, { method: 'POST' });
                            showToast('Retrying...');
                            setTimeout(refreshQueue, 2000);
                          } catch (e) { showToast(`Error: ${e.message}`); }
                        }} className="flex items-center gap-1 rounded-md border border-amber-500 px-3 py-1.5 text-xs text-amber-400 hover:bg-amber-950">
                          <RefreshCw className="h-3.5 w-3.5" /> Retry
                        </button>
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
                    {schedule.length === 0 && (
                      <tr><td colSpan={4} className="px-4 py-12 text-center text-zinc-500">No scheduled posts yet.</td></tr>
                    )}
                    {schedule.map((s) => (
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
