(function () {
  const BALANCE_FILE_REGEX = /\.(xlsx|xls|pdf|docx|doc|txt|jpg|jpeg|png|gif|bmp|tiff|tif)$/i;

  class BalanceCalendarApp {
    constructor() {
      this.api = window.apiService || new APIService();
      this.timeframeSelect = document.getElementById("balance-timeframe");
      this.refreshButton = document.getElementById("balance-refresh");
      this.fileSelect = document.getElementById("balance-file-select");
      this.replaceCheckbox = document.getElementById("balance-replace-checkbox");
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
      this.init();
    }

    init() {
      this.bindEvents();
      this.loadFileOptions();
      this.refreshCalendar();
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

    async loadFileOptions() {
      if (!this.fileSelect) return;
      try {
        const result = await this.api.getFiles();
        if (!result.success || !Array.isArray(result.files)) {
          throw new Error(result.error || "Unable to fetch uploads");
        }

        const options = result.files
          .filter((file) => BALANCE_FILE_REGEX.test(file.name))
          .sort((a, b) => a.name.localeCompare(b.name));

        if (!options.length) {
          this.fileSelect.innerHTML =
            '<option value="" disabled selected>No balance documents found</option>';
          return;
        }

        const fragments = [
          '<option value="" disabled selected>Select a balance document…</option>',
          ...options.map(
            (file) =>
              `<option value="${file.name}">${Utils.escapeHtml(
                file.name
              )}</option>`
          ),
        ];

        this.fileSelect.innerHTML = fragments.join("");
      } catch (error) {
        this.fileSelect.innerHTML =
          '<option value="" disabled selected>Failed to load documents</option>';
        logger.error(`Failed to load balance document list: ${error}`, "BALANCE");
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
          acc.net += day.net;
          return acc;
        },
        { income: 0, expense: 0, net: 0 }
      );

      const rangeText = `${this.formatDateLabel(
        data.startDate
      )} - ${this.formatDateLabel(data.endDate)}`;

      const latestText = data.latestActivity
        ? `Latest activity: ${this.formatDateLabel(data.latestActivity)}`
        : "No activity recorded yet";

      this.summaryContainer.innerHTML = `
        <div class="summary-range">
          <div class="summary-label">Period</div>
          <div class="summary-value">${rangeText}</div>
          <div class="summary-subtext">${latestText}</div>
        </div>
        <div class="summary-metric positive">
          <span class="label">Total Income</span>
          <span class="value">${this.formatCurrency(totals.income)}</span>
        </div>
        <div class="summary-metric negative">
          <span class="label">Total Expense</span>
          <span class="value">${this.formatCurrency(totals.expense)}</span>
        </div>
        <div class="summary-metric neutral">
          <span class="label">Net Change</span>
          <span class="value">${this.formatCurrency(totals.net)}</span>
        </div>
      `;
    }

    renderLegend(maxAbsoluteNet) {
      if (!this.legendContainer) return;

      if (!maxAbsoluteNet || maxAbsoluteNet <= 0) {
        this.legendContainer.innerHTML = "";
        return;
      }

      const steps = [0.2, 0.4, 0.6, 0.8, 1];
      const segments = steps
        .map((ratio) => {
          const positiveColor = this.computeColor(
            maxAbsoluteNet * ratio,
            maxAbsoluteNet
          );
          const negativeColor = this.computeColor(
            -maxAbsoluteNet * ratio,
            maxAbsoluteNet
          );

          return `
            <div class="legend-row">
              <div class="legend-swatch" style="background:${negativeColor}"></div>
              <span class="legend-label">-${Math.round(
                ratio * 100
              )}%</span>
              <div class="legend-divider"></div>
              <span class="legend-label">+${Math.round(ratio * 100)}%</span>
              <div class="legend-swatch" style="background:${positiveColor}"></div>
            </div>
          `;
        })
        .join("");

      this.legendContainer.innerHTML = `
        <div class="legend-title">
          <i class="fas fa-circle"></i>
          Net balance intensity
        </div>
        ${segments}
      `;
    }

    renderHeatmap(data) {
      if (!this.heatmapContainer) return;

      const start = new Date(data.startDate);
      const end = new Date(data.endDate);
      const dayMap = new Map();
      data.days.forEach((day) => dayMap.set(day.date, day));
      const maxAbs = data.maxAbsoluteNet || 0;

      const weeks = [];
      let cursor = new Date(start);
      while (cursor <= end) {
        const week = [];
        for (let i = 0; i < 7; i++) {
          const dayKey = cursor.toISOString().slice(0, 10);
          const entry = dayMap.get(dayKey);
          week.push({
            date: dayKey,
            entry,
            currentMonth: cursor.getMonth(),
          });
          cursor.setDate(cursor.getDate() + 1);
        }
        weeks.push(week);
      }

      const monthLabels = this.buildMonthLabels(start, weeks);

      const heatmapHtml = weeks
        .map((week, weekIndex) => {
          const monthLabel = monthLabels.get(weekIndex);
          const cells = week
            .map((day) => this.renderDayCell(day, maxAbs))
            .join("");
          return `
            <div class="balance-week">
              <div class="balance-week-label">${monthLabel || ""}</div>
              <div class="balance-week-days">
                ${cells}
              </div>
            </div>
          `;
        })
        .join("");

      const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        .map((label) => `<div class="balance-weekday">${label}</div>`)
        .join("");

      this.heatmapContainer.innerHTML = `
        <div class="balance-grid">
          <div class="balance-weekday-column">${weekdayLabels}</div>
          <div class="balance-weeks">${heatmapHtml}</div>
        </div>
      `;

      this.attachDayHandlers();
    }

    buildMonthLabels(startDate, weeks) {
      const labels = new Map();
      let lastMonth = null;
      weeks.forEach((week, index) => {
        const firstDay = week[0];
        const dateObj = new Date(firstDay.date);
        const month = dateObj.getMonth();
        if (month !== lastMonth) {
          labels.set(
            index,
            dateObj.toLocaleString(undefined, {
              month: "short",
              year: dateObj.getFullYear() !== new Date(startDate).getFullYear()
                ? "numeric"
                : undefined,
            })
          );
          lastMonth = month;
        }
      });
      return labels;
    }

    renderDayCell(day, maxAbs) {
      const { date, entry } = day;
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
        <button
          class="${classNames.join(" ")}"
          data-date="${date}"
          data-has-entry="${entry ? "true" : "false"}"
          style="background:${color};"
          title="${Utils.escapeHtml(tooltip)}"
          aria-pressed="${isSelected}"
        >
          <span class="day-dot" style="opacity:${intensity}"></span>
        </button>
      `;
    }

    attachDayHandlers() {
      this.heatmapContainer
        .querySelectorAll(".balance-day")
        .forEach((button) => {
          button.addEventListener("click", () => {
            const date = button.getAttribute("data-date");
            const hasEntry = button.getAttribute("data-has-entry") === "true";
            this.selectDay(date, hasEntry);
          });
        });
    }

    async selectDay(date, hasEntry) {
      this.selectedDate = date;
      this.heatmapContainer
        .querySelectorAll(".balance-day")
        .forEach((btn) => {
          btn.classList.toggle(
            "selected",
            btn.getAttribute("data-date") === date
          );
        });

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
      this.detailPanel.innerHTML = `
        <div class="detail-empty">
          <i class="fas fa-info-circle"></i>
          <h3>${this.formatDateLabel(date)}</h3>
          <p>No transactions recorded for this day.</p>
        </div>
      `;
    }

    renderDetailError(message) {
      this.detailPanel.innerHTML = `
        <div class="detail-empty error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>${Utils.escapeHtml(message)}</p>
        </div>
      `;
    }

    renderDetail(data) {
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
      const selectedFile = fileNameOverride || this.fileSelect?.value;
      if (!selectedFile) {
        this.setFeedback("Please select a balance document first.", "error");
        return;
      }

      try {
        this.setProcessing(true);
        if (!fileNameOverride) {
          this.setFeedback("Running agent…", "info");
        }

        if (this.fileSelect && fileNameOverride) {
          this.fileSelect.value = selectedFile;
        }

        const replaceExisting =
          typeof replaceOverride === "boolean"
            ? replaceOverride
            : Boolean(this.replaceCheckbox?.checked);
        const result = await this.api.processBalanceWorkbook(
          selectedFile,
          replaceExisting
        );

        if (!result.success || !result.data) {
          throw new Error(result.error || "Agent run failed");
        }

        const message = result.data?.message || "Agent completed successfully.";
        this.setFeedback(message, "success");
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

    async refreshOnActivate() {
      await this.loadFileOptions();
      await this.refreshCalendar();
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

        const uploadResult = await this.api.uploadFile(file);
        if (!uploadResult.success) {
          throw new Error(uploadResult.error || "Upload failed");
        }

        const uploadedName =
          uploadResult.data?.filename ||
          uploadResult.data?.file_name ||
          file.name;

        await this.loadFileOptions();
        if (this.fileSelect) {
          this.fileSelect.value = uploadedName;
        }

        if (this.replaceCheckbox) {
          this.replaceCheckbox.checked = true;
        }

        this.setFeedback(
          `Uploaded ${uploadedName}. Running agent…`,
          "info"
        );

        await this.handleProcess(uploadedName, true);
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

  document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".balance-app")) {
      window.balanceCalendarApp = new BalanceCalendarApp();
    }
  });
})();
