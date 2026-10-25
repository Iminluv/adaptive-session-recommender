import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP);

const FALLBACK_PRODUCTS = [
  { product_id: 1001, category_code: 'electronics.smartphone', brand: 'samsung', average_price: 499.0, popularity_score: 1.0 },
  { product_id: 1002, category_code: 'electronics.smartphone', brand: 'apple', average_price: 799.0, popularity_score: 0.8 },
  { product_id: 1003, category_code: 'electronics.audio', brand: 'sony', average_price: 149.0, popularity_score: 0.6 },
  { product_id: 1004, category_code: 'electronics.audio', brand: 'bose', average_price: 299.0, popularity_score: 0.5 },
];

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).substring(2, 10);
}

function formatCategory(category = '') {
  const value = category.split('.').filter(Boolean).pop() || 'unknown';
  return value.replace(/[-_]/g, ' ');
}

function titleCase(value = '') {
  return value.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function productLabel(product) {
  const category = titleCase(formatCategory(product.category_code));
  return `${product.brand ? titleCase(product.brand) : 'Generic'} ${category} #${product.product_id}`;
}

function reasonLabel(reason = '') {
  return reason.replace(/_/g, ' ') || 'ranked candidate';
}

function getReasonClass(reason) {
  if (reason === 'adaptive_session_intent') return 'adaptive';
  if (reason === 'long_term_preference') return 'als';
  return 'popular';
}

function StatusPill({ status, children }) {
  return <span className={`status-pill ${status}`}>{children}</span>;
}

function DemoHeader({ health }) {
  return (
    <header className="hero-header" data-hero>
      <div className="hero-copy">
        <div className="eyebrow"><span className="eyebrow-dot" /> Live recommendation lab</div>
        <h1>Adaptive recommendations, live.</h1>
        <p>Watch long-term preference and current session intent work together in real time.</p>
      </div>
      <div className="service-health">
        <span className={`health-orb ${health.status}`} />
        <div>
          <span className="health-label">Serving status</span>
          <strong>{health.status === 'healthy' ? 'Healthy' : titleCase(health.status)}</strong>
        </div>
      </div>
    </header>
  );
}

function SessionControls({ userId, setUserId, sessionId, setSessionId, onRefresh }) {
  return (
    <section className="session-bar" data-controls>
      <div className="session-context">
        <span className="section-kicker">Live session</span>
        <span className="session-id">{sessionId}</span>
      </div>
      <div className="control-field">
        <label htmlFor="user-select">Persona</label>
        <select id="user-select" value={userId} onChange={(event) => setUserId(event.target.value)}>
          <option value="user-1">user-1 · Existing profile</option>
          <option value="user-2">user-2 · Existing profile</option>
          <option value="user-3">user-3 · Existing profile</option>
          <option value="anonymous">anonymous · Cold start</option>
        </select>
      </div>
      <div className="control-field session-input-field">
        <label htmlFor="session-input">Session ID</label>
        <input id="session-input" type="text" value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
      </div>
      <button className="button-secondary" onClick={() => setSessionId(generateSessionId())} title="Start fresh session">
        New session
      </button>
      <button className="button-primary control-refresh" onClick={onRefresh}>
        Refresh shelf <span aria-hidden="true">↗</span>
      </button>
    </section>
  );
}

function IntentSummary({ intent, eventCount }) {
  const hasIntent = Boolean(intent.category);
  const signalWidth = hasIntent ? Math.min(96, 28 + eventCount * 18) : 0;

  return (
    <section className={`intent-summary ${hasIntent ? 'has-intent' : ''}`} data-intent-summary>
      <div className="intent-heading">
        <div>
          <span className="section-kicker">Current session intent</span>
          <h2>{hasIntent ? `Exploring ${titleCase(formatCategory(intent.category))}` : 'No active intent yet'}</h2>
        </div>
        <div className="intent-count"><strong>{eventCount}</strong><span>events<br />this session</span></div>
      </div>
      <div className="intent-meter" aria-label={hasIntent ? `${signalWidth}% session intent strength` : 'No session intent'}>
        <span className="intent-meter-fill" style={{ width: `${signalWidth}%` }} />
      </div>
      <div className="intent-footer">
        <span>{hasIntent ? 'Streaming signal detected' : 'Interact with a product to create a signal'}</span>
        <span className="intent-source">{hasIntent ? 'Short-term behavior' : 'Waiting for first event'}</span>
      </div>
    </section>
  );
}

function WhyThisChanged() {
  return (
    <div className="why-changed">
      <div>
        <span className="section-kicker">Ranking recipe</span>
        <h3>Why this changed</h3>
      </div>
      <div className="recipe-bars" aria-label="Recommendation score weighting">
        <div className="recipe-row"><span><i className="recipe-dot als" /> Long-term preference</span><strong>60%</strong><span className="recipe-bar"><i style={{ width: '60%' }} /></span></div>
        <div className="recipe-row"><span><i className="recipe-dot adaptive" /> Session intent</span><strong>25%</strong><span className="recipe-bar"><i style={{ width: '25%' }} /></span></div>
        <div className="recipe-row"><span><i className="recipe-dot popular" /> Popularity</span><strong>10%</strong><span className="recipe-bar"><i style={{ width: '10%' }} /></span></div>
      </div>
    </div>
  );
}

function RecommendationShelf({ recommendations, loading, isFallback, changedRecIds, error }) {
  return (
    <section className="panel recommendation-panel" data-recommendations>
      <div className="panel-heading">
        <div>
          <span className="section-kicker">Adaptive output</span>
          <h2>Recommended for you</h2>
        </div>
        {isFallback && <StatusPill status="warning">Cold-start fallback</StatusPill>}
      </div>
      <p className="panel-intro">The shelf combines a durable user profile with what is happening right now.</p>

      <WhyThisChanged />

      {error && <div className="inline-state error-state"><strong>Recommendation service unavailable.</strong><span>{error}</span></div>}
      {loading ? (
        <div className="inline-state loading-state"><span className="loading-orb" /><span>Re-ranking the shelf from the latest session signal…</span></div>
      ) : recommendations.length === 0 ? (
        <div className="inline-state empty-state"><strong>No recommendations yet.</strong><span>Choose a persona or interact with a product to start the demo.</span></div>
      ) : (
        <div className="recommendations-list">
          {recommendations.map((rec) => {
            const reasonClass = getReasonClass(rec.reason);
            const score = Number(rec.score || 0);
            return (
              <article key={rec.product_id} className={`recommendation-card ${reasonClass} ${changedRecIds.includes(rec.product_id) ? 'is-changed' : ''}`}>
                <div className="rec-rank">0{rec.rank || 1}</div>
                <div className="rec-main">
                  <div className="rec-topline">
                    <span className="rec-brand">{titleCase(rec.brand || 'Generic')}</span>
                    <span className={`reason-tag ${reasonClass}`}>{reasonLabel(rec.reason)}</span>
                  </div>
                  <h3>{productLabel({ ...rec, category_code: rec.category_code || 'product' })}</h3>
                  <div className="rec-meta"><span>{titleCase(formatCategory(rec.category_code))}</span><span>·</span><span>${Number(rec.price || 0).toFixed(2)}</span></div>
                  <div className="score-line"><span>Match score</span><strong>{score.toFixed(3)}</strong><span className="score-track"><i style={{ width: `${Math.min(100, score * 100)}%` }} /></span></div>
                </div>
                {changedRecIds.includes(rec.product_id) && <span className="changed-label">Updated</span>}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function CatalogPanel({ products, onEvent, onScenario, busy }) {
  return (
    <section className="panel catalog-panel" data-catalog>
      <div className="panel-heading panel-heading-stack">
        <div>
          <span className="section-kicker">Try the system</span>
          <h2>Explore products</h2>
        </div>
        <p className="panel-intro">Every explicit interaction becomes a live event and can shift the shelf.</p>
      </div>
      <div className="scenario-actions">
        <button className="scenario-button" onClick={() => onScenario('smartphone')} disabled={busy}><span>⌁</span> Explore smartphones</button>
        <button className="scenario-button" onClick={() => onScenario('audio')} disabled={busy}><span>◌</span> Explore audio</button>
      </div>
      <div className="product-grid">
        {products.map((product) => (
          <article key={product.product_id} className="product-card">
            <div className="product-visual" aria-hidden="true"><span>{titleCase(formatCategory(product.category_code)).slice(0, 2)}</span></div>
            <div className="product-info">
              <span className="product-brand">{titleCase(product.brand || 'Generic')}</span>
              <h3>{productLabel(product)}</h3>
              <span className="product-category">{titleCase(formatCategory(product.category_code))}</span>
            </div>
            <div className="product-footer">
              <strong>${Number(product.average_price || 99.99).toFixed(2)}</strong>
              <div className="card-actions">
                <button onClick={() => onEvent('view', product)} disabled={busy}>View</button>
                <button className="button-primary" onClick={() => onEvent('cart', product)} disabled={busy}>Add to cart</button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ActivityTimeline({ events, status }) {
  return (
    <section className="activity-panel" data-activity>
      <div className="panel-heading">
        <div>
          <span className="section-kicker">Evidence trail</span>
          <h2>Live session timeline</h2>
        </div>
        <span className="event-counter">{events.length} events emitted</span>
      </div>
      {status && <div className={`event-status ${status.type}`}><span className="status-pulse" />{status.message}</div>}
      {events.length === 0 ? (
        <div className="timeline-empty">Your live event trail will appear here as you explore.</div>
      ) : (
        <div className="timeline-list">
          {events.map((event, index) => (
            <div key={event.id} className={`timeline-item ${index === 0 ? 'is-new' : ''}`}>
              <span className={`timeline-icon ${event.eventType}`}>{event.eventType === 'cart' ? '+' : '↗'}</span>
              <div className="timeline-copy"><strong>{titleCase(event.eventType)}</strong><span>{titleCase(event.brand || 'Generic')} · {titleCase(formatCategory(event.category))}</span></div>
              <div className="timeline-meta"><span className={`event-result ${event.status.includes('Accepted') ? 'accepted' : 'failed'}`}>{event.status}</span><time>{event.time}</time></div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function App() {
  const [userId, setUserId] = useState('user-1');
  const [sessionId, setSessionId] = useState(generateSessionId());
  const [products, setProducts] = useState(FALLBACK_PRODUCTS);
  const [recommendations, setRecommendations] = useState([]);
  const [changedRecIds, setChangedRecIds] = useState([]);
  const [isFallback, setIsFallback] = useState(false);
  const [eventsLog, setEventsLog] = useState([]);
  const [health, setHealth] = useState({ status: 'checking', storage: 'Connecting...' });
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recommendationError, setRecommendationError] = useState('');
  const [eventStatus, setEventStatus] = useState(null);
  const rootRef = useRef(null);
  const recommendationsRef = useRef([]);

  const intent = useMemo(() => {
    const counts = eventsLog.reduce((accumulator, event) => {
      if (event.category) accumulator[event.category] = (accumulator[event.category] || 0) + 1;
      return accumulator;
    }, {});
    const category = Object.entries(counts).sort(([, first], [, second]) => second - first)[0]?.[0] || '';
    return { category };
  }, [eventsLog]);

  useGSAP(() => {
    const intro = gsap.timeline({ defaults: { duration: 0.55, ease: 'power2.out' } });
    intro.from('[data-hero]', { autoAlpha: 0, y: 18 })
      .from('[data-controls]', { autoAlpha: 0, y: 14 }, '-=0.28')
      .from('[data-intent-summary]', { autoAlpha: 0, y: 14 }, '-=0.28')
      .from('[data-recommendations], [data-catalog], [data-activity]', { autoAlpha: 0, y: 14, stagger: 0.08 }, '-=0.24');

    const media = gsap.matchMedia();
    media.add('(prefers-reduced-motion: reduce)', () => {
      intro.progress(1).pause();
    });
    return () => media.revert();
  }, { scope: rootRef });

  useGSAP(() => {
    gsap.from('.timeline-item.is-new', { autoAlpha: 0, x: -16, duration: 0.35, ease: 'power2.out' });
    gsap.from('.recommendation-card.is-changed', { autoAlpha: 0, y: 10, duration: 0.45, stagger: 0.07, ease: 'power2.out' });
    gsap.fromTo('.intent-meter-fill', { scaleX: 0.85 }, { scaleX: 1, duration: 0.55, transformOrigin: 'left center', ease: 'power2.out' });
  }, { scope: rootRef, dependencies: [eventsLog.length, changedRecIds.join(','), loadingRecs], revertOnUpdate: true });

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch('/health');
      if (res.ok) {
        const data = await res.json();
        setHealth({ status: 'healthy', storage: data.storage || 'Cassandra & API Online' });
      } else {
        setHealth({ status: 'warning', storage: 'API reporting degraded storage' });
      }
    } catch {
      setHealth({ status: 'warning', storage: 'API offline or unreachable' });
    }
  }, []);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch('/products?limit=20');
      if (res.ok) {
        const data = await res.json();
        if (data.products && data.products.length > 0) setProducts(data.products);
      }
    } catch (error) {
      console.warn('Failed to fetch /products, keeping fallback items', error);
    }
  }, []);

  const fetchRecommendations = useCallback(async (uid, sid) => {
    setLoadingRecs(true);
    setRecommendationError('');
    try {
      const query = sid ? `?user_session=${encodeURIComponent(sid)}&limit=5` : '?limit=5';
      const res = await fetch(`/recommendations/${encodeURIComponent(uid)}${query}`);
      if (!res.ok) {
        setRecommendations([]);
        setRecommendationError(`Request returned ${res.status}.`);
        return;
      }
      const data = await res.json();
      const nextRecommendations = data.recommendations || [];
      const previousIds = new Set(recommendationsRef.current.map((recommendation) => recommendation.product_id));
      recommendationsRef.current = nextRecommendations;
      setChangedRecIds(nextRecommendations.filter((recommendation) => !previousIds.has(recommendation.product_id)).map((recommendation) => recommendation.product_id));
      setRecommendations(nextRecommendations);
      setIsFallback(Boolean(data.fallback));
    } catch {
      setRecommendations([]);
      setRecommendationError('Check that the API and serving layer are running.');
    } finally {
      setLoadingRecs(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    fetchProducts();
    const timer = setInterval(checkHealth, 30000);
    return () => clearInterval(timer);
  }, [checkHealth, fetchProducts]);

  useEffect(() => {
    setEventsLog([]);
    setEventStatus(null);
    fetchRecommendations(userId, sessionId);
  }, [userId, sessionId, fetchRecommendations]);

  const emitEvent = async (eventType, product) => {
    const eventId = globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `evt-${Date.now()}`;
    const nowIso = new Date().toISOString();
    const payload = {
      schema_version: 1,
      event_id: eventId,
      event_time: nowIso,
      ingest_time: nowIso,
      event_type: eventType,
      product_id: product.product_id,
      category_id: 2053013555631882655,
      category_code: product.category_code || 'appliances.personal.massager',
      brand: product.brand || 'unknown',
      price: product.average_price || 100.0,
      user_id: userId,
      user_session: sessionId,
      event_source: 'browser',
    };

    let statusLabel = 'Sent';
    let statusType = 'failed';
    try {
      const res = await fetch('/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      statusLabel = res.ok ? '202 Accepted' : `${res.status} Error`;
      statusType = res.ok ? 'accepted' : 'failed';
    } catch {
      statusLabel = 'Network Failed';
    }

    setEventStatus({
      type: statusType,
      message: statusType === 'accepted' ? `${titleCase(eventType)} accepted · refreshing the recommendation shelf` : `${titleCase(eventType)} failed · recommendation shelf not updated`,
    });
    setEventsLog((previous) => [{
      id: eventId,
      eventType,
      productId: product.product_id,
      category: product.category_code,
      brand: product.brand,
      time: new Date().toLocaleTimeString(),
      status: statusLabel,
    }, ...previous.slice(0, 19)]);

    if (statusType === 'accepted') await fetchRecommendations(userId, sessionId);
  };

  const simulateInterest = async (categoryKeyword) => {
    const matched = products.filter((product) => (product.category_code || '').includes(categoryKeyword));
    const target = matched.length > 0 ? matched[0] : products[0];
    if (!target) return;
    await emitEvent('view', target);
    await emitEvent('view', target);
    await emitEvent('cart', target);
  };

  return (
    <main className="app-shell" ref={rootRef}>
      <div className="container">
        <DemoHeader health={health} />
        <SessionControls userId={userId} setUserId={setUserId} sessionId={sessionId} setSessionId={setSessionId} onRefresh={() => fetchRecommendations(userId, sessionId)} />
        <IntentSummary intent={intent} eventCount={eventsLog.length} />

        <div className="main-layout">
          <RecommendationShelf recommendations={recommendations} loading={loadingRecs} isFallback={isFallback} changedRecIds={changedRecIds} error={recommendationError} />
          <CatalogPanel products={products} onEvent={emitEvent} onScenario={simulateInterest} busy={loadingRecs} />
        </div>

        <ActivityTimeline events={eventsLog} status={eventStatus} />
        <footer className="system-footnote"><span className="footnote-line" />Live browser events feed the session-aware ranking path. Product IDs remain the shared join key.</footer>
      </div>
    </main>
  );
}
