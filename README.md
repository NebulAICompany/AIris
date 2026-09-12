# AIris

AIris is a multi-agent, B2B financial assistant designed for financial institutions and researchers. It allows users to query large archives of financial documents (policies, contracts, reports, financial statements) in natural language and receive auditable, decision-ready answers, technical charts, and generated Office documents (Word, Excel, PowerPoint).

For detailed architecture and system design, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Installation and Setup

### Prerequisites

- Python 3.11+ (Python 3.11 recommended)
- Node.js 16+
- `.env` file in the root directory

### Setup Steps

1. **Backend Setup:**

   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS / Linux

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Frontend Setup:**

   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` in the root directory and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

### Running the Application

1. **Open two terminal windows** (split terminal recommended)
2. **Start the Backend:**

   ```bash
   .venv\Scripts\activate  # Activate virtual environment
   python backend_runner.py
   ```

3. **Start the Frontend:**

   ```bash
   python frontend_runner.py
   ```

> **Note:** The backend may take some time to start, especially on the first run. The frontend can be opened in advance, but it is recommended to wait until the backend is fully initialized before submitting queries.
