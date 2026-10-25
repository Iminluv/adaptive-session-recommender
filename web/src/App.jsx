import React, { useState, useEffect, useCallback } from 'react';

const FALLBACK_PRODUCTS = [
  { product_id: 1001, category_code: 'electronics.smartphone', brand: 'samsung', average_price: 499.0, popularity_score: 1.0 },
  { product_id: 1002, category_code: 'electronics.smartphone', brand: 'apple', average_price: 799.0, popularity_score: 0.8 },
  { product_id: 1003, category_code: 'electronics.audio', brand: 'sony', average_price: 149.0, popularity_score: 0.6 },
  { product_id: 1004, category_code: 'electronics.audio', brand: 'bose', average_price: 299.0, popularity_score: 0.5 },
];

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).substring(2, 10);
}

export default function App() {
  const [userId, setUserId] = useState('user-1');
  const [sessionId, setSessionId] = useState(generateSessionId());
  const [products, setProducts] = useState(FALLBACK_PRODUCTS);
  const [recommendations, setRecommendations] = useState([]);
  const [isFallback, setIsFallback] = useState(false);
  const [eventsLog, setEventsLog] = useState([]);
  const [health, setHealth] = useState({ status: 'checking', storage: 'Connecting...' });
  const [loadingRecs, setLoadingRecs] = useState(false);

  // Health check
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

  // Fetch catalog products
  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch('/products?limit=20');
      if (res.ok) {
        const data = await res.json();
        if (data.products && data.products.length > 0) {
          setProducts(data.products);
        }
      }
    } catch (e) {
      console.warn('Failed to fetch /products, keeping fallback items', e);
    }
  }, []);

  // Fetch recommendations for current user and session
  const fetchRecommendations = useCallback(async (uid, sid) => {
    setLoadingRecs(true);
    try {
      const query = sid ? `?user_session=${encodeURIComponent(sid)}&limit=5` : '?limit=5';
      const res = await fetch(`/recommendations/${encodeURIComponent(uid)}${query}`);
      if (res.ok) {
        const data = await res.json();
        setRecommendations(data.recommendations || []);
        setIsFallback(Boolean(data.fallback));
      } else {
        setRecommendations([]);
      }
    } catch (e) {
      console.warn('Failed to fetch recommendations', e);
      setRecommendations([]);
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
    fetchRecommendations(userId, sessionId);
  }, [userId, sessionId, fetchRecommendations]);

  // Send canonical event to POST /events
  const emitEvent = async (eventType, product) => {
    const eventId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : 'evt-' + Date.now();
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
    try {
      const res = await fetch('/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      statusLabel = res.ok ? '202 Accepted' : `${res.status} Error`;
    } catch {
      statusLabel = 'Network Failed';
    }

    setEventsLog(prev => [
      {
        id: eventId,
        eventType,
        productId: product.product_id,
        category: product.category_code,
        brand: product.brand,
        time: new Date().toLocaleTimeString(),
        status: statusLabel,
      },
      ...prev.slice(0, 19),
    ]);

    // Re-fetch recommendations to reflect immediate updates
    setTimeout(() => {
      fetchRecommendations(userId, sessionId);
    }, 400);
  };

  // Quick simulation helper
  const simulateInterest = async (categoryKeyword) => {
    const matched = products.filter(p => (p.category_code || '').includes(categoryKeyword));
    const target = matched.length > 0 ? matched[0] : products[0];
    if (!target) return;

    for (let i = 0; i < 2; i++) {
      await emitEvent('view', target);
    }
    await emitEvent('cart', target);
  };

  const getReasonClass = (reason) => {
    if (reason === 'adaptive_session_intent') return 'adaptive';
    if (reason === 'long_term_preference') return 'als';
    return 'popular';
  };

  return (
    <div className="container">
      <header>
        <div className="header-title">
          <h1>⚡ Adaptive Session-Aware Recommender</h1>
          <p>Real-time Kafka + Spark Streaming + Cassandra + FastAPI Re-ranking Demo</p>
        </div>
        <div>
          <span className={`badge-status ${health.status}`}>
            ● {health.status === 'healthy' ? 'Serving Healthy' : health.status}
          </span>
        </div>
      </header>

      {/* Persona and Session Control Bar */}
      <section className="session-bar">
        <div className="session-group">
          <label htmlFor="user-select">User Persona:</label>
          <select
            id="user-select"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          >
            <option value="user-1">user-1 (Existing user with ALS candidates)</option>
            <option value="user-2">user-2 (Existing user)</option>
            <option value="user-3">user-3 (Existing user)</option>
            <option value="anonymous">anonymous (Cold start / Fallback)</option>
          </select>
        </div>

        <div className="session-group">
          <label htmlFor="session-input">Session ID:</label>
          <input
            id="session-input"
            type="text"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            style={{ width: '130px' }}
          />
          <button onClick={() => setSessionId(generateSessionId())} title="Start fresh session">
            New Session
          </button>
        </div>

        <div className="session-group" style={{ marginLeft: 'auto' }}>
          <button className="primary" onClick={() => fetchRecommendations(userId, sessionId)}>
            🔄 Refresh Shelf
          </button>
        </div>
      </section>

      {/* Main Grid: Catalog vs Recommended */}
      <div className="main-layout">
        {/* Left Panel: Catalog */}
        <section className="section-panel">
          <div className="panel-header">
            <h2>🛍️ Product Catalog</h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="accent" onClick={() => simulateInterest('audio')}>
                Simulate Audio Focus
              </button>
              <button className="accent" onClick={() => simulateInterest('smartphone')}>
                Simulate Phone Focus
              </button>
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px' }}>
            Click items to emit real-time canonical events to Kafka.
          </p>
          <div className="product-grid">
            {products.map((p) => (
              <div key={p.product_id} className="product-card">
                <div>
                  <div className="product-brand">{p.brand || 'Generic'}</div>
                  <div className="product-name">Product #{p.product_id}</div>
                  <div className="product-category">{p.category_code || 'appliances'}</div>
                </div>
                <div>
                  <div className="product-price">
                    ${(p.average_price || 99.99).toFixed(2)}
                  </div>
                  <div className="card-actions">
                    <button onClick={() => emitEvent('view', p)}>
                      👁️ View
                    </button>
                    <button className="primary" onClick={() => emitEvent('cart', p)}>
                      🛒 Cart
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right Panel: Adaptive Recommendations */}
        <section className="section-panel">
          <div className="panel-header">
            <h2>🎯 Recommended For You</h2>
            {isFallback && (
              <span className="badge-status warning">Cold-start Fallback</span>
            )}
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px' }}>
            Top candidates ranked with ALS (60%) + Session Intent (25%) + Popularity (10%).
          </p>

          {loadingRecs ? (
            <p style={{ color: 'var(--text-muted)' }}>Loading recommendations...</p>
          ) : recommendations.length === 0 ? (
            <p style={{ color: 'var(--text-muted)' }}>No recommendations found.</p>
          ) : (
            <div className="recommendations-list">
              {recommendations.map((rec) => {
                const reasonClass = getReasonClass(rec.reason);
                return (
                  <div key={rec.product_id} className={`rec-card ${reasonClass}`}>
                    <div className="rec-header">
                      <div>
                        <span className="rec-rank">#{rec.rank} </span>
                        <span className="rec-title">
                          Product #{rec.product_id} ({rec.brand || 'brand'})
                        </span>
                      </div>
                      <span className={`reason-tag ${reasonClass}`}>
                        {rec.reason.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Category: {rec.category_code || 'unknown'} | Price: ${(rec.price || 0).toFixed(2)}
                    </div>
                    <div className="score-breakdown">
                      <div className="score-item">
                        <strong>Score:</strong> {rec.score.toFixed(3)}
                      </div>
                      {rec.score_components && (
                        <>
                          <div className="score-item">
                            ALS: {rec.score_components.als.toFixed(2)}
                          </div>
                          <div className="score-item">
                            Intent: {rec.score_components.intent.toFixed(2)}
                          </div>
                          <div className="score-item">
                            Pop: {rec.score_components.popularity.toFixed(2)}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* Activity Clickstream Feed */}
      <section className="activity-feed">
        <div className="feed-title">
          <span>📡 Live Session Clickstream Log</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {eventsLog.length} events emitted in this session
          </span>
        </div>
        {eventsLog.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No interactions yet. Click "View" or "Cart" on any product to emit events.
          </p>
        ) : (
          <div className="feed-items">
            {eventsLog.map((ev) => (
              <div key={ev.id} className="feed-item">
                <span>
                  <strong className={`event-type ${ev.eventType}`}>{ev.eventType.toUpperCase()}</strong>
                  {' '}→ Product #{ev.productId} ({ev.category})
                </span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {ev.status} • {ev.time}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
