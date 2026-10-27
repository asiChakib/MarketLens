(() => {
  const datasetSelect = document.querySelector("#dataset-select");
  const symbolInput = document.querySelector("#symbol-search");
  const symbolOptions = document.querySelector("#symbol-options");
  const addSymbolButton = document.querySelector("#add-symbol-button");
  const selectedStocksElement = document.querySelector("#selected-stocks");
  const dashboard = document.querySelector("#dashboard-content");
  const metricsPanels = document.querySelector("#metrics-panels");
  const errorPanel = document.querySelector("#error-panel");
  const errorTitle = document.querySelector("#error-title");
  const errorMessage = document.querySelector("#error-message");
  const retryButton = document.querySelector("#retry-button");
  const chartLoading = document.querySelector("#chart-loading");
  const chartEmpty = document.querySelector("#chart-empty");
  const chartWrap = document.querySelector("#chart-wrap");
  const chart = document.querySelector("#price-chart");
  const chartSymbol = document.querySelector("#chart-symbol");
  const dateRange = document.querySelector("#date-range");
  const periodButtons = [...document.querySelectorAll("[data-period]")];
  const customRangeForm = document.querySelector("#custom-range");
  const rangeStart = document.querySelector("#range-start");
  const rangeEnd = document.querySelector("#range-end");
  const rangeError = document.querySelector("#range-error");

  const metricDefinitions = [
    { key: "total_return", label: "Total return", help: "Overall price change across the selected date window.", kind: "percent" },
    { key: "mean_daily_return", label: "Mean daily return", help: "Arithmetic average of daily returns in the selected window.", kind: "percent" },
    { key: "annualized_volatility", label: "Annualized volatility", help: "Annualized sample standard deviation of daily returns.", kind: "percent" },
    { key: "maximum_drawdown", label: "Maximum drawdown", help: "Largest peak-to-trough decline in the selected window.", kind: "percent" },
    { key: "observations", label: "Observations", help: "Daily returns used by return-based metrics.", kind: "count" },
  ];
  const stockColors = ["#16876c", "#5278c8"];

  function stockColor(index) {
    if (index < stockColors.length) return stockColors[index];
    return `hsl(${(index * 137.508) % 360} 54% 43%)`;
  }

  let activeController = null;
  let requestVersion = 0;
  let retryAction = loadDatasets;
  let activeDataset = null;
  let availableSymbols = [];
  let selectedSymbols = [];
  let historiesBySymbol = {};
  let selectedPeriod = "all";
  let customStart = "";
  let customEnd = "";

  function clearDashboard() {
    metricsPanels.replaceChildren();
    chart.replaceChildren();
    chartSymbol.textContent = "";
    dateRange.textContent = "Historical observations";
  }

  function setLoading(isLoading) {
    dashboard.setAttribute("aria-busy", String(isLoading));
    chartLoading.hidden = !isLoading;
    chartWrap.hidden = true;
    chartEmpty.hidden = true;
  }

  function showError(title, message, retry) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    retryAction = retry;
    errorPanel.hidden = false;
  }

  function hideError() {
    errorPanel.hidden = true;
  }

  async function requestJson(url, signal) {
    let response;
    try {
      response = await fetch(url, { headers: { Accept: "application/json" }, signal });
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new Error("MarketLens could not be reached. Check that the local server is running, then retry.");
    }
    if (!response.ok) {
      const messages = {
        404: "This dataset or symbol is no longer available.",
        422: "There is not enough price history in this date window to calculate all metrics.",
        500: "MarketLens could not read the configured price data. Check the CSV and retry.",
      };
      throw new Error(messages[response.status] || "MarketLens returned an unexpected response. Please retry.");
    }
    try {
      return await response.json();
    } catch {
      throw new Error("MarketLens returned data in an unexpected format. Please retry.");
    }
  }

  function apiUrl(path, parameters = {}) {
    const query = new URLSearchParams();
    if (activeDataset) query.set("dataset", activeDataset);
    Object.entries(parameters).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const suffix = query.toString();
    return suffix ? `${path}?${suffix}` : path;
  }

  function updateAddButton() {
    const candidate = symbolInput.value.trim().toUpperCase();
    addSymbolButton.disabled = !availableSymbols.includes(candidate) || selectedSymbols.includes(candidate);
  }

  function renderSelectedStocks() {
    selectedStocksElement.replaceChildren();
    selectedSymbols.forEach((symbol, index) => {
      const chip = document.createElement("span");
      chip.className = "stock-chip";
      chip.style.setProperty("--stock-color", stockColor(index));
      chip.append(document.createTextNode(symbol));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remove ${symbol} from the comparison`);
      remove.addEventListener("click", () => removeSymbol(symbol));
      chip.append(remove);
      selectedStocksElement.append(chip);
    });
    updateAddButton();
  }

  async function loadDatasets() {
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const version = ++requestVersion;
    datasetSelect.disabled = true;
    datasetSelect.replaceChildren(new Option("Loading datasets…", ""));
    symbolInput.disabled = true;
    symbolInput.value = "";
    symbolOptions.replaceChildren();
    availableSymbols = [];
    selectedSymbols = [];
    historiesBySymbol = {};
    clearDashboard();
    renderSelectedStocks();
    hideError();
    setLoading(true);

    try {
      const data = await requestJson("/datasets", controller.signal);
      if (version !== requestVersion) return;
      if (!data || !Array.isArray(data.datasets) || typeof data.default_dataset !== "string") {
        throw new Error("MarketLens returned an unexpected dataset list. Please retry.");
      }
      const validDatasets = data.datasets.filter(
        (item) => item && typeof item.id === "string" && typeof item.name === "string",
      );
      if (validDatasets.length !== data.datasets.length || validDatasets.length === 0) {
        throw new Error("No datasets are available in the data folder.");
      }
      datasetSelect.replaceChildren();
      validDatasets.forEach((item) => datasetSelect.add(new Option(item.name, item.id)));
      activeDataset = validDatasets.some((item) => item.id === data.default_dataset)
        ? data.default_dataset
        : validDatasets[0].id;
      datasetSelect.value = activeDataset;
      datasetSelect.disabled = false;
      await loadSymbols();
    } catch (error) {
      if (error.name === "AbortError" || version !== requestVersion) return;
      setLoading(false);
      chartLoading.hidden = true;
      chartEmpty.hidden = false;
      chartEmpty.textContent = "Choose a dataset to view its metrics.";
      showError("Couldn’t load available datasets", error.message, loadDatasets);
    }
  }

  async function loadSymbols() {
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const version = ++requestVersion;
    symbolInput.disabled = true;
    symbolInput.value = "";
    symbolInput.placeholder = "Loading symbols…";
    symbolOptions.replaceChildren();
    availableSymbols = [];
    selectedSymbols = [];
    historiesBySymbol = {};
    renderSelectedStocks();
    clearDashboard();
    hideError();
    setLoading(true);

    try {
      const data = await requestJson(apiUrl("/symbols"), controller.signal);
      if (version !== requestVersion) return;
      if (!data || !Array.isArray(data.symbols) || !data.symbols.every((symbol) => typeof symbol === "string")) {
        throw new Error("MarketLens returned an unexpected symbol list. Please retry.");
      }
      if (data.symbols.length === 0) {
        symbolInput.placeholder = "No symbols available";
        setLoading(false);
        chartLoading.hidden = true;
        chartEmpty.hidden = false;
        showError("No market data yet", "The selected dataset does not contain any symbols.", loadSymbols);
        return;
      }
      availableSymbols = data.symbols;
      data.symbols.forEach((symbol) => symbolOptions.append(new Option(symbol, symbol)));
      symbolInput.placeholder = "Search symbols…";
      symbolInput.disabled = false;
      selectedSymbols = [data.symbols[0]];
      renderSelectedStocks();
      await loadSelectedStocks();
    } catch (error) {
      if (error.name === "AbortError" || version !== requestVersion) return;
      setLoading(false);
      chartLoading.hidden = true;
      chartEmpty.hidden = false;
      chartEmpty.textContent = "Metrics will appear after data is available.";
      showError("Couldn’t load available symbols", error.message, loadSymbols);
    }
  }

  async function loadSelectedStocks() {
    if (selectedSymbols.length === 0) {
      if (activeController) activeController.abort();
      activeController = null;
      requestVersion += 1;
      historiesBySymbol = {};
      clearDashboard();
      setLoading(false);
      chartEmpty.hidden = false;
      chartEmpty.textContent = "Add a stock to display its metrics.";
      renderSelectedStocks();
      return;
    }
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const version = ++requestVersion;
    const symbols = [...selectedSymbols];
    historiesBySymbol = {};
    clearDashboard();
    hideError();
    renderSelectedStocks();
    chartSymbol.textContent = symbols.join(" · ");
    setLoading(true);

    try {
      const histories = await Promise.all(symbols.map(async (symbol) => {
        const data = await requestJson(apiUrl(`/prices/${encodeURIComponent(symbol)}`), controller.signal);
        if (!data || data.symbol !== symbol || !Array.isArray(data.prices)) {
          throw new Error(`MarketLens returned unexpected price data for ${symbol}.`);
        }
        if (data.prices.some((point) => !point || typeof point.date !== "string" || !Number.isFinite(point.close))) {
          throw new Error(`MarketLens returned an invalid price history for ${symbol}.`);
        }
        return [symbol, data.prices];
      }));
      if (version !== requestVersion) return;
      historiesBySymbol = Object.fromEntries(histories);
      updateCustomRangeBounds();
      await loadMetricsForWindow(controller, version);
    } catch (error) {
      if (error.name === "AbortError" || version !== requestVersion) return;
      clearDashboard();
      setLoading(false);
      chartLoading.hidden = true;
      chartEmpty.hidden = true;
      showError("Couldn’t load selected stocks", error.message, loadSelectedStocks);
    }
  }

  function allDates() {
    return Object.values(historiesBySymbol).flatMap((prices) => prices.map((point) => point.date)).sort();
  }

  function updateCustomRangeBounds() {
    const dates = allDates();
    if (dates.length === 0) return;
    const first = dates[0];
    const last = dates[dates.length - 1];
    rangeStart.min = first;
    rangeStart.max = last;
    rangeEnd.min = first;
    rangeEnd.max = last;
    customStart ||= first;
    customEnd ||= last;
    rangeStart.value = customStart;
    rangeEnd.value = customEnd;
  }

  function subtractMonths(isoDate, months) {
    const date = new Date(`${isoDate}T00:00:00Z`);
    const day = date.getUTCDate();
    date.setUTCDate(1);
    date.setUTCMonth(date.getUTCMonth() - months);
    const daysInTargetMonth = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
    date.setUTCDate(Math.min(day, daysInTargetMonth));
    return date.toISOString().slice(0, 10);
  }

  function dateWindow() {
    const dates = allDates();
    if (dates.length === 0) return null;
    const earliest = dates[0];
    const latest = dates[dates.length - 1];
    if (selectedPeriod === "all") return { start: null, end: null, label: `${earliest} — ${latest}` };

    let start;
    let end = latest;
    if (selectedPeriod === "custom") {
      start = customStart;
      end = customEnd;
      if (!start || !end) return null;
      if (start < earliest || end > latest || start > end) {
        rangeError.textContent = "Choose dates within the available history.";
        return null;
      }
    } else {
      const months = { "1m": 1, "3m": 3, "6m": 6, "1y": 12, "3y": 36 }[selectedPeriod];
      start = subtractMonths(latest, months);
      if (start < earliest) start = earliest;
    }
    return { start, end, label: `${start} — ${end}` };
  }

  async function loadMetricsForWindow(controller, version) {
    const window = dateWindow();
    if (!window) {
      setLoading(false);
      chartLoading.hidden = true;
      chartEmpty.hidden = false;
      chartEmpty.textContent = "Choose valid dates to compare metrics.";
      return;
    }
    const parameters = window.start && window.end ? { start: window.start, end: window.end } : {};
    dateRange.textContent = window.label;
    chartSymbol.textContent = selectedSymbols.join(" · ");
    try {
      const results = await Promise.all(selectedSymbols.map(async (symbol) => {
        const metrics = await requestJson(
          apiUrl(`/analytics/${encodeURIComponent(symbol)}`, parameters),
          controller.signal,
        );
        if (!metrics || metrics.symbol !== symbol) {
          throw new Error(`MarketLens returned unexpected metrics for ${symbol}.`);
        }
        return { symbol, metrics };
      }));
      if (version !== requestVersion) return;
      renderMetrics(results);
      const hasPrices = drawPriceChart(window);
      setLoading(false);
      chartLoading.hidden = true;
      chartEmpty.hidden = hasPrices;
      chartEmpty.textContent = "No price observations fall within this date window.";
      chartWrap.hidden = !hasPrices;
      hideError();
    } catch (error) {
      if (error.name === "AbortError" || version !== requestVersion) return;
      metricsPanels.replaceChildren();
      chart.replaceChildren();
      setLoading(false);
      chartLoading.hidden = true;
      chartWrap.hidden = true;
      chartEmpty.hidden = true;
      showError("Couldn’t calculate this comparison", error.message, () => refreshMetrics());
    }
  }

  function refreshMetrics() {
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const version = ++requestVersion;
    hideError();
    metricsPanels.replaceChildren();
    chart.replaceChildren();
    setLoading(true);
    loadMetricsForWindow(controller, version);
  }

  function formatMetric(definition, value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "Unavailable";
    if (definition.kind === "count") return new Intl.NumberFormat().format(value);
    return new Intl.NumberFormat(undefined, {
      style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2,
    }).format(value);
  }

  function renderMetrics(results) {
    metricsPanels.replaceChildren();
    results.forEach(({ symbol, metrics }, stockIndex) => {
      const section = document.createElement("section");
      section.className = "stock-metrics";
      section.setAttribute("aria-label", `${symbol} performance and risk metrics`);
      const heading = document.createElement("div");
      heading.className = "stock-metrics-header";
      heading.style.setProperty("--stock-color", stockColor(stockIndex));
      const dot = document.createElement("span");
      dot.className = "stock-color-dot";
      dot.setAttribute("aria-hidden", "true");
      const title = document.createElement("h2");
      title.textContent = symbol;
      heading.append(dot, title);

      const grid = document.createElement("div");
      grid.className = "metrics-grid";
      metricDefinitions.forEach((definition, metricIndex) => {
        const card = document.createElement("article");
        card.className = `metric-card${metricIndex === 0 ? " metric-primary" : ""}`;
        card.style.setProperty("--stock-color", stockColor(stockIndex));
        const metricHeading = document.createElement("div");
        metricHeading.className = "metric-heading";
        const label = document.createElement("h3");
        label.textContent = definition.label;
        const info = document.createElement("span");
        info.className = "info-mark";
        info.title = definition.help;
        info.setAttribute("aria-label", definition.help);
        info.textContent = "i";
        metricHeading.append(label, info);

        const value = document.createElement("p");
        value.className = "metric-value";
        value.textContent = formatMetric(definition, metrics[definition.key]);
        if (typeof metrics[definition.key] === "number" && metrics[definition.key] < 0) value.classList.add("negative");
        const foot = document.createElement("p");
        foot.className = "metric-foot";
        foot.textContent = definition.key === "observations" ? "Daily returns included" : "Selected date window";
        card.append(metricHeading, value, foot);
        grid.append(card);
      });
      section.append(heading, grid);
      metricsPanels.append(section);
    });
  }

  function svgElement(tag, attributes = {}, text = null) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, String(value)));
    if (text !== null) element.textContent = text;
    return element;
  }

  function drawPriceChart(window) {
    chart.replaceChildren();
    const series = selectedSymbols.map((symbol) => ({
      symbol,
      prices: (historiesBySymbol[symbol] || [])
        .filter((point) => (!window.start || point.date >= window.start) && (!window.end || point.date <= window.end))
        .sort((left, right) => left.date.localeCompare(right.date)),
    })).filter((item) => item.prices.length > 0);
    if (series.length === 0) return false;

    const width = 900;
    const height = 360;
    const margin = { top: 22, right: 28, bottom: 48, left: 82 };
    const plotHeight = height - margin.top - margin.bottom;
    const plotWidth = width - margin.left - margin.right;
    const allPoints = series.flatMap((item) => item.prices);
    const timestamps = allPoints.map((point) => Date.parse(`${point.date}T00:00:00Z`));
    const firstTimestamp = Math.min(...timestamps);
    const lastTimestamp = Math.max(...timestamps);
    const allCloses = allPoints.map((point) => point.close);
    const minClose = Math.min(...allCloses);
    const maxClose = Math.max(...allCloses);
    const spread = maxClose - minClose;
    const padding = spread === 0 ? Math.max(maxClose * 0.04, 1) : spread * 0.12;
    const low = minClose - padding;
    const high = maxClose + padding;
    const xFor = (point) => margin.left + (lastTimestamp === firstTimestamp
      ? plotWidth / 2
      : (Date.parse(`${point.date}T00:00:00Z`) - firstTimestamp) * plotWidth / (lastTimestamp - firstTimestamp));
    const yFor = (close) => margin.top + (high - close) * plotHeight / (high - low);
    const priceFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
    const dateFormat = new Intl.DateTimeFormat(undefined, { month: "short", year: "numeric", timeZone: "UTC" });

    for (let tick = 0; tick <= 4; tick += 1) {
      const fraction = tick / 4;
      const yPosition = margin.top + fraction * plotHeight;
      const price = high - fraction * (high - low);
      chart.append(svgElement("line", {
        x1: margin.left, y1: yPosition, x2: width - margin.right, y2: yPosition, class: "chart-grid",
      }));
      chart.append(svgElement("text", {
        x: margin.left - 12, y: yPosition + 4, "text-anchor": "end", class: "chart-axis-label",
      }, priceFormat.format(price)));
    }

    for (let tick = 0; tick <= 4; tick += 1) {
      const fraction = tick / 4;
      const timestamp = firstTimestamp + fraction * (lastTimestamp - firstTimestamp);
      const xPosition = margin.left + fraction * plotWidth;
      chart.append(svgElement("line", {
        x1: xPosition, y1: margin.top, x2: xPosition, y2: height - margin.bottom, class: "chart-grid chart-grid-vertical",
      }));
      chart.append(svgElement("text", {
        x: xPosition, y: height - 13, "text-anchor": fraction === 0 ? "start" : fraction === 1 ? "end" : "middle",
        class: "chart-axis-label",
      }, dateFormat.format(new Date(timestamp))));
    }

    chart.append(svgElement("text", {
      x: margin.left, y: 12, class: "chart-axis-label chart-unit-label",
    }, "Closing price"));

    series.forEach(({ symbol, prices }, stockIndex) => {
      if (prices.length > 1) {
        const points = prices.map((point) => `${xFor(point)},${yFor(point.close)}`).join(" ");
        const line = svgElement("polyline", { points, class: "chart-line" });
        line.style.stroke = stockColor(stockIndex);
        chart.append(line);
      }
      prices.forEach((point) => {
        const label = `${symbol} · ${point.date} · ${priceFormat.format(point.close)}`;
        const circle = svgElement("circle", {
          cx: xFor(point), cy: yFor(point.close), r: prices.length > 45 ? 2.5 : 5,
          class: "chart-point", tabindex: "0", role: "img",
          "aria-label": label,
        });
        circle.style.stroke = stockColor(stockIndex);
        circle.append(svgElement("title", {}, label));
        chart.append(circle);
      });
    });
    return true;
  }

  function choosePeriod(period) {
    selectedPeriod = period;
    rangeError.textContent = "";
    if (period === "custom") {
      updateCustomRangeBounds();
      customRangeForm.hidden = false;
      return;
    }
    customRangeForm.hidden = true;
    periodButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.period === period)));
    refreshMetrics();
  }

  function applyCustomPeriod(event) {
    event.preventDefault();
    if (!rangeStart.value || !rangeEnd.value) {
      rangeError.textContent = "Choose both dates.";
      return;
    }
    if (rangeStart.value > rangeEnd.value) {
      rangeError.textContent = "The start date must be before the end date.";
      return;
    }
    customStart = rangeStart.value;
    customEnd = rangeEnd.value;
    rangeError.textContent = "";
    periodButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.period === "custom")));
    refreshMetrics();
  }

  function addSymbol() {
    const symbol = symbolInput.value.trim().toUpperCase();
    if (!availableSymbols.includes(symbol)) return;
    if (selectedSymbols.includes(symbol)) return;
    selectedSymbols.push(symbol);
    symbolInput.value = "";
    renderSelectedStocks();
    loadSelectedStocks();
  }

  function removeSymbol(symbol) {
    selectedSymbols = selectedSymbols.filter((item) => item !== symbol);
    renderSelectedStocks();
    loadSelectedStocks();
  }

  function handleSearchInput() {
    updateAddButton();
  }

  datasetSelect.addEventListener("change", () => {
    activeDataset = datasetSelect.value;
    selectedPeriod = "all";
    customStart = "";
    customEnd = "";
    customRangeForm.hidden = true;
    periodButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.period === "all")));
    loadSymbols();
  });
  symbolInput.addEventListener("input", handleSearchInput);
  symbolInput.addEventListener("change", handleSearchInput);
  addSymbolButton.addEventListener("click", addSymbol);
  periodButtons.forEach((button) => button.addEventListener("click", () => choosePeriod(button.dataset.period)));
  customRangeForm.addEventListener("submit", applyCustomPeriod);
  retryButton.addEventListener("click", () => retryAction());
  loadDatasets();
})();
