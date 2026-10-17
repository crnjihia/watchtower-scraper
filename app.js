/**
 * Watchtower Scraper - Interactive Telemetry & Documentation Engine
 */

document.addEventListener("DOMContentLoaded", () => {
  initMetricsCounter();
  initEventFeed();
  initTerminalSimulator();
  initDocsTabs();
  initCopyButtons();
});

// 1. Metric Counter Animation
function initMetricsCounter() {
  const counters = document.querySelectorAll(".metric-value[data-target]");
  counters.forEach((counter) => {
    const target = +counter.getAttribute("data-target");
    const suffix = counter.getAttribute("data-suffix") || "";
    const isFloat = counter.getAttribute("data-float") === "true";
    let count = 0;
    const speed = target / 60;

    const update = () => {
      count += speed;
      if (count < target) {
        counter.textContent = isFloat
          ? count.toFixed(2) + suffix
          : Math.floor(count).toLocaleString() + suffix;
        requestAnimationFrame(update);
      } else {
        counter.textContent = isFloat
          ? target.toFixed(2) + suffix
          : target.toLocaleString() + suffix;
      }
    };
    update();
  });
}

// 2. Sample Change Events Data
const SAMPLE_EVENTS = [
  {
    type: "NEW",
    source: "brightermonday",
    title: "Lead Cloud Infrastructure Architect",
    company: "Equity Bank Kenya",
    location: "Nairobi, Kenya",
    salary: "KES 350,000 - 450,000",
    url: "https://www.brightermonday.co.ke/listings/lead-cloud-architect-9921",
    timestamp: "1 min ago",
    raw: {
      source: "brightermonday",
      external_id: "lead-cloud-architect-9921",
      title: "Lead Cloud Infrastructure Architect",
      company: "Equity Bank Kenya",
      location: "Nairobi, Kenya",
      job_type: "Full Time",
      salary: "KES 350,000 - 450,000",
      content_hash: "8f4d92a10c73e1bb425c28fa4891b93f182c1b29",
      scraped_at: "2026-10-17T01:45:10Z"
    }
  },
  {
    type: "PRICE_DROP",
    source: "jumia",
    title: "Apple iPhone 13 Pro Max - 512GB Blue",
    old_price: "KES 154,999",
    new_price: "KES 142,500",
    url: "https://www.jumia.co.ke/p/phone-iphone-13-pro-max-512gb-blue-5555555",
    timestamp: "3 mins ago",
    raw: {
      type: "PRICE_DROP",
      source: "jumia",
      external_id: "phone-iphone-13-pro-max-512gb-blue-5555555",
      field: "price",
      old: 154999.0,
      new: 142500.0,
      url: "https://www.jumia.co.ke/p/phone-iphone-13-pro-max-512gb-blue-5555555"
    }
  },
  {
    type: "NEW",
    source: "fuzu",
    title: "Senior Python Backend Engineer (FastAPI/Django)",
    company: "Safaricom PLC",
    location: "Westlands, Nairobi",
    salary: "Competitive",
    url: "https://www.fuzu.com/kenya/jobs/senior-python-engineer-safaricom",
    timestamp: "7 mins ago",
    raw: {
      source: "fuzu",
      external_id: "senior-python-engineer-safaricom",
      title: "Senior Python Backend Engineer (FastAPI/Django)",
      company: "Safaricom PLC",
      location: "Westlands, Nairobi",
      job_type: "Full Time",
      content_hash: "2e9a710bca78891efc6198f2445831ba92410a8c"
    }
  },
  {
    type: "UPDATED",
    source: "myjobmag",
    title: "Data Analyst & Business Intelligence Specialist",
    company: "KCB Group",
    change: "salary updated from 'Undisclosed' to 'KES 180,000 - 240,000'",
    url: "https://www.myjobmag.co.ke/job/data-analyst-kcb-group",
    timestamp: "12 mins ago",
    raw: {
      type: "UPDATED",
      source: "myjobmag",
      external_id: "data-analyst-kcb-group",
      field: "salary",
      old: "Undisclosed",
      new: "KES 180,000 - 240,000"
    }
  },
  {
    type: "PRICE_DROP",
    source: "kilimall",
    title: "Sony 55-inch 4K HDR Google Smart TV",
    old_price: "KES 78,000",
    new_price: "KES 69,999",
    url: "https://www.kilimall.co.ke/p/sony-55-inch-smart-tv-222222",
    timestamp: "18 mins ago",
    raw: {
      type: "PRICE_DROP",
      source: "kilimall",
      external_id: "sony-55-inch-smart-tv-222222",
      field: "price",
      old: 78000.0,
      new: 69999.0
    }
  },
  {
    type: "NEW",
    source: "brighter_monday",
    title: "DevOps & SRE Specialist (Kubernetes/Terraform)",
    company: "Cellulant Corporation",
    location: "Nairobi",
    salary: "KES 280,000 - 360,000",
    url: "https://www.brightermonday.co.ke/listings/devops-sre-specialist-4412",
    timestamp: "24 mins ago",
    raw: {
      source: "brighter_monday",
      external_id: "devops-sre-specialist-4412",
      title: "DevOps & SRE Specialist (Kubernetes/Terraform)",
      company: "Cellulant Corporation"
    }
  }
];

function initEventFeed() {
  const feedContainer = document.getElementById("eventFeedStream");
  const filterBtns = document.querySelectorAll(".feed-btn");
  let currentFilter = "all";

  function renderFeed() {
    feedContainer.innerHTML = "";
    const filtered = SAMPLE_EVENTS.filter((ev) => {
      if (currentFilter === "all") return true;
      if (currentFilter === "jobs")
        return ["brightermonday", "fuzu", "myjobmag", "brighter_monday"].includes(ev.source);
      if (currentFilter === "products")
        return ["jumia", "kilimall"].includes(ev.source);
      if (currentFilter === "price_drop")
        return ev.type === "PRICE_DROP";
      return true;
    });

    filtered.forEach((ev) => {
      const item = document.createElement("div");
      item.className = "feed-item";
      item.onclick = () => openEventModal(ev);

      let badgeHtml = "";
      if (ev.type === "NEW") {
        badgeHtml = `<span class="ev-badge badge-new">🆕 NEW</span>`;
      } else if (ev.type === "PRICE_DROP") {
        badgeHtml = `<span class="ev-badge badge-price-drop">📉 DROP</span>`;
      } else {
        badgeHtml = `<span class="ev-badge badge-updated">✏️ UPDATE</span>`;
      }

      let metaHtml = "";
      if (ev.type === "PRICE_DROP") {
        metaHtml = `<span style="text-decoration: line-through; color: var(--text-faint);">${ev.old_price}</span> → <strong style="color: #fbbf24;">${ev.new_price}</strong>`;
      } else if (ev.company) {
        metaHtml = `at <strong>${ev.company}</strong> ${ev.location ? `• ${ev.location}` : ""} ${ev.salary ? `• <span style="color:#34d399;">${ev.salary}</span>` : ""}`;
      } else if (ev.change) {
        metaHtml = `<span>${ev.change}</span>`;
      }

      item.innerHTML = `
        ${badgeHtml}
        <div class="feed-body">
          <div class="feed-title">
            <span>[${ev.source.toUpperCase()}] ${ev.title}</span>
            <span class="feed-time">${ev.timestamp}</span>
          </div>
          <div class="feed-meta">${metaHtml}</div>
        </div>
      `;
      feedContainer.appendChild(item);
    });
  }

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.getAttribute("data-filter");
      renderFeed();
    });
  });

  renderFeed();
}

function openEventModal(eventObj) {
  const modal = document.getElementById("eventModal");
  const modalTitle = document.getElementById("modalEventTitle");
  const modalBody = document.getElementById("modalEventJson");

  modalTitle.textContent = `[${eventObj.source.toUpperCase()}] ${eventObj.title}`;
  modalBody.textContent = JSON.stringify(eventObj.raw, null, 2);
  modal.classList.add("active");
}

function closeEventModal() {
  const modal = document.getElementById("eventModal");
  modal.classList.remove("active");
}

// 3. Interactive Terminal Simulator
const TERMINAL_OUTPUTS = {
  status: `<span class="t-prompt">$</span> <span class="t-cmd">python run.py status</span>
============================================================
  WATCHTOWER SCRAPER - SYSTEM STATUS
============================================================
Total Stored Items     : <span class="t-success">14,820</span> listings
Total History Diffs    : <span class="t-accent">1,432</span> state transitions
Total Alerts Dispatched: <span class="t-warn">384</span> telegram / email
------------------------------------------------------------
Items by Source:
  * brightermonday     : <span class="t-success">5,240</span> listings (HEALTHY)
  * fuzu               : <span class="t-success">3,890</span> listings (HEALTHY)
  * myjobmag           : <span class="t-success">4,120</span> listings (HEALTHY)
  * jumia              : <span class="t-success">  820</span> watchlist products (MONITORED)
  * kilimall           : <span class="t-success">  750</span> watchlist products (MONITORED)
------------------------------------------------------------
Most Recently Updated Items:
  [brightermonday] Lead Cloud Infrastructure Architect -> Safaricom
  [jumia] Apple iPhone 13 Pro Max (KES 142,500.00) -> In Stock
  [fuzu] Staff Distributed Systems Engineer -> Cellulant
============================================================`,

  crawl: `<span class="t-prompt">$</span> <span class="t-cmd">python run.py crawl jobs --limit 5</span>
Starting crawl for: brighter_monday, fuzu, myjobmag (limit=5)

--- Running spider: brighter_monday ---
[scrapy.core.engine] INFO: Spider opened (brighter_monday)
[scrapy.extensions.throttle] INFO: AutoThrottle active (delay=2.0s, target=1.0)
[watchtower.pipelines.normalize] INFO: normalized_item (url: https://...)
[watchtower.pipelines.change_detect] INFO: change_detected: NEW_LISTING external_id='lead-cloud-architect-9921'
[watchtower.pipelines.persist] INFO: item_persisted_and_snapshotted (id=14821)
[scrapy.core.engine] INFO: Closing spider (closespider_itemcount)
[scrapy.statscollectors] INFO: Dumping Scrapy stats:
    'item_scraped_count': 5,
    'change_events': 3,
    'finish_reason': 'closespider_itemcount'

[OK] Job boards crawl sequence completed successfully.`,

  alerts: `<span class="t-prompt">$</span> <span class="t-cmd">python run.py alerts --dry-run</span>
Fetching change events from past 24 hours...
Discovered <span class="t-accent">42 change events</span> (41 new jobs, 1 price drop).

<span class="t-warn">[DRY RUN PREVIEW]</span>
1. 🆕 *[BrighterMonday]* [Lead Cloud Infrastructure Architect](https://...) at *Equity Bank Kenya*
2. 📉 *[Jumia]* [Apple iPhone 13 Pro Max - 512GB](https://...): Price dropped *154999.0 → 142500.0*
3. 🆕 *[Fuzu]* [Senior Python Backend Engineer](https://...) at *Safaricom PLC*
4. ✏️ *[MyJobMag]* [Data Analyst](https://...): *salary* changed *Undisclosed → KES 180,000 - 240,000*
5. 🆕 *[BrighterMonday]* [DevOps & SRE Specialist](https://...) at *Cellulant Corporation*
... and 37 more events.

<span class="t-success">Email Digest Subject:</span> Watchtower Daily: 41 new jobs, 1 price drop
<span class="t-success">Email Digest Summary:</span> 41 new jobs, 1 price drop detected across Kenyan portals.
[DRY-RUN] No messages dispatched to Telegram or SendGrid.`,

  docker: `<span class="t-prompt">$</span> <span class="t-cmd">docker run --rm -v $(pwd)/data:/app/data ghcr.io/crnjihia/watchtower-scraper:latest status</span>
Unable to find image 'ghcr.io/crnjihia/watchtower-scraper:latest' locally
latest: Pulling from crnjihia/watchtower-scraper
Digest: sha256:7198cfb5e408544d6a9a08e1bf9a584020a
Status: Downloaded newer image for ghcr.io/crnjihia/watchtower-scraper:latest

============================================================
  WATCHTOWER SCRAPER - SYSTEM STATUS
============================================================
Total Stored Items     : 14,820 listings
Total History Diffs    : 1,432 transitions
Status                 : CONTAINER OPERATIONAL (Non-root user UID 1000)
============================================================`,

  demo: `<span class="t-prompt">$</span> <span class="t-cmd">python run.py demo</span>
============================================================
  WATCHTOWER SCRAPER - LIVE DEMONSTRATION
============================================================

1. Crawling sample listings from 'myjobmag'...
[scrapy.core.engine] INFO: Spider opened (my_job_mag)
[watchtower.pipelines.persist] INFO: Validated and stored item: 'Database Administrator'
[scrapy.core.engine] INFO: Closing spider (closespider_itemcount=2)

2. Database status after crawl:
Total Stored Items : 2 listings
Items by Source:
  * myjobmag : 2 listings

3. Generating and previewing alert digest:
[DRY RUN PREVIEW]
1. 🆕 *[MyJobMag]* [Database Administrator](https://...) at *KCB Group*

<span class="t-success">[OK] Demonstration complete! All components verified operational.</span>`
};

function initTerminalSimulator() {
  const terminalBody = document.getElementById("terminalOutput");
  const tabs = document.querySelectorAll(".t-tab");

  function switchTab(cmdKey) {
    tabs.forEach((t) => t.classList.remove("active"));
    const activeTab = document.querySelector(`.t-tab[data-cmd="${cmdKey}"]`);
    if (activeTab) activeTab.classList.add("active");
    terminalBody.innerHTML = TERMINAL_OUTPUTS[cmdKey] || "";
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const cmdKey = tab.getAttribute("data-cmd");
      switchTab(cmdKey);
    });
  });

  switchTab("status");
}

// 4. Documentation Tabs
function initDocsTabs() {
  const navItems = document.querySelectorAll(".docs-nav-item");
  const panes = document.querySelectorAll(".doc-pane");

  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      navItems.forEach((i) => i.classList.remove("active"));
      panes.forEach((p) => p.classList.remove("active"));

      item.classList.add("active");
      const targetId = item.getAttribute("data-target");
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
      }
    });
  });
}

// 5. Copy Buttons
function initCopyButtons() {
  document.querySelectorAll(".copy-btn, .code-pill").forEach((el) => {
    el.addEventListener("click", (e) => {
      const textToCopy = el.getAttribute("data-copy") || el.innerText.trim();
      navigator.clipboard.writeText(textToCopy).then(() => {
        const originalText = el.innerText;
        el.innerText = "Copied!";
        setTimeout(() => {
          el.innerText = originalText;
        }, 1800);
      });
    });
  });
}
