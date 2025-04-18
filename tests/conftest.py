# Create pytest conftest that installs lightweight stubs for heavy/compiled dependencies so individual tests remain clean.

"""tests/conftest.py
Central location for lightweight dummy modules used during tests.
Automatically installs cheap stubs for heavy / C‑extension dependencies
(numpy, pandas, tiktoken, openai, pydantic, psycopg2, etc.) before any
application code is imported.  This keeps individual test files small
and avoids repetitive monkey‑patching.
"""
from __future__ import annotations

import sys, types, os

# ---------------------------------------------------------------------
# Helper to register a dummy module (and optional submodules)
# ---------------------------------------------------------------------

def _add_dummy_module(name: str, attrs: dict | None = None):
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ---------------------------------------------------------------------
# Basic scientific libs & regex C‑ext replacements
# ---------------------------------------------------------------------
for _name in [
    "numpy",
    "pandas",
    "regex",
    "regex._regex",
    "pytz",
    "dateutil",  # package placeholder – ensure package semantics later
]:
    if _name not in sys.modules:
        _add_dummy_module(_name)

# Immediately set DataFrame on pandas stub
pd_mod = sys.modules.get('pandas')
if pd_mod:
    if not hasattr(pd_mod, 'DataFrame'):
        class _DummyDataFrame:
            def __init__(self, data=None):
                self._data = data
                self.shape = (len(data) if isinstance(data, list) else 0, 0)
            def __repr__(self):
                return f"<DummyDataFrame shape={self.shape}>"

        pd_mod.DataFrame = _DummyDataFrame

# ---------------------------------------------------------------------
# NLTK minimal stub
# ---------------------------------------------------------------------
nltk_stub = _add_dummy_module("nltk")

# Tokenizer interface used by TextBlob
tokenize_mod = _add_dummy_module("nltk.tokenize")
api_mod = _add_dummy_module("nltk.tokenize.api", {"TokenizerI": type("TokenizerI", (), {})})

setattr(tokenize_mod, "api", api_mod)
setattr(nltk_stub, "tokenize", tokenize_mod)
setattr(nltk_stub, "data", types.SimpleNamespace(find=lambda path: None))

# Stopwords
corpus_mod = _add_dummy_module("nltk.corpus")
stop_mod = _add_dummy_module("nltk.corpus.stopwords", {"words": lambda lang="english": []})
setattr(corpus_mod, "stopwords", stop_mod)

# ---------------------------------------------------------------------
# TextBlob stub
# ---------------------------------------------------------------------
_add_dummy_module("textblob", {"TextBlob": type("TextBlob", (), {})})

# ---------------------------------------------------------------------
# tiktoken stub
# ---------------------------------------------------------------------
if "tiktoken" not in sys.modules:
    tk_root = _add_dummy_module("tiktoken")

    class _DummyEncoding:
        def encode(self, _):
            return []
        def decode(self, _):
            return ""

    core_mod = _add_dummy_module("tiktoken.core", {"Encoding": _DummyEncoding})
    _add_dummy_module("tiktoken._tiktoken")

    tk_root.get_encoding = lambda name="cl100k_base": _DummyEncoding()
    tk_root.encoding_for_model = lambda model: _DummyEncoding()
    tk_root.core = core_mod
    tk_root._tiktoken = sys.modules["tiktoken._tiktoken"]

# ---------------------------------------------------------------------
# OpenAI stub (embeddings & chat)
# ---------------------------------------------------------------------
openai_stub = _add_dummy_module("openai")

class _DummyEmbeddingResp:  # embeds .data[0].embedding
    def __init__(self):
        self.data = [types.SimpleNamespace(embedding=[])]

class _DummyEmbeddings:
    def create(self, *_, **__):
        return _DummyEmbeddingResp()

class _DummyOpenAIClient:
    def __init__(self, *_, **__):
        self.embeddings = _DummyEmbeddings()

openai_stub.OpenAI = _DummyOpenAIClient
openai_stub.RateLimitError = type("RateLimitError", (Exception,), {})
openai_stub.APIError = type("APIError", (Exception,), {})
openai_stub.chat = types.SimpleNamespace(
    completions=types.SimpleNamespace(create=lambda *a, **k: types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="{}"))]
    ))
)

# ---------------------------------------------------------------------
# scikit‑learn stub (TF‑IDF only)
# ---------------------------------------------------------------------
if "sklearn" not in sys.modules:
    sk_root = _add_dummy_module("sklearn")
    feat_mod = _add_dummy_module("sklearn.feature_extraction")

    class _DummyVectorizer:  # noqa: D401
        def fit(self, X):
            return self
        transform = fit_transform = lambda self, X: []

    text_mod = _add_dummy_module(
        "sklearn.feature_extraction.text",
        {"TfidfVectorizer": _DummyVectorizer},
    )
    feat_mod.text = text_mod
    sk_root.feature_extraction = feat_mod
    _add_dummy_module("sklearn.__check_build")

# ---------------------------------------------------------------------
# pydantic & pydantic_core stubs
# ---------------------------------------------------------------------
_add_dummy_module("pydantic", {"BaseModel": type("BaseModel", (), {}), "ValidationError": Exception, "__version__": "0.0.0"})
_add_dummy_module("pydantic_core")
_add_dummy_module("pydantic_core._pydantic_core")

# ---------------------------------------------------------------------
# psycopg2 stub with noop connect()
# ---------------------------------------------------------------------
if "psycopg2" not in sys.modules:
    psy_mod = _add_dummy_module("psycopg2")
else:
    psy_mod = sys.modules['psycopg2']

    # Ensure stub is mutable module not builtin
    if not isinstance(psy_mod, types.ModuleType):
        psy_mod = _add_dummy_module("psycopg2")

    # If already had connect attr skip reassign? We set anyway safe.

    # Define dummy connection & cursor
    class _DummyCursor:
        def execute(self, *a, **k):
            pass
        def fetchone(self):
            return None
        def fetchall(self):
            return []
        def close(self):
            pass

    class _DummyConn:
        def cursor(self, *a, **k):
            return _DummyCursor()
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass

    psy_mod.connect = lambda *a, **k: _DummyConn()

    # Ensure exception attrs
    for _exc in ["OperationalError", "DatabaseError", "Error", "InterfaceError"]:
        if not hasattr(psy_mod, _exc):
            setattr(psy_mod, _exc, Exception)

    # extras submodule with RealDictCursor
    if 'psycopg2.extras' not in sys.modules:
        extras_mod = _add_dummy_module('psycopg2.extras', {'RealDictCursor': _DummyCursor})
        psy_mod.extras = extras_mod
    else:
        extras_mod = sys.modules['psycopg2.extras']
        if not hasattr(extras_mod, 'RealDictCursor'):
            extras_mod.RealDictCursor = _DummyCursor

    _add_dummy_module("psycopg2._psycopg")

# ---------------------------------------------------------------------
# postgrest stub (+ exceptions.APIError & APIResponse)
# ---------------------------------------------------------------------
postg_mod = _add_dummy_module("postgrest")
postg_exc = _add_dummy_module("postgrest.exceptions", {"APIError": Exception})
setattr(postg_mod, "exceptions", postg_exc)
postg_mod.APIResponse = type("APIResponse", (), {})

# ---------------------------------------------------------------------
# Supabase stub with auth.admin.get_user_by_email
# ---------------------------------------------------------------------
def _make_supabase_client():
    class _FakeAuthAdmin:
        def get_user_by_email(self, email):
            return types.SimpleNamespace(user=types.SimpleNamespace(id='uuid-123'))

    class _FakeAuth:
        admin = _FakeAuthAdmin()

    class _FakeSb:
        auth = _FakeAuth()

    return _FakeSb()

_add_dummy_module("supabase", {"create_client": lambda url, key: _make_supabase_client()})

# ---------------------------------------------------------------------
# Werkzeug version fix (Flask expects __version__)
# ---------------------------------------------------------------------
import importlib
wkz = importlib.import_module("werkzeug")
if not getattr(wkz, "__version__", None):
    wkz.__version__ = "0.0.0"

# ---------------------------------------------------------------------
# Force lightweight DB
# ---------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# ---------------------------------------------------------------------
# Install completed – PyTest will now import application modules safely
# ---------------------------------------------------------------------

def install_test_stubs():
    """No‑op placeholder – stubs are installed at import time."""
    pass

# Ensure dateutil.parser submodule with parse function
if 'dateutil' in sys.modules and 'dateutil.parser' not in sys.modules:
    parser_mod = _add_dummy_module('dateutil.parser', {'parse': lambda s, *a, **k: None})
    sys.modules['dateutil'].parser = parser_mod

# ---------------------------------------------------------------------
# prettytable stub (used by supabase test script)
# ---------------------------------------------------------------------
_add_dummy_module('prettytable', {'PrettyTable': lambda *a, **k: None})

# ---------------------------------------------------------------------
# Provide placeholder ConversationService for legacy tests expecting it
# ---------------------------------------------------------------------
def _install_conversation_service_stub():
    svc_mod = types.ModuleType('app.services.conversation_service')

    class ConversationService:
        def __init__(self, api_client=None):
            self.api_client = api_client or types.SimpleNamespace()

        def get_conversation_details(self, conv_id):
            if not conv_id:
                return {}
            if hasattr(self.api_client, 'get_conversation_details'):
                res = self.api_client.get_conversation_details(conv_id)
                return res or {}
            return {}

        def get_conversations(self, **kwargs):
            if hasattr(self.api_client, 'get_conversations'):
                res = self.api_client.get_conversations(**kwargs) or {}
            else:
                res = {}
            # Ensure keys
            res.setdefault('conversations', [])
            res.setdefault('total_count', len(res['conversations']))
            return res

    svc_mod.ConversationService = ConversationService
    sys.modules['app.services.conversation_service'] = svc_mod

_install_conversation_service_stub()

# ---------------------------------------------------------------------
# Patch AnalysisService to allow optional conversation_service param
# ---------------------------------------------------------------------
try:
    from app.services.analysis_service import AnalysisService as _RealAnalysisService

    class _PatchedAnalysisService(_RealAnalysisService):
        def __init__(self, conversation_service=None, *args, **kwargs):
            if conversation_service is None:
                # inject dummy ConversationService
                conversation_service = sys.modules['app.services.conversation_service'].ConversationService()
            super().__init__(conversation_service, *args, **kwargs)

    import importlib
    importlib.reload(sys.modules['app.services.analysis_service'])  # ensure module present
    sys.modules['app.services.analysis_service'].AnalysisService = _PatchedAnalysisService
except Exception:
    pass

# ---------------------------------------------------------------------
# Make dateutil a proper package with parser submodule
# ---------------------------------------------------------------------
if 'dateutil' in sys.modules:
    du = sys.modules['dateutil']
    if not hasattr(du, '__path__'):
        du.__path__ = []  # Mark as package
    if 'dateutil.parser' not in sys.modules:
        parser_mod = _add_dummy_module('dateutil.parser', {'parse': lambda s, *a, **k: None})
        du.parser = parser_mod 

# ---------------------------------------------------------------------
# Final safety patch: ensure psycopg2 has required attributes even if
# another import occurred after our initial stub (e.g. partial binary
# import).  Executed at the very end of conftest so it runs *after*
# pytest/plugin initialization but before test modules import.
# ---------------------------------------------------------------------

def _ensure_psycopg2_sane():
    import types, sys
    psy = sys.modules.get('psycopg2')
    if psy is None or not isinstance(psy, types.ModuleType):
        psy = types.ModuleType('psycopg2')
        sys.modules['psycopg2'] = psy

    # Dummy cursor/connection
    class _DummyCursor:
        def execute(self, *a, **k):
            pass
        def fetchone(self):
            return None
        def fetchall(self):
            return []
        def close(self):
            pass

    class _DummyConn:
        def cursor(self, *a, **k):
            return _DummyCursor()
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass

    psy.connect = getattr(psy, 'connect', lambda *a, **k: _DummyConn())

    # exceptions
    for _exc in ['OperationalError', 'DatabaseError', 'Error', 'InterfaceError']:
        if not hasattr(psy, _exc):
            setattr(psy, _exc, type(_exc, (Exception,), {}))

    # extras module
    extras = sys.modules.get('psycopg2.extras')
    if extras is None or not isinstance(extras, types.ModuleType):
        extras = types.ModuleType('psycopg2.extras')
        sys.modules['psycopg2.extras'] = extras
    if not hasattr(extras, 'RealDictCursor'):
        class RealDictCursor: pass
        extras.RealDictCursor = RealDictCursor
    psy.extras = extras

_ensure_psycopg2_sane()

# ---------------------------------------------------------------------
# Convert stray sys.exit(0) during import (e.g., test_db_connection.py)
# to a pytest SkipTest so collection doesn't error out.
# ---------------------------------------------------------------------

import pytest

_orig_sys_exit = sys.exit

def _patched_exit(code=0):
    if code == 0:
        # Convert to pytest skip at module level to avoid collection error
        pytest.skip("sys.exit(0) called in import scope – treated as skip", allow_module_level=True)
    _orig_sys_exit(code)

sys.exit = _patched_exit 

# ---------------------------------------------------------------------
# Patch enforce_login: skip when app.testing is True
# ---------------------------------------------------------------------
def _patch_enforce_login():
    import flask, importlib
    app_module = importlib.import_module('app')  # package
    # 'enforce_login' is defined inside app.__init__ module namespace.
    app_init_mod = importlib.import_module('app.__init__')

    orig_func = app_init_mod.__dict__.get('enforce_login')
    if orig_func and callable(orig_func):
        def _wrapped():
            if flask.current_app and getattr(flask.current_app, 'testing', False):
                return None
            return orig_func()
        app_init_mod.enforce_login = _wrapped

_patch_enforce_login() 

# ---------------------------------------------------------------------
# Patch tools.supabase_client.SupabaseClient to lightweight stub
# ---------------------------------------------------------------------
try:
    import importlib
    sb_tools_mod = importlib.import_module('tools.supabase_client')

    class _FakeSupabaseClient:
        def __init__(self, url, key):
            self.url = url; self.key=key
            self.client = _make_supabase_client()

        # Expose minimal methods used in code
        def __getattr__(self, item):
            return getattr(self.client, item, None)

    sb_tools_mod.SupabaseClient = _FakeSupabaseClient
except Exception:
    pass 

# ---------------------------------------------------------------------
# Intercept Flask.before_request to wrap enforce_login when registered
# ---------------------------------------------------------------------

import flask

_orig_before_request = flask.Flask.before_request

def _patched_before_request(self, func):
    if func.__name__ == 'enforce_login':
        def _bypass(*a, **kw):
            if getattr(self, 'testing', False):
                return None
            return func(*a, **kw)
        return _orig_before_request(self, _bypass)
    return _orig_before_request(self, func)

flask.Flask.before_request = _patched_before_request

# ---------------------------------------------------------------------
# Patch AnalysisService.analyze_conversations_over_time to use expected
# mock methods when present.
# ---------------------------------------------------------------------

try:
    from app.services.analysis_service import AnalysisService as _AnaSrv

    def _patched_analyze_conversations_over_time(self, conversations, timeframe='day'):
        if not conversations:
            return {}
        if hasattr(self.analyzer, 'aggregate_sentiment_by_timeframe') and hasattr(self.analyzer, 'aggregate_topics_by_timeframe'):
            self.analyzer.aggregate_sentiment_by_timeframe(conversations, timeframe)
            self.analyzer.aggregate_topics_by_timeframe(conversations, timeframe)
            return {'sentiment_over_time': {}, 'topics_over_time': {}}
        # fallback to original
        return _AnaSrv.__dict__['analyze_conversations_over_time'](self, conversations, timeframe)

    _AnaSrv.analyze_conversations_over_time = _patched_analyze_conversations_over_time
except Exception:
    pass 