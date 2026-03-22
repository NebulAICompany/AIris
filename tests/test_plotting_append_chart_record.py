import importlib.util
import json
import sys
import types
from pathlib import Path


def _load_plotting_module():
    langchain_tools = types.ModuleType("langchain.tools")

    def tool(*args, **kwargs):
        def decorator(fn):
            fn.func = fn
            return fn

        return decorator

    langchain_tools.tool = tool
    sys.modules["langchain.tools"] = langchain_tools

    dotenv_module = types.ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv_module

    e2b_module = types.ModuleType("e2b_code_interpreter")
    e2b_module.Sandbox = object
    sys.modules["e2b_code_interpreter"] = e2b_module

    pydantic_module = types.ModuleType("pydantic")
    pydantic_module.BaseModel = object
    pydantic_module.Field = lambda *args, **kwargs: None
    sys.modules["pydantic"] = pydantic_module

    finance_module = types.ModuleType("backend.core.tools.finance")
    finance_module.calculate_sma = lambda *args, **kwargs: None
    finance_module.calculate_ema = lambda *args, **kwargs: None
    finance_module.calculate_bollinger_bands = lambda *args, **kwargs: (None, None, None)
    finance_module.calculate_rsi = lambda *args, **kwargs: None
    finance_module.calculate_macd = lambda *args, **kwargs: (None, None, None)
    finance_module.get_eod_data = types.SimpleNamespace(func=lambda **kwargs: {"data": []})
    sys.modules["backend.core.tools.finance"] = finance_module

    class _DummyLogger:
        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

    logger_module = types.ModuleType("backend.shared.logger")
    logger_module.get_logger = lambda *_args, **_kwargs: _DummyLogger()
    sys.modules["backend.shared.logger"] = logger_module

    constants_module = types.ModuleType("backend.shared.constants")
    constants_module.BASE_DIR = Path("/tmp")
    constants_module.CHARTS_DIR = Path("/tmp/charts")
    constants_module.CHART_DATA_FILE = Path("/tmp/charts/chart_data.json")
    constants_module.CREATED_DOCUMENTS_PATH = Path("/tmp/created")
    constants_module.REPORTS_CHARTS_FILE = Path("/tmp/created/chart_reports.json")
    sys.modules["backend.shared.constants"] = constants_module

    pandas_module = types.ModuleType("pandas")
    pandas_module.DatetimeIndex = type("DatetimeIndex", (), {})
    pandas_module.to_datetime = lambda x: x
    pandas_module.DataFrame = object
    pandas_module.bdate_range = lambda *args, **kwargs: []
    sys.modules["pandas"] = pandas_module

    plotly_module = types.ModuleType("plotly")
    plotly_graph_objects = types.ModuleType("plotly.graph_objects")
    plotly_subplots = types.ModuleType("plotly.subplots")
    plotly_subplots.make_subplots = lambda *args, **kwargs: None
    sys.modules["plotly"] = plotly_module
    sys.modules["plotly.graph_objects"] = plotly_graph_objects
    sys.modules["plotly.subplots"] = plotly_subplots

    plotting_path = Path("/home/runner/work/AIris/AIris/backend/core/tools/plotting.py")
    spec = importlib.util.spec_from_file_location("plotting_under_test", plotting_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_append_chart_record_accepts_str_paths(tmp_path):
    plotting = _load_plotting_module()

    base_dir = tmp_path / "backend"
    charts_dir = base_dir / "database" / "charts"
    reports_file = base_dir / "database" / "created_documents" / "chart_reports.json"
    html_path = charts_dir / "chart.html"

    charts_dir.mkdir(parents=True, exist_ok=True)
    reports_file.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text("<html></html>", encoding="utf-8")

    plotting.BASE_DIR = base_dir
    plotting.CHARTS_DIR = charts_dir
    plotting.REPORTS_CHARTS_FILE = reports_file

    plotting.append_chart_record("", str(html_path), "test chart")

    data = json.loads(reports_file.read_text(encoding="utf-8"))
    assert data[0]["png_file_path"] == ""
    assert data[0]["html_file_path"] == "database/charts/chart.html"


def test_append_chart_record_keeps_external_paths(tmp_path):
    plotting = _load_plotting_module()

    base_dir = tmp_path / "backend"
    charts_dir = base_dir / "database" / "charts"
    reports_file = base_dir / "database" / "created_documents" / "chart_reports.json"
    external_html = tmp_path / "external" / "chart.html"

    charts_dir.mkdir(parents=True, exist_ok=True)
    reports_file.parent.mkdir(parents=True, exist_ok=True)
    external_html.parent.mkdir(parents=True, exist_ok=True)
    external_html.write_text("<html></html>", encoding="utf-8")

    plotting.BASE_DIR = base_dir
    plotting.CHARTS_DIR = charts_dir
    plotting.REPORTS_CHARTS_FILE = reports_file

    plotting.append_chart_record(Path(""), external_html, "external chart")

    data = json.loads(reports_file.read_text(encoding="utf-8"))
    assert data[0]["html_file_path"] == external_html.as_posix()
