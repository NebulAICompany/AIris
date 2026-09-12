(function () {
  const BALANCE_FILE_REGEX = /\.(xlsx|xls|pdf|docx|doc|txt|jpg|jpeg|png|gif|bmp|tiff|tif)$/i;

  class BalanceCalendarApp {
    constructor() {
      this.api = window.apiService || new APIService();
      this.timeframeSelect = document.getElementById("balance-timeframe");
      this.refreshButton = document.getElementById("balance-refresh");
      this.processButton = document.getElementById("balance-process-btn");
      this.feedbackBox = document.getElementById("balance-process-feedback");
      this.loadingIndicator = document.getElementById("balance-loading");
      this.heatmapContainer = document.getElementById("balance-heatmap");
      this.summaryContainer = document.getElementById("balance-summary");
      this.legendContainer = document.getElementById("balance-legend");
      this.detailPanel = document.getElementById("balance-detail");
      this.uploadButton = document.getElementById("balance-upload-btn");
      this.uploadInput = document.getElementById("balance-file-input");
      this.latestData = null;
      this.selectedDate = null;
      this.currentFileName = null;
      this.isDataLoaded = false;
      this.init();
    }

    t(key, args = {}) {
      const service = window.languageService;
      if (!service?.translations) {
        return key;
      }

      const lang = service.currentLanguage || "en";
      const fallbackLang = "en";
      const resolve = (targetLang) => {
        const segments = key.split(".");
        let value = service.translations?.[targetLang];
        for (const segment of segments) {
          if (value?.[segment] === undefined) {
            return undefined;
          }
          value = value[segment];
        }
        return value;
      };

      let raw = resolve(lang);
      if (raw === undefined) {
        raw = resolve(fallbackLang);
      }

      if (typeof raw === "string") {
        return raw.replace(/\{(\w+)\}/g, (_, token) => {
          return Object.prototype.hasOwnProperty.call(args, token)
            ? args[token]
            : `{${token}}`;
        });
      }
      return raw !== undefined ? raw : key;
    }

    getWeekdayLabels() {
      const service = window.languageService;
      const lang = service?.currentLanguage || "en";
      const fallback = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
      const labels = service?.translations?.[lang]?.balanceCalendar?.weekdays;
      return Array.isArray(labels) && labels.length === 7 ? labels : fallback;
    }

    init() {
      this.bindEvents();
      this.renderEmptyState();
    }

    bindEvents() {
      if (this.timeframeSelect) {
        this.timeframeSelect.addEventListener("change", () =>
          this.refreshCalendar()
        );
      }

      if (this.refreshButton) {
        this.refreshButton.addEventListener("click", () =>
          this.refreshCalendar()
        );
      }

      if (this.processButton) {
        this.processButton.addEventListener("click", () =>
          this.handleProcess()
        );
      }

      if (this.uploadButton && this.uploadInput) {
        this.uploadButton.addEventListener("click", () =>
          this.uploadInput.click()
        );
        this.uploadInput.addEventListener("change", (event) =>
          this.handleUploadSelection(event)
        );
      }
    }

    async refreshCalendar() {
      const months = parseInt(this.timeframeSelect?.value || "3", 10);

      try {
        this.setLoading(true);
        const result = await this.api.getBalanceCalendar(months);

        if (!result.success || !result.data) {
          throw new Error(result.error || "Unable to fetch calendar data");
        }

        this.latestData = result.data;
        this.renderSummary(result.data);
        this.renderLegend(result.data.maxAbsoluteNet || 0);
        this.renderHeatmap(result.data);
        this.isDataLoaded = true;

        // Also refresh the category charts
        if (window.categoryPieChart) {
          await window.categoryPieChart.refresh();
        }
        if (window.categoryColumnChart) {
          await window.categoryColumnChart.refresh();
        }
      } catch (error) {
        logger.error(`Failed to load calendar: ${error}`, "BALANCE");
        this.heatmapContainer.innerHTML = this.renderErrorState(
          error?.message || "Unable to load calendar"
        );
        const retryBtn = this.heatmapContainer.querySelector(
          "#balance-retry-btn"
        );
        if (retryBtn) {
          retryBtn.addEventListener("click", () => this.refreshCalendar());
        }
      } finally {
        this.setLoading(false);
      }
    }

    setLoading(isLoading) {
      if (this.loadingIndicator) {
        this.loadingIndicator.hidden = !isLoading;
      }
      if (this.refreshButton) {
        this.refreshButton.disabled = isLoading;
      }
      if (this.processButton) {
        this.processButton.disabled = isLoading;
      }
    }

    renderEmptyState() {
      if (!this.heatmapContainer) return;
      this.heatmapContainer.innerHTML = `
        <div class="balance-empty">
          <i class="fas fa-calendar-alt" style="font-size: 3rem; color: #94a3b8; margin-bottom: 1rem;"></i>
          <h3 style="color: #64748b; margin-bottom: 0.5rem;">${this.t("balanceCalendar.noDataLoaded") || "No Data Loaded"}</h3>
          <p style="color: #94a3b8; margin-bottom: 1.5rem;">${this.t("balanceCalendar.clickRefreshToLoad") || "Click the refresh button to load balance data"}</p>
        </div>
      `;
      if (this.summaryContainer) {
        this.summaryContainer.innerHTML = "";
      }
    }

    renderErrorState(message) {
      return `
        <div class="balance-empty">
          <i class="fas fa-exclamation-circle"></i>
          <p>${Utils.escapeHtml(message)}</p>
          <button class="btn btn-secondary" id="balance-retry-btn">
            <i class="fas fa-rotate"></i>
            Retry
          </button>
        </div>
      `;
    }

    renderSummary(data) {
      if (!this.summaryContainer) return;

      const totals = data.days.reduce(
        (acc, day) => {
          acc.income += day.income;
          acc.expense += day.expense;
          return acc;
        },
        { income: 0, expense: 0 }
      );

      const finalNet = data.days.length
        ? data.days[data.days.length - 1].net
        : 0;

      const rangeText = `${this.formatDateLabel(
        data.startDate
      )} - ${this.formatDateLabel(data.endDate)}`;

      const latestText = data.latestActivity
        ? this.t("balanceCalendar.latestActivity", {
            date: this.formatDateLabel(data.latestActivity),
          })
        : this.t("balanceCalendar.noActivity");

      this.summaryContainer.innerHTML = `
        <div class="summary-range">
          <div class="summary-label">${this.t("balanceCalendar.summaryPeriodLabel")}</div>
          <div class="summary-value">${rangeText}</div>
          <div class="summary-subtext">${latestText}</div>
        </div>
        <div class="summary-metric positive">
          <span class="label">${this.t("balanceCalendar.totalIncome")}</span>
          <span class="value">${this.formatCurrency(totals.income)}</span>
        </div>
        <div class="summary-metric negative">
          <span class="label">${this.t("balanceCalendar.totalExpense")}</span>
          <span class="value">${this.formatCurrency(totals.expense)}</span>
        </div>
        <div class="summary-metric neutral">
          <span class="label">${this.t("balanceCalendar.netChange")}</span>
          <span class="value">${this.formatCurrency(finalNet)}</span>
        </div>
      `;
    }

    renderLegend(maxAbsoluteNet) {
      if (!this.legendContainer) return;

      this.legendContainer.innerHTML = "";
      this.legendContainer.hidden = true;
    }

    renderHeatmap(data) {
      if (!this.heatmapContainer) return;

      const start = new Date(data.startDate);
      const end = new Date(data.endDate);
      const dayMap = new Map();
      data.days.forEach((day) => dayMap.set(day.date, day));
      const maxAbs = data.maxAbsoluteNet || 0;

      const months = [];
      const monthCursor = new Date(start.getFullYear(), start.getMonth(), 1);
      const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);

      while (monthCursor <= endMonth) {
        months.push({
          year: monthCursor.getFullYear(),
          month: monthCursor.getMonth(),
        });
        monthCursor.setMonth(monthCursor.getMonth() + 1);
      }

      // Calculate optimal grid layout based on number of months
      const totalMonths = months.length;
      let columnsPerRow;
      let scale;
      
      if (totalMonths <= 3) {
        columnsPerRow = totalMonths;
        scale = 'normal';
      } else if (totalMonths <= 6) {
        columnsPerRow = 3;
        scale = 'medium';
      } else if (totalMonths <= 9) {
        columnsPerRow = 3;
        scale = 'small';
      } else {
        columnsPerRow = 4;
        scale = 'tiny';
      }

      const rows = [];
      for (let i = 0; i < months.length; i += columnsPerRow) {
        rows.push(months.slice(i, i + columnsPerRow));
      }

      const layoutHtml = rows
        .map((row) => {
          const monthHtml = row
            .map((info) => this.renderMonthBlock(info, dayMap, maxAbs))
            .join("");

          return `<div class="balance-month-row" style="grid-template-columns: repeat(${row.length}, 1fr);">${monthHtml}</div>`;
        })
        .join("");

      this.heatmapContainer.innerHTML = `
        <div class="balance-month-layout" data-scale="${scale}" data-columns="${columnsPerRow}">
          ${layoutHtml}
        </div>
      `;

      this.attachDayHandlers();
      this.attachMonthHandlers();
    }

    renderMonthBlock(monthInfo, dayMap, maxAbs) {
      const { year, month } = monthInfo;
      const monthDate = new Date(year, month, 1);
      const label = monthDate.toLocaleDateString(undefined, {
        month: "short",
        year: "numeric",
      });

      const weekdayLabels = this.getWeekdayLabels()
        .map((weekday) => `<div class="balance-weekday">${weekday}</div>`)
        .join("");

      const firstDay = new Date(year, month, 1);
      const daysInMonth = new Date(year, month + 1, 0).getDate();
      const leadingBlanks = (firstDay.getDay() + 6) % 7; // Monday-first calendar

      const cells = [];
      for (let i = 0; i < leadingBlanks; i++) {
        cells.push(this.renderDayCell(null, null, maxAbs, true));
      }

      for (let day = 1; day <= daysInMonth; day++) {
        const dateKey = `${year}-${String(month + 1).padStart(2, "0")}-${String(
          day
        ).padStart(2, "0")}`;
        const entry = dayMap.get(dateKey);
        cells.push(this.renderDayCell(dateKey, entry, maxAbs));
      }

      while (cells.length % 7 !== 0) {
        cells.push(this.renderDayCell(null, null, maxAbs, true));
      }

      return `
        <div class="balance-month" data-month="${year}-${String(month + 1).padStart(
        2,
        "0"
      )}" style="cursor: pointer;" title="Click to expand">
          <div class="balance-month-header">${label}</div>
          <div class="balance-month-weekdays">${weekdayLabels}</div>
          <div class="balance-month-grid">
            ${cells.join("")}
          </div>
        </div>
      `;
    }

    renderDayCell(date, entry, maxAbs, isPlaceholder = false) {
      if (isPlaceholder || !date) {
        return '<div class="balance-day placeholder" role="presentation"></div>';
      }

      const isSelected = this.selectedDate === date;
      const value = entry ? entry.net : 0;
      const color = entry ? this.computeColor(value, maxAbs) : "#e5e7eb";
      const intensity = entry ? Math.min(1, Math.abs(value) / (maxAbs || 1)) : 0;
      const classNames = ["balance-day"];
      if (!entry) classNames.push("empty");
      if (isSelected) classNames.push("selected");
      if (entry && entry.net > 0) classNames.push("positive");
      if (entry && entry.net < 0) classNames.push("negative");

      const tooltip = entry
        ? `${this.formatDateLabel(date)}\nIncome: ${this.formatCurrency(
            entry.income
          )}\nExpense: ${this.formatCurrency(
            entry.expense
          )}\nNet: ${this.formatCurrency(entry.net)}`
        : `${this.formatDateLabel(date)}\nNo transactions`;

      return `
        <div
          class="${classNames.join(" ")}"
          data-date="${date}"
          data-has-entry="${entry ? "true" : "false"}"
          style="background:${color};"
          title="${Utils.escapeHtml(tooltip)}"
        >
          <span class="day-dot" style="opacity:${intensity}"></span>
        </div>
      `;
    }

    attachDayHandlers() {
      // Make day cells clickable to open month modal
      this.heatmapContainer
        .querySelectorAll(".balance-day[data-date]")
        .forEach((dayCell) => {
          dayCell.addEventListener("click", (e) => {
            e.stopPropagation(); // Prevent event from bubbling to month handler
            // Find the parent month block to get the month key
            const monthBlock = dayCell.closest(".balance-month");
            if (monthBlock) {
              const monthKey = monthBlock.getAttribute("data-month");
              this.openMonthModal(monthKey);
            }
          });
        });
    }

    attachMonthHandlers() {
      this.heatmapContainer
        .querySelectorAll(".balance-month")
        .forEach((monthBlock) => {
          monthBlock.addEventListener("click", (e) => {
            // Don't open modal if clicking on a day cell (day cells handle their own clicks)
            if (e.target.closest(".balance-day")) {
              return;
            }
            const monthKey = monthBlock.getAttribute("data-month");
            this.openMonthModal(monthKey);
          });
        });
    }

    openMonthModal(monthKey) {
      const [year, month] = monthKey.split("-").map(Number);
      const dayMap = new Map();
      this.latestData.days.forEach((day) => dayMap.set(day.date, day));
      const maxAbs = this.latestData.maxAbsoluteNet || 0;

      const monthInfo = { year, month: month - 1 };
      const monthContent = this.renderMonthBlock(monthInfo, dayMap, maxAbs);

      const modal = document.createElement("div");
      modal.className = "balance-month-modal";
      modal.innerHTML = `
        <div class="balance-month-modal-overlay"></div>
        <div class="balance-month-modal-content">
          <button class="balance-month-modal-close" aria-label="Close">
            <i class="fas fa-times"></i>
          </button>
          <div class="balance-month-modal-body">
            ${monthContent}
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      // Close handlers
      const closeBtn = modal.querySelector(".balance-month-modal-close");
      const overlay = modal.querySelector(".balance-month-modal-overlay");

      const closeModal = () => {
        modal.classList.add("closing");
        setTimeout(() => modal.remove(), 300);
      };

      closeBtn.addEventListener("click", closeModal);
      overlay.addEventListener("click", closeModal);

      // Animate in
      requestAnimationFrame(() => {
        modal.classList.add("active");
      });
    }

    async selectDay(date, hasEntry) {
      this.selectedDate = date;
      this.heatmapContainer
        .querySelectorAll(".balance-day[data-date]")
        .forEach((btn) => {
          btn.classList.toggle(
            "selected",
            btn.getAttribute("data-date") === date
          );
        });

      // Skip detail panel rendering if it doesn't exist
      if (!this.detailPanel) {
        return;
      }

      if (!hasEntry) {
        this.renderDetailEmpty(date);
        return;
      }

      try {
        this.detailPanel.classList.add("loading");
        const result = await this.api.getBalanceTransactions(date);
        if (!result.success || !result.data) {
          throw new Error(result.error || "Unable to load transactions");
        }
        this.renderDetail(result.data);
      } catch (error) {
        logger.error(`Failed to load transactions: ${error}`, "BALANCE");
        this.renderDetailError(error?.message || "Unable to load transactions");
      } finally {
        this.detailPanel.classList.remove("loading");
      }
    }

    renderDetailEmpty(date) {
      if (!this.detailPanel) return;
      this.detailPanel.innerHTML = `
        <div class="detail-empty">
          <i class="fas fa-info-circle"></i>
          <h3>${this.formatDateLabel(date)}</h3>
          <p>No transactions recorded for this day.</p>
        </div>
      `;
    }

    renderDetailError(message) {
      if (!this.detailPanel) return;
      this.detailPanel.innerHTML = `
        <div class="detail-empty error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>${Utils.escapeHtml(message)}</p>
        </div>
      `;
    }

    renderDetail(data) {
      if (!this.detailPanel) return;
      
      const { date, transactions } = data;
      if (!transactions?.length) {
        this.renderDetailEmpty(date);
        return;
      }

      const rows = transactions
        .map((tx) => {
          const directionClass =
            tx.direction === "income" ? "income" : "expense";
          return `
            <div class="transaction-row ${directionClass}">
              <div class="transaction-amount">${this.formatCurrency(
                tx.amount
              )}</div>
              <div class="transaction-meta">
                <span class="transaction-direction">${tx.direction.toUpperCase()}</span>
                ${tx.category ? `<span class="transaction-category">${Utils.escapeHtml(tx.category)}</span>` : ""}
                ${tx.description ? `<p class="transaction-description">${Utils.escapeHtml(tx.description)}</p>` : ""}
              </div>
              ${tx.source_file ? `<div class="transaction-source">${Utils.escapeHtml(tx.source_file)}</div>` : ""}
            </div>
          `;
        })
        .join("");

      this.detailPanel.innerHTML = `
        <div class="detail-header">
          <h3>${this.formatDateLabel(date)}</h3>
          <span>${transactions.length} transaction${
        transactions.length !== 1 ? "s" : ""
      }</span>
        </div>
        <div class="transaction-list">${rows}</div>
      `;
    }

    async handleProcess(fileNameOverride = null, replaceOverride = null) {
      const selectedFile = fileNameOverride || this.currentFileName;
      if (!selectedFile) {
        this.setFeedback("Please upload a balance document first.", "error");
        return;
      }

      try {
        this.setProcessing(true);
        this.setFeedback("Running agent…", "info");

        if (fileNameOverride) {
          this.currentFileName = fileNameOverride;
        }

        const replaceExisting =
          typeof replaceOverride === "boolean"
            ? replaceOverride
            : true;
        const result = await this.api.processBalanceWorkbook(
          selectedFile,
          replaceExisting
        );

        if (!result.success || !result.data) {
          throw new Error(result.error || "Agent run failed");
        }

        const message = result.data?.message || "Agent completed successfully.";
        this.setFeedback(message, "success");
        this.currentFileName = selectedFile;
        await this.refreshCalendar();
      } catch (error) {
        logger.error(`Balance process error: ${error}`, "BALANCE");
        this.setFeedback(error?.message || "Failed to run the agent.", "error");
      } finally {
        this.setProcessing(false);
      }
    }

    setProcessing(isProcessing) {
      if (this.processButton) {
        this.processButton.disabled = isProcessing;
        this.processButton.classList.toggle("loading", isProcessing);
      }
      this.setUploadBusy(isProcessing);
    }

    setUploadBusy(isBusy) {
      if (this.uploadButton) {
        this.uploadButton.disabled = isBusy;
        this.uploadButton.classList.toggle("loading", isBusy);
      }
    }

    setFeedback(message, state) {
      if (!this.feedbackBox) return;
      this.feedbackBox.textContent = message;
      this.feedbackBox.setAttribute("data-state", state);
      this.feedbackBox.classList.toggle("visible", Boolean(message));
    }

    async loadInitialDataIfNeeded() {
      // Only load data once, on first activation or manual refresh
      if (!this.isDataLoaded) {
        await this.refreshCalendar();
      }
    }

    async handleUploadSelection(event) {
      const files = Array.from(event?.target?.files || []);
      if (!files.length) {
        return;
      }

      const file = files[0];
      if (!BALANCE_FILE_REGEX.test(file.name)) {
        this.setFeedback("Unsupported file type for balance processing.", "error");
        event.target.value = "";
        return;
      }
      event.target.value = "";

      try {
        this.setUploadBusy(true);
        this.setFeedback(`Uploading ${file.name}…`, "info");

        const uploadResult = await this.api.uploadBalanceDocument(file);
        if (!uploadResult.success) {
          throw new Error(uploadResult.error || "Upload failed");
        }

        const uploadedName =
          uploadResult.data?.filename ||
          uploadResult.data?.file_name ||
          file.name;

        this.currentFileName = uploadedName;

        this.setFeedback(
          `File ${uploadedName} uploaded successfully. Click "Run Agent" to process.`,
          "success"
        );
        
        // Enable the process button
        if (this.processButton) {
          this.processButton.disabled = false;
        }
      } catch (error) {
        logger.error(`Balance upload error: ${error}`, "BALANCE");
        this.setFeedback(
          error?.message || "Failed to upload balance document.",
          "error"
        );
      } finally {
        this.setUploadBusy(false);
      }
    }

    computeColor(value, maxAbs) {
      if (!maxAbs || maxAbs <= 0 || !value) {
        return "#e5e7eb";
      }

      const ratio = Math.min(1, Math.abs(value) / maxAbs);
      const hue = value >= 0 ? 140 : 5;
      const saturation = 60;
      const lightness = 80 - ratio * 50; // 80% for smallest, 30% for largest
      return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    }

    formatCurrency(value) {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 2,
      }).format(value || 0);
    }

    formatDateLabel(value) {
      if (!value) return "-";
      try {
        const date = new Date(value);
        return date.toLocaleDateString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
        });
      } catch (error) {
        return value;
      }
    }
  }

  // Category Pie Chart Class
  class CategoryPieChart {
    constructor() {
      this.api = window.apiService || new APIService();
      this.canvas = document.getElementById("category-pie-chart");
      this.legendContainer = document.getElementById("category-chart-legend");
      this.loadingIndicator = document.getElementById("category-chart-loading");
      this.emptyMessage = document.getElementById("category-chart-empty");
      this.ctx = this.canvas?.getContext("2d");
      this.chartData = null;
      
      // Color palette for categories
      this.colors = [
        { bg: "rgba(59, 130, 246, 0.8)", border: "rgba(59, 130, 246, 1)" },   // Blue
        { bg: "rgba(16, 185, 129, 0.8)", border: "rgba(16, 185, 129, 1)" },   // Green
        { bg: "rgba(245, 158, 11, 0.8)", border: "rgba(245, 158, 11, 1)" },   // Amber
      ];
    }

    async refresh() {
      if (!this.canvas || !this.ctx) {
        console.warn("Category pie chart canvas not found");
        return;
      }

      this.showLoading(true);
      this.hideEmpty();

      try {
        const result = await this.api.getBalanceCategoryTotals();
        
        if (!result.success) {
          throw new Error(result.error || "Failed to fetch category data");
        }

        const categories = result.data?.categories || [];
        
        if (categories.length === 0) {
          this.showEmpty(true);
          this.clear();
          return;
        }

        this.chartData = categories;
        this.render();
        this.renderLegend();
      } catch (error) {
        console.error("Error loading category chart:", error);
        this.showEmpty(true);
        this.clear();
      } finally {
        this.showLoading(false);
      }
    }

    render() {
      if (!this.chartData || this.chartData.length === 0) {
        return;
      }

      const total = this.chartData.reduce((sum, item) => sum + item.total, 0);
      
      if (total === 0) {
        this.showEmpty(true);
        return;
      }

      // Clear canvas
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      // Calculate center and radius
      const centerX = this.canvas.width / 2;
      const centerY = this.canvas.height / 2;
      const radius = Math.min(centerX, centerY) - 20;

      let currentAngle = -Math.PI / 2; // Start from top

      this.chartData.forEach((item, index) => {
        const percentage = item.total / total;
        const sliceAngle = percentage * 2 * Math.PI;
        const color = this.colors[index % this.colors.length];

        // Draw slice
        this.ctx.beginPath();
        this.ctx.moveTo(centerX, centerY);
        this.ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
        this.ctx.closePath();
        this.ctx.fillStyle = color.bg;
        this.ctx.fill();
        this.ctx.strokeStyle = color.border;
        this.ctx.lineWidth = 2;
        this.ctx.stroke();

        // Draw percentage label
        const labelAngle = currentAngle + sliceAngle / 2;
        const labelRadius = radius * 0.65;
        const labelX = centerX + Math.cos(labelAngle) * labelRadius;
        const labelY = centerY + Math.sin(labelAngle) * labelRadius;

        this.ctx.fillStyle = "#ffffff";
        this.ctx.font = "bold 16px Inter, sans-serif";
        this.ctx.textAlign = "center";
        this.ctx.textBaseline = "middle";
        this.ctx.shadowColor = "rgba(0, 0, 0, 0.5)";
        this.ctx.shadowBlur = 4;
        this.ctx.fillText(`${(percentage * 100).toFixed(1)}%`, labelX, labelY);
        this.ctx.shadowBlur = 0;

        currentAngle += sliceAngle;
      });
    }

    renderLegend() {
      if (!this.legendContainer || !this.chartData) {
        return;
      }

      this.legendContainer.innerHTML = "";
      const total = this.chartData.reduce((sum, item) => sum + item.total, 0);

      this.chartData.forEach((item, index) => {
        const color = this.colors[index % this.colors.length];
        const percentage = ((item.total / total) * 100).toFixed(1);
        
        const legendItem = document.createElement("div");
        legendItem.className = "legend-item";
        legendItem.innerHTML = `
          <div class="legend-color" style="background-color: ${color.bg}; border-color: ${color.border};"></div>
          <div class="legend-content">
            <div class="legend-label">${item.category}</div>
            <div class="legend-value">${this.formatCurrency(item.total)} (${percentage}%)</div>
          </div>
        `;
        
        this.legendContainer.appendChild(legendItem);
      });
    }

    formatCurrency(value) {
      return new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 2,
      }).format(value || 0);
    }

    showLoading(show) {
      if (this.loadingIndicator) {
        this.loadingIndicator.style.display = show ? "flex" : "none";
      }
    }

    showEmpty(show) {
      if (this.emptyMessage) {
        this.emptyMessage.style.display = show ? "flex" : "none";
      }
      if (this.canvas) {
        this.canvas.style.display = show ? "none" : "block";
      }
      if (this.legendContainer) {
        this.legendContainer.style.display = show ? "none" : "block";
      }
    }

    hideEmpty() {
      this.showEmpty(false);
    }

    clear() {
      if (this.ctx && this.canvas) {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      }
      if (this.legendContainer) {
        this.legendContainer.innerHTML = "";
      }
    }
  }

  // Category Column Chart Class
  class CategoryColumnChart {
    constructor() {
      this.api = window.apiService || new APIService();
      this.canvas = document.getElementById("category-column-chart");
      this.ctx = this.canvas?.getContext("2d");
      this.chartData = null;
      
      // Color palette matching pie chart
      this.colors = [
        { bg: "rgba(59, 130, 246, 0.8)", border: "rgba(59, 130, 246, 1)" },   // Blue
        { bg: "rgba(16, 185, 129, 0.8)", border: "rgba(16, 185, 129, 1)" },   // Green
        { bg: "rgba(245, 158, 11, 0.8)", border: "rgba(245, 158, 11, 1)" },   // Amber
      ];
      
      // Negative color (for negative net values)
      this.negativeColor = { bg: "rgba(239, 68, 68, 0.8)", border: "rgba(239, 68, 68, 1)" }; // Red
    }

    async refresh() {
      if (!this.canvas || !this.ctx) {
        console.warn("Category column chart canvas not found");
        return;
      }

      try {
        const result = await this.api.getBalanceCategoryNetValues();
        
        if (!result.success) {
          throw new Error(result.error || "Failed to fetch category net data");
        }

        const categories = result.data?.categories || [];
        
        if (categories.length === 0) {
          this.clear();
          return;
        }

        this.chartData = categories;
        this.render();
      } catch (error) {
        console.error("Error loading category column chart:", error);
        this.clear();
      }
    }

    render() {
      if (!this.chartData || this.chartData.length === 0) {
        return;
      }

      const padding = { top: 40, right: 20, bottom: 80, left: 80 };
      const chartWidth = this.canvas.width - padding.left - padding.right;
      const chartHeight = this.canvas.height - padding.top - padding.bottom;

      // Clear canvas
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      // Find max and min values for scaling
      const netValues = this.chartData.map(item => item.net);
      const maxValue = Math.max(...netValues, 0);
      const minValue = Math.min(...netValues, 0);
      const absMax = Math.max(Math.abs(maxValue), Math.abs(minValue));

      // Draw title
      this.ctx.fillStyle = "#0f172a";
      this.ctx.font = "600 16px Inter, sans-serif";
      this.ctx.textAlign = "center";
      this.ctx.fillText("Net Value (TRY)", this.canvas.width / 2, 22);

      // Calculate bar width and spacing
      const barCount = this.chartData.length;
      const barSpacing = chartWidth / (barCount * 2);
      const barWidth = (chartWidth - barSpacing * (barCount + 1)) / barCount;

      // Draw axes
      this.drawAxes(padding, chartWidth, chartHeight, absMax);

      // Draw bars
      this.chartData.forEach((item, index) => {
        const color = this.colors[index % this.colors.length];
        const x = padding.left + barSpacing + index * (barWidth + barSpacing);
        const netValue = item.net;
        
        // Determine bar color (positive or negative)
        const barColor = netValue >= 0 ? color : this.negativeColor;
        
        // Calculate bar height and position
        const zeroY = padding.top + chartHeight / 2;
        let barHeight = 0;
        let barY = zeroY;
        
        if (absMax > 0) {
          barHeight = Math.abs(netValue) * (chartHeight / 2) / absMax;
          if (netValue >= 0) {
            barY = zeroY - barHeight;
          } else {
            barY = zeroY;
          }
        }

        // Draw bar
        this.ctx.fillStyle = barColor.bg;
        this.ctx.fillRect(x, barY, barWidth, Math.abs(barHeight));
        
        // Draw bar border
        this.ctx.strokeStyle = barColor.border;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, barY, barWidth, Math.abs(barHeight));

        // Draw value label on top of bar
        const labelY = netValue >= 0 ? barY - 10 : barY + barHeight + 20;
        const labelText = this.formatCompactCurrency(netValue);
        
        // Draw text directly without background
        this.ctx.font = "600 16px Inter, sans-serif";
        this.ctx.fillStyle = "#ffffff";
        this.ctx.textAlign = "center";
        this.ctx.shadowColor = "rgba(0, 0, 0, 0.7)";
        this.ctx.shadowBlur = 4;
        this.ctx.fillText(labelText, x + barWidth / 2, labelY);
        this.ctx.shadowBlur = 0;

        // Draw category label below x-axis (horizontal, not rotated)
        this.ctx.font = "600 14px Inter, sans-serif";
        this.ctx.fillStyle = "#ffffff";
        this.ctx.textAlign = "center";
        this.ctx.textBaseline = "top";
        
        // Shorten category names
        let categoryLabel = item.category;
        categoryLabel = categoryLabel.replace(" Faaliyetleri", "").replace(" Activities", "");
        if (categoryLabel.length > 20) {
          categoryLabel = categoryLabel.substring(0, 18) + "...";
        }
        
        // Add shadow for better readability
        this.ctx.shadowColor = "rgba(0, 0, 0, 0.7)";
        this.ctx.shadowBlur = 4;
        this.ctx.fillText(categoryLabel, x + barWidth / 2, padding.top + chartHeight + 12);
        this.ctx.shadowBlur = 0;
      });
    }

    drawAxes(padding, chartWidth, chartHeight, absMax) {
      const zeroY = padding.top + chartHeight / 2;

      // Draw y-axis
      this.ctx.strokeStyle = "#64748b";
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(padding.left, padding.top);
      this.ctx.lineTo(padding.left, padding.top + chartHeight);
      this.ctx.stroke();

      // Draw x-axis (zero line)
      this.ctx.strokeStyle = "#94a3b8";
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(padding.left, zeroY);
      this.ctx.lineTo(padding.left + chartWidth, zeroY);
      this.ctx.stroke();

      // Draw y-axis labels
      this.ctx.fillStyle = "#ffffff";
      this.ctx.font = "600 14px Inter, sans-serif";
      this.ctx.textAlign = "right";
      this.ctx.textBaseline = "middle";
      this.ctx.shadowColor = "rgba(0, 0, 0, 0.7)";
      this.ctx.shadowBlur = 3;

      // Positive side
      const steps = 3;
      for (let i = 0; i <= steps; i++) {
        const value = (absMax / steps) * i;
        const y = zeroY - (chartHeight / 2) * (i / steps);
        this.ctx.fillText(this.formatCompactCurrency(value), padding.left - 10, y);
        
        // Draw grid line
        this.ctx.shadowBlur = 0;
        this.ctx.strokeStyle = "#cbd5e1";
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(padding.left, y);
        this.ctx.lineTo(padding.left + chartWidth, y);
        this.ctx.stroke();
        this.ctx.shadowBlur = 3;
      }

      // Negative side
      for (let i = 1; i <= steps; i++) {
        const value = -(absMax / steps) * i;
        const y = zeroY + (chartHeight / 2) * (i / steps);
        this.ctx.fillText(this.formatCompactCurrency(value), padding.left - 10, y);
        
        // Draw grid line
        this.ctx.shadowBlur = 0;
        this.ctx.strokeStyle = "#cbd5e1";
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(padding.left, y);
        this.ctx.lineTo(padding.left + chartWidth, y);
        this.ctx.stroke();
        this.ctx.shadowBlur = 3;
      }
      
      this.ctx.shadowBlur = 0;
    }

    formatCurrency(value) {
      return new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 0,
      }).format(value || 0);
    }

    formatCompactCurrency(value) {
      const absValue = Math.abs(value);
      let formatted = "";
      
      if (absValue >= 1000000) {
        formatted = (value / 1000000).toFixed(1) + "M";
      } else if (absValue >= 1000) {
        formatted = (value / 1000).toFixed(1) + "K";
      } else {
        formatted = value.toFixed(0);
      }
      
      return formatted + " ₺";
    }

    clear() {
      if (this.ctx && this.canvas) {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      }
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".balance-app")) {
      window.balanceCalendarApp = new BalanceCalendarApp();
      
      // Load initial data once on startup
      setTimeout(() => {
        if (window.balanceCalendarApp) {
          window.balanceCalendarApp.loadInitialDataIfNeeded();
        }
      }, 500);
    }
    
    // Initialize category charts
    if (document.getElementById("category-pie-chart")) {
      window.categoryPieChart = new CategoryPieChart();
      // Initial load when balance tab is visible
      setTimeout(() => {
        if (window.categoryPieChart && document.getElementById("category-pie-chart")) {
          window.categoryPieChart.refresh();
        }
      }, 500);
    }
    
    if (document.getElementById("category-column-chart")) {
      window.categoryColumnChart = new CategoryColumnChart();
      // Initial load when balance tab is visible
      setTimeout(() => {
        if (window.categoryColumnChart && document.getElementById("category-column-chart")) {
          window.categoryColumnChart.refresh();
        }
      }, 500);
    }
  });
})();

